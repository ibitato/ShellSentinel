"""Wrapper Mistral con reasoning_effort obligatorio para Shell Sentinel."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any, Literal, override

from mistralai.client import Mistral
from strands.models._validation import warn_on_tool_choice_not_supported
from strands.models.mistral import MistralModel
from strands.types.content import Messages
from strands.types.exceptions import ModelThrottledException
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

logger = logging.getLogger("smart_ai_sys_admin.agent.providers.mistral")

ReasoningEffort = Literal["high", "none"]
DEFAULT_REASONING_EFFORT: ReasoningEffort = "high"


def _extract_delta_segments(content: Any) -> list[tuple[str, str]]:
    """Convierte delta.content de Mistral en segmentos (kind, text)."""
    if content is None:
        return []
    if isinstance(content, str):
        return [("text", content)] if content else []

    segments: list[tuple[str, str]] = []
    for chunk in content:
        chunk_type = getattr(chunk, "type", None)
        if chunk_type == "thinking":
            for inner in getattr(chunk, "thinking", None) or []:
                if getattr(inner, "type", None) == "text":
                    text = getattr(inner, "text", "")
                    if text:
                        segments.append(("reasoning", text))
        elif chunk_type == "text":
            text = getattr(chunk, "text", "")
            if text:
                segments.append(("text", text))
    return segments


class ShellMistralModel(MistralModel):
    """Extiende Strands MistralModel inyectando reasoning_effort y thinking stream."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client_args: dict[str, Any] | None = None,
        reasoning_effort: ReasoningEffort = DEFAULT_REASONING_EFFORT,
        **model_config: Any,
    ) -> None:
        if reasoning_effort not in ("high", "none"):
            raise ValueError(
                f"reasoning_effort debe ser 'high' o 'none', se recibió: {reasoning_effort!r}"
            )
        self._reasoning_effort: ReasoningEffort = reasoning_effort
        super().__init__(api_key=api_key, client_args=client_args, **model_config)

    @property
    def reasoning_effort(self) -> ReasoningEffort:
        return self._reasoning_effort

    @override
    def format_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        request = super().format_request(messages, tool_specs, system_prompt)
        request["reasoning_effort"] = self._reasoning_effort
        return request

    @override
    def format_chunk(self, event: dict[str, Any]) -> StreamEvent:
        chunk_type = event.get("chunk_type")
        data_type = event.get("data_type")
        if chunk_type == "content_start" and data_type == "reasoning_content":
            return {"contentBlockStart": {"start": {}}}
        if chunk_type == "content_delta" and data_type == "reasoning_content":
            return {
                "contentBlockDelta": {
                    "delta": {"reasoningContent": {"text": event["data"]}},
                }
            }
        if chunk_type == "content_stop" and data_type in {"reasoning_content", "text"}:
            return {"contentBlockStop": {}}
        return super().format_chunk(event)

    @override
    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        warn_on_tool_choice_not_supported(tool_choice)

        request = self.format_request(messages, tool_specs, system_prompt)
        logger.debug("ShellMistralModel request keys: %s", list(request.keys()))

        try:
            if not self.config.get("stream", True):
                async with Mistral(**self.client_args) as client:
                    response = await client.chat.complete_async(**request)
                    for event in self._handle_non_streaming_response(response):
                        yield self.format_chunk(event)
                return

            async with Mistral(**self.client_args) as client:
                stream_response = await client.chat.stream_async(**request)

                yield self.format_chunk({"chunk_type": "message_start"})

                text_started = False
                reasoning_started = False
                tool_calls: dict[str, list[Any]] = {}

                async for chunk in stream_response:
                    if not (
                        hasattr(chunk, "data")
                        and hasattr(chunk.data, "choices")
                        and chunk.data.choices
                    ):
                        continue

                    choice = chunk.data.choices[0]
                    delta = getattr(choice, "delta", None)

                    if delta is not None and hasattr(delta, "content") and delta.content:
                        for kind, text in _extract_delta_segments(delta.content):
                            if kind == "reasoning":
                                if not reasoning_started:
                                    yield self.format_chunk(
                                        {
                                            "chunk_type": "content_start",
                                            "data_type": "reasoning_content",
                                        }
                                    )
                                    reasoning_started = True
                                yield self.format_chunk(
                                    {
                                        "chunk_type": "content_delta",
                                        "data_type": "reasoning_content",
                                        "data": text,
                                    }
                                )
                            else:
                                if reasoning_started and not text_started:
                                    yield self.format_chunk(
                                        {
                                            "chunk_type": "content_stop",
                                            "data_type": "reasoning_content",
                                        }
                                    )
                                    reasoning_started = False
                                if not text_started:
                                    yield self.format_chunk(
                                        {"chunk_type": "content_start", "data_type": "text"}
                                    )
                                    text_started = True
                                yield self.format_chunk(
                                    {
                                        "chunk_type": "content_delta",
                                        "data_type": "text",
                                        "data": text,
                                    }
                                )

                    if delta is not None and hasattr(delta, "tool_calls") and delta.tool_calls:
                        for tool_call in delta.tool_calls:
                            tool_id = tool_call.id
                            tool_calls.setdefault(tool_id, []).append(tool_call)

                    if hasattr(choice, "finish_reason") and choice.finish_reason:
                        if reasoning_started:
                            yield self.format_chunk(
                                {"chunk_type": "content_stop", "data_type": "reasoning_content"}
                            )
                            reasoning_started = False
                        if text_started:
                            yield self.format_chunk(
                                {"chunk_type": "content_stop", "data_type": "text"}
                            )
                            text_started = False

                        for tool_deltas in tool_calls.values():
                            yield self.format_chunk(
                                {
                                    "chunk_type": "content_start",
                                    "data_type": "tool",
                                    "data": tool_deltas[0],
                                }
                            )
                            for tool_delta in tool_deltas:
                                if hasattr(tool_delta.function, "arguments"):
                                    yield self.format_chunk(
                                        {
                                            "chunk_type": "content_delta",
                                            "data_type": "tool",
                                            "data": tool_delta.function.arguments,
                                        }
                                    )
                            yield self.format_chunk(
                                {"chunk_type": "content_stop", "data_type": "tool"}
                            )

                        yield self.format_chunk(
                            {"chunk_type": "message_stop", "data": choice.finish_reason}
                        )

                        if (
                            hasattr(chunk, "data")
                            and hasattr(chunk.data, "usage")
                            and chunk.data.usage
                        ):
                            yield self.format_chunk(
                                {"chunk_type": "metadata", "data": chunk.data.usage}
                            )

        except Exception as exc:
            if "rate" in str(exc).lower() or "429" in str(exc):
                raise ModelThrottledException(str(exc)) from exc
            raise

        logger.debug("ShellMistralModel stream finished")


__all__ = ["DEFAULT_REASONING_EFFORT", "ShellMistralModel"]
