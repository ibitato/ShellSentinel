"""Wrapper Mistral con reasoning_effort obligatorio para Shell Sentinel."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from types import SimpleNamespace
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


def _extract_cached_prompt_tokens(usage: Any) -> int | None:
    """Obtiene ``prompt_tokens_details.cached_tokens`` del usage de Mistral si existe.

    El SDK expone ``prompt_tokens_details`` como objeto tipado en algunos endpoints y
    como dict (campo extra de pydantic) en Chat Completions, así que se aceptan ambos.
    Devuelve ``None`` cuando el campo falta, es ``None`` o no es un entero válido.
    """
    if usage is None:
        return None
    details = (
        usage.get("prompt_tokens_details")
        if isinstance(usage, dict)
        else getattr(usage, "prompt_tokens_details", None)
    )
    if details is None:
        return None
    cached = (
        details.get("cached_tokens")
        if isinstance(details, dict)
        else getattr(details, "cached_tokens", None)
    )
    if isinstance(cached, bool) or not isinstance(cached, int) or cached < 0:
        return None
    return cached


def _real_tool_call_id(tool_call: Any) -> str | None:
    """Devuelve el ``id`` del fragmento solo si es un identificador real.

    En el SDK 2.x un fragmento sin ``id`` se deserializa con la cadena ``"null"`` (valor
    por defecto del modelo pydantic); también se descartan ``None`` y la cadena vacía.
    """
    tool_id = getattr(tool_call, "id", None)
    if isinstance(tool_id, str) and tool_id and tool_id != "null":
        return tool_id
    return None


def _tool_call_index(tool_call: Any) -> int | None:
    """Devuelve ``index`` del fragmento cuando es un entero utilizable."""
    index = getattr(tool_call, "index", None)
    if isinstance(index, int) and not isinstance(index, bool):
        return index
    return None


def _tool_call_name(tool_call: Any) -> str | None:
    """Devuelve ``function.name`` si el fragmento lo trae (no vacío)."""
    name = getattr(getattr(tool_call, "function", None), "name", None)
    if isinstance(name, str) and name:
        return name
    return None


def _tool_call_arguments(tool_call: Any) -> str | None:
    """Devuelve el fragmento de argumentos como texto, serializando dicts a JSON."""
    function = getattr(tool_call, "function", None)
    if function is None or not hasattr(function, "arguments"):
        return None
    arguments = function.arguments
    if arguments is None:
        return None
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments)


@dataclass
class _PendingToolCall:
    """Tool call en construcción a partir de uno o más deltas de streaming."""

    index: int | None
    tool_id: str | None = None
    name: str | None = None
    head: Any = None
    fragments: list[str] = field(default_factory=list)

    def start_payload(self) -> Any:
        """Objeto para ``content_start``: el delta que trajo id y nombre, o uno sintético."""
        if (
            self.head is not None
            and _real_tool_call_id(self.head) == self.tool_id
            and _tool_call_name(self.head) == self.name
        ):
            return self.head
        return SimpleNamespace(
            id=self.tool_id,
            type="function",
            index=self.index,
            function=SimpleNamespace(name=self.name, arguments=""),
        )


class _ToolCallAssembler:
    """Reagrupa los fragmentos de ``tool_calls`` que llegan repartidos en varios deltas.

    Algunos modelos servidos por Mistral (p. ej. ``zai-glm-5-3``) envían el ``id`` y el
    nombre solo en el primer fragmento y el resto de los argumentos en deltas con id
    ``"null"``. Agrupar por ``id`` partía la llamada en varios bloques ``toolUse`` rotos
    y la herramienta acababa ejecutándose con ``input={}``. Aquí se agrupa por ``index``
    cuando existe, por ``id`` real cuando lo hay y, si el fragmento no trae ninguno de
    los dos, se añade a la última llamada abierta. Llamadas paralelas con ids o índices
    distintos se mantienen separadas.
    """

    def __init__(self) -> None:
        self._calls: list[_PendingToolCall] = []
        self._last: _PendingToolCall | None = None

    def add(self, tool_call: Any) -> None:
        tool_id = _real_tool_call_id(tool_call)
        index = _tool_call_index(tool_call)
        target = self._find(tool_id, index)
        if target is None:
            target = _PendingToolCall(index=index)
            self._calls.append(target)
        if tool_id is not None and target.tool_id is None:
            target.tool_id = tool_id
            target.head = tool_call
        name = _tool_call_name(tool_call)
        if name is not None and target.name is None:
            target.name = name
        if target.index is None and index is not None:
            target.index = index
        arguments = _tool_call_arguments(tool_call)
        if arguments:
            target.fragments.append(arguments)
        self._last = target

    def _find(self, tool_id: str | None, index: int | None) -> _PendingToolCall | None:
        if tool_id is not None:
            for call in reversed(self._calls):
                if call.tool_id == tool_id:
                    return call
            # Id nuevo: solo se reutiliza el grupo del índice si aún no tiene id propio;
            # si ya lo tiene es otra llamada paralela que comparte índice.
            if index is not None:
                for call in reversed(self._calls):
                    if call.index == index and call.tool_id is None:
                        return call
            return None
        if index is not None:
            for call in reversed(self._calls):
                if call.index == index:
                    return call
            return None
        return self._last

    def finished(self) -> list[_PendingToolCall]:
        """Llamadas reensambladas en orden de aparición."""
        return list(self._calls)


def _warn_if_malformed(call: _PendingToolCall, arguments: str) -> None:
    """Red de seguridad: avisa cuando la tool call reensamblada sigue siendo inservible."""
    if call.tool_id is None or call.name is None:
        logger.warning(
            "Tool call de Mistral incompleta (id=%r, name=%r, index=%r); Strands la descartará",
            call.tool_id,
            call.name,
            call.index,
        )
        return
    if not arguments.strip():
        logger.warning(
            "Tool call %s (%s) llegó sin argumentos; la herramienta se ejecutará con input vacío",
            call.name,
            call.tool_id,
        )
        return
    try:
        parsed = json.loads(arguments)
    except ValueError:
        logger.warning(
            "Tool call %s (%s) con argumentos JSON inválidos (%d fragmentos): %.200r",
            call.name,
            call.tool_id,
            len(call.fragments),
            arguments,
        )
        return
    if not isinstance(parsed, dict):
        logger.warning(
            "Tool call %s (%s) con argumentos que no son un objeto JSON: %.200r",
            call.name,
            call.tool_id,
            arguments,
        )


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
        if (
            chunk_type == "content_delta"
            and data_type == "tool"
            and not isinstance(event.get("data"), str)
        ):
            # El SDK admite ``arguments`` como dict; Strands concatena cadenas.
            event = {**event, "data": json.dumps(event.get("data"))}
        if chunk_type == "metadata":
            return self._format_metadata_chunk(event)
        return super().format_chunk(event)

    def _format_metadata_chunk(self, event: dict[str, Any]) -> StreamEvent:
        """Añade ``cacheReadInputTokens`` al usage que construye Strands.

        Strands solo copia ``prompt_tokens``/``completion_tokens``/``total_tokens`` e ignora
        ``prompt_tokens_details.cached_tokens``, por lo que ``/status`` mostraba siempre cero
        aciertos de caché con Mistral. Se mantiene ``inputTokens = prompt_tokens`` (contabilidad
        estilo OpenAI, con los tokens cacheados ya incluidos), que ``summarize_cache_usage``
        ya interpreta correctamente.
        """
        stream_event = super().format_chunk(event)
        cached = _extract_cached_prompt_tokens(event.get("data"))
        if cached is None:
            return stream_event
        usage = stream_event.get("metadata", {}).get("usage")
        if isinstance(usage, dict):
            usage["cacheReadInputTokens"] = cached
        return stream_event

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
                tool_calls = _ToolCallAssembler()

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
                            tool_calls.add(tool_call)

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

                        for pending in tool_calls.finished():
                            _warn_if_malformed(pending, "".join(pending.fragments))
                            yield self.format_chunk(
                                {
                                    "chunk_type": "content_start",
                                    "data_type": "tool",
                                    "data": pending.start_payload(),
                                }
                            )
                            for fragment in pending.fragments:
                                yield self.format_chunk(
                                    {
                                        "chunk_type": "content_delta",
                                        "data_type": "tool",
                                        "data": fragment,
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
