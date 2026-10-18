"""Doble del cliente ``mistralai`` para probar ``ShellMistralModel`` sin red.

Reproduce la forma de los objetos que devuelve el SDK 2.x (``chunk.data.choices[0]
.delta``, ``tool_calls``, ``usage``) con ``SimpleNamespace`` y ``UsageInfo`` reales.
Se instala con ``install_fake_mistral`` sustituyendo ``Mistral`` en el módulo del
proveedor.
"""

from __future__ import annotations

from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import pytest
from mistralai.client.models import UsageInfo

from smart_ai_sys_admin.agent.providers import mistral as mistral_provider


class FakeStream:
    """Iterador asíncrono que entrega los chunks de ``chat.stream_async``."""

    def __init__(self, chunks: Iterable[Any]) -> None:
        self._chunks = list(chunks)

    def __aiter__(self) -> FakeStream:
        return self

    async def __anext__(self) -> Any:
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class FakeChat:
    """Registra las peticiones y devuelve guiones de streaming o respuestas completas.

    ``stream_scripts`` permite encadenar varias llamadas a ``stream_async`` con chunks
    distintos (p. ej. un turno de tool call y después un turno de texto).
    """

    def __init__(
        self,
        *,
        stream_chunks: Iterable[Any] | None = None,
        stream_scripts: Iterable[Iterable[Any]] | None = None,
        response: Any = None,
        responses: Iterable[Any] | None = None,
    ) -> None:
        self._stream_chunks = list(stream_chunks or [])
        self._stream_scripts = [list(script) for script in (stream_scripts or [])]
        self._response = response
        self._responses = list(responses or [])
        self.requests: list[dict[str, Any]] = []

    async def stream_async(self, **request: Any) -> FakeStream:
        self.requests.append(request)
        if self._stream_scripts:
            return FakeStream(self._stream_scripts.pop(0))
        return FakeStream(self._stream_chunks)

    async def complete_async(self, **request: Any) -> Any:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return self._response


class FakeMistralClient:
    """Sustituye a ``mistralai.client.Mistral`` como context manager asíncrono."""

    chat: FakeChat | None = None

    def __init__(self, **_client_args: Any) -> None:
        pass

    async def __aenter__(self) -> FakeMistralClient:
        return self

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


def install_fake_mistral(monkeypatch: pytest.MonkeyPatch, chat: FakeChat) -> None:
    """Hace que ``ShellMistralModel`` hable con ``chat`` en lugar de con la API real."""

    monkeypatch.setattr(FakeMistralClient, "chat", chat, raising=False)
    monkeypatch.setattr(mistral_provider, "Mistral", FakeMistralClient)


def usage_info(prompt: int = 120, completion: int = 8, total: int = 128, **extra: Any) -> UsageInfo:
    """``UsageInfo`` real del SDK; los extras van a los campos adicionales de pydantic."""

    return UsageInfo.model_validate(
        {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            **extra,
        }
    )


def tool_call_delta(
    tool_id: str | None,
    name: str | None,
    arguments: str,
    *,
    index: int = 0,
) -> SimpleNamespace:
    """Fragmento de ``tool_calls`` tal y como lo emite el SDK en streaming.

    En el SDK 2.x un fragmento sin ``id`` llega con la cadena ``"null"`` (valor por
    defecto del modelo pydantic), no con ``None``; se respeta ese comportamiento.
    """

    return SimpleNamespace(
        id="null" if tool_id is None else tool_id,
        index=index,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def stream_chunk(
    *,
    content: Any = None,
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str | None = None,
    usage: UsageInfo | None = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(data=SimpleNamespace(choices=[choice], usage=usage))


def completion_response(
    *,
    content: Any = "hola",
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str = "stop",
    usage: UsageInfo | None = None,
) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], usage=usage)


__all__ = [
    "FakeChat",
    "FakeMistralClient",
    "FakeStream",
    "completion_response",
    "install_fake_mistral",
    "stream_chunk",
    "tool_call_delta",
    "usage_info",
]
