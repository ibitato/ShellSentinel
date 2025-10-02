"""Proveedor personalizado de Strands para Cerebras Cloud SDK."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any, TypedDict, TypeVar, cast

from cerebras.cloud.sdk import AsyncCerebras
from cerebras.cloud.sdk.types.chat.chat_completion import (
    ChatChunkResponse,
    ChatChunkResponseChoiceDeltaToolCall,
)
from strands.models import Model
from strands.models._validation import validate_config_keys
from strands.models.openai import OpenAIModel
from strands.tools import convert_pydantic_to_tool_spec
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

logger = logging.getLogger("smart_ai_sys_admin.agent.providers.cerebras")


class CerebrasModelConfig(TypedDict, total=False):
    """Opciones soportadas por el proveedor Cerebras."""

    model_id: str
    params: dict[str, Any]
    client_args: dict[str, Any]
    api_key_env: str
    api_key: str


T = TypeVar("T")


class CerebrasModel(Model):
    """Implementación de proveedor Strands sobre el SDK oficial de Cerebras."""

    def __init__(self, **model_config: Any) -> None:
        validate_config_keys(model_config, CerebrasModelConfig)

        raw_config: CerebrasModelConfig = cast(CerebrasModelConfig, model_config)
        self._config: CerebrasModelConfig = CerebrasModelConfig(
            model_id=raw_config.get("model_id", ""),
            params=dict(raw_config.get("params", {})),
        )

        client_args = dict(raw_config.get("client_args", {}))
        api_key = raw_config.get("api_key")
        api_key_env = raw_config.get("api_key_env")

        if api_key_env:
            self._config["api_key_env"] = api_key_env
            api_key = api_key or os.getenv(api_key_env)

        api_key = api_key or os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError(
                "CerebrasModel requiere un API key. "
                "Define 'api_key_env', 'api_key' o CEREBRAS_API_KEY'."
            )

        self._client_args = client_args
        self._client_args.setdefault("api_key", api_key)
        self._client = AsyncCerebras(**self._client_args)

        if client_args:
            safe_args = {k: v for k, v in client_args.items() if k != "api_key"}
            if safe_args:
                self._config["client_args"] = safe_args

        logger.debug("Inicializado CerebrasModel con configuración %s", list(self._config.keys()))

    # ------------------------------------------------------------------
    # Configuración dinámica
    # ------------------------------------------------------------------

    def update_config(self, **model_config: Any) -> None:  # type: ignore[override]
        validate_config_keys(model_config, CerebrasModelConfig)
        if "model_id" in model_config:
            self._config["model_id"] = cast(str, model_config["model_id"])
        if "params" in model_config:
            params = dict(model_config["params"] or {})
            self._config["params"] = cast(dict[str, Any], params)

    def get_config(self) -> CerebrasModelConfig:  # type: ignore[override]
        config: CerebrasModelConfig = CerebrasModelConfig(
            model_id=self._config.get("model_id", ""),
            params=dict(self._config.get("params", {})),
        )
        if "client_args" in self._config:
            config["client_args"] = dict(self._config.get("client_args", {}))
        if "api_key_env" in self._config:
            config["api_key_env"] = self._config["api_key_env"]
        return config

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        request = self._build_request(messages, tool_specs, system_prompt, tool_choice)
        request["stream"] = True

        logger.debug("Invocando modelo Cerebras con stream")
        response_stream = await self._client.chat.completions.create(**request)

        yield {"messageStart": {"role": "assistant"}}

        text_block_started = False
        tool_chunks: dict[int, list[ChatChunkResponseChoiceDeltaToolCall]] = {}
        last_usage = None
        last_time_info = None
        finish_reason: str | None = None

        async for chunk in response_stream:
            if not isinstance(chunk, ChatChunkResponse) or not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                if not text_block_started:
                    yield {"contentBlockStart": {"start": {}}}
                    text_block_started = True
                yield {"contentBlockDelta": {"delta": {"text": delta.content}}}

            if delta.reasoning:
                if not text_block_started:
                    yield {"contentBlockStart": {"start": {}}}
                    text_block_started = True
                yield {
                    "contentBlockDelta": {
                        "delta": {"reasoningContent": {"text": delta.reasoning}}
                    }
                }

            for tool_call in delta.tool_calls or []:
                idx = tool_call.index or 0
                tool_chunks.setdefault(idx, []).append(tool_call)

            last_usage = chunk.usage or last_usage
            last_time_info = chunk.time_info or last_time_info

            if choice.finish_reason:
                finish_reason = choice.finish_reason
                break

        async for chunk in response_stream:
            if isinstance(chunk, ChatChunkResponse):
                last_usage = chunk.usage or last_usage
                last_time_info = chunk.time_info or last_time_info

        if text_block_started:
            yield {"contentBlockStop": {}}

        for idx, calls in tool_chunks.items():
            first_call = calls[0]
            tool_name = first_call.function.name or ""
            tool_use_id = first_call.id or f"cerebras-tool-{idx}"
            yield {
                "contentBlockStart": {
                    "start": {
                        "toolUse": {
                            "name": tool_name,
                            "toolUseId": tool_use_id,
                        }
                    }
                }
            }
            for call in calls:
                yield {
                    "contentBlockDelta": {
                        "delta": {
                            "toolUse": {"input": call.function.arguments or ""}
                        }
                    }
                }
            yield {"contentBlockStop": {}}

        yield {"messageStop": {"stopReason": self._map_stop_reason(finish_reason)}}

        if last_usage:
            metadata: dict[str, Any] = {
                "usage": {
                    "inputTokens": last_usage.prompt_tokens or 0,
                    "outputTokens": last_usage.completion_tokens or 0,
                    "totalTokens": last_usage.total_tokens or 0,
                }
            }
            if last_time_info and last_time_info.total_time is not None:
                metadata["metrics"] = {"latencyMs": int(last_time_info.total_time * 1000)}
            yield {"metadata": metadata}

    # ------------------------------------------------------------------
    # Salidas estructuradas
    # ------------------------------------------------------------------

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        tool_spec = convert_pydantic_to_tool_spec(output_model)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_spec["name"],
                    "description": tool_spec.get("description"),
                    "parameters": tool_spec["inputSchema"]["json"],
                },
            }
        ]

        request = self._build_request(prompt, None, system_prompt, None)
        request.update(
            {
                "tools": tools,
                "tool_choice": {"type": "function", "function": {"name": tool_spec["name"]}},
            }
        )
        request.pop("stream", None)

        logger.debug("Invocando modelo Cerebras para structured_output")
        response = await self._client.chat.completions.create(**request)

        for choice in response.choices:
            for tool_call in choice.message.tool_calls or []:
                if tool_call.function.name != tool_spec["name"]:
                    continue
                try:
                    payload = json.loads(tool_call.function.arguments or "{}")
                    yield {"output": output_model(**payload)}
                    return
                except json.JSONDecodeError as exc:  # pragma: no cover - defensivo
                    raise ValueError(
                        "La respuesta del modelo no contiene JSON válido para la herramienta"
                    ) from exc

        raise ValueError(
            "No se encontró ninguna invocación de herramienta compatible "
            "en la respuesta del modelo."
        )

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _build_request(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None,
        system_prompt: str | None,
        tool_choice: ToolChoice | None,
    ) -> dict[str, Any]:
        formatted_messages = self._normalize_messages(
            OpenAIModel.format_request_messages(messages, system_prompt)
        )
        request: dict[str, Any] = {
            "messages": formatted_messages,
            "model": self._config.get("model_id", ""),
            **dict(self._config.get("params", {})),
        }

        if tool_specs:
            request["tools"] = [self._format_tool(tool) for tool in tool_specs]

        request.update(OpenAIModel._format_request_tool_choice(tool_choice))
        return request

    @staticmethod
    def _format_tool(tool_spec: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool_spec["name"],
                "description": tool_spec["description"],
                "parameters": tool_spec["inputSchema"]["json"],
            },
        }

    @staticmethod
    def _map_stop_reason(reason: str | None) -> str:
        if reason == "tool_calls":
            return "tool_use"
        if reason == "length":
            return "max_tokens"
        return "end_turn"

    @staticmethod
    def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for message in messages:
            entry = dict(message)
            content = entry.get("content")
            if isinstance(content, list):
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if "text" in block:
                            text_parts.append(str(block["text"]))
                        elif "image_url" in block:
                            url = block["image_url"].get("url", "")
                            text_parts.append(f"[image:{url}]")
                        elif "file" in block:
                            filename = block["file"].get("filename", "archivo")
                            text_parts.append(f"[file:{filename}]")
                        else:
                            text_parts.append(json.dumps(block))
                    else:
                        text_parts.append(str(block))
                entry["content"] = "".join(text_parts)
            elif content is None:
                entry["content"] = ""
            if "tool_calls" in entry and not isinstance(entry.get("content"), str):
                entry["content"] = ""
            normalized.append(entry)
        return normalized
