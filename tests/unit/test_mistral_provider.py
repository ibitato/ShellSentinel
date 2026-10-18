"""Pruebas unitarias del proveedor ShellMistralModel."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mistralai.client.models import PromptTokensDetails, UsageInfo

from smart_ai_sys_admin.agent.providers import mistral as mistral_provider
from smart_ai_sys_admin.agent.providers.mistral import (
    DEFAULT_REASONING_EFFORT,
    ShellMistralModel,
)
from smart_ai_sys_admin.agent.runtime import summarize_cache_usage


def test_format_request_injects_reasoning_effort_high():
    model = ShellMistralModel(
        api_key="test-key",
        model_id="mistral-medium-3.5",
        reasoning_effort="high",
        stream=False,
    )
    request = model.format_request(
        messages=[{"role": "user", "content": [{"text": "hola"}]}],
    )
    assert request["reasoning_effort"] == "high"
    assert request["model"] == "mistral-medium-3.5"


def test_format_request_defaults_reasoning_effort_to_high():
    model = ShellMistralModel(
        api_key="test-key",
        model_id="mistral-medium-3.5",
        stream=False,
    )
    assert model.reasoning_effort == DEFAULT_REASONING_EFFORT
    request = model.format_request(
        messages=[{"role": "user", "content": [{"text": "hola"}]}],
    )
    assert request["reasoning_effort"] == "high"


def test_invalid_reasoning_effort_raises():
    with pytest.raises(ValueError, match="reasoning_effort"):
        ShellMistralModel(
            api_key="test-key",
            model_id="mistral-medium-3.5",
            reasoning_effort="medium",  # type: ignore[arg-type]
        )


# --- Prompt cache: cacheReadInputTokens en los metadatos de usage -------------------


class _FakeStream:
    """Simula el iterador asíncrono que devuelve ``chat.stream_async``."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class _FakeChat:
    def __init__(self, *, stream_chunks=None, response=None):
        self._stream_chunks = stream_chunks or []
        self._response = response
        self.requests: list[dict] = []

    async def stream_async(self, **request):
        self.requests.append(request)
        return _FakeStream(self._stream_chunks)

    async def complete_async(self, **request):
        self.requests.append(request)
        return self._response


class _FakeMistralClient:
    """Sustituye a ``mistralai.client.Mistral`` como context manager asíncrono."""

    chat: _FakeChat | None = None

    def __init__(self, **_client_args):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False


def _usage(prompt=120, completion=8, total=128, **extra):
    """Construye un ``UsageInfo`` real del SDK; los extras van a los campos adicionales."""
    return UsageInfo.model_validate(
        {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": total,
            **extra,
        }
    )


def _stream_chunk(*, content=None, finish_reason=None, usage=None):
    delta = SimpleNamespace(content=content, tool_calls=None)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(data=SimpleNamespace(choices=[choice], usage=usage))


def _completion_response(*, usage):
    message = SimpleNamespace(content="hola", tool_calls=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice], usage=usage)


def _metadata_usage(events):
    metadata_events = [event["metadata"] for event in events if "metadata" in event]
    assert len(metadata_events) == 1
    return metadata_events[0]["usage"]


def _install_fake_client(monkeypatch, chat: _FakeChat):
    monkeypatch.setattr(_FakeMistralClient, "chat", chat, raising=False)
    monkeypatch.setattr(mistral_provider, "Mistral", _FakeMistralClient)


async def _collect(model: ShellMistralModel):
    return [
        event
        async for event in model.stream(messages=[{"role": "user", "content": [{"text": "hola"}]}])
    ]


def test_format_chunk_metadata_adds_cache_read_tokens_from_dict_details():
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")
    usage = _usage(prompt_tokens_details={"cached_tokens": 64})

    event = model.format_chunk({"chunk_type": "metadata", "data": usage})

    assert event["metadata"]["usage"] == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
        "cacheReadInputTokens": 64,
    }


def test_format_chunk_metadata_adds_cache_read_tokens_from_typed_details():
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")
    usage = SimpleNamespace(
        prompt_tokens=50,
        completion_tokens=5,
        total_tokens=55,
        prompt_tokens_details=PromptTokensDetails(cached_tokens=32),
    )

    event = model.format_chunk({"chunk_type": "metadata", "data": usage})

    assert event["metadata"]["usage"]["cacheReadInputTokens"] == 32
    assert event["metadata"]["usage"]["inputTokens"] == 50


def test_format_chunk_metadata_without_details_omits_cache_read_tokens():
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")

    event = model.format_chunk({"chunk_type": "metadata", "data": _usage()})

    assert event["metadata"]["usage"] == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
    }


@pytest.mark.parametrize(
    "details",
    [
        None,
        {},
        {"cached_tokens": None},
        {"cached_tokens": "64"},
        {"cached_tokens": -1},
        {"cached_tokens": True},
    ],
)
def test_format_chunk_metadata_ignores_invalid_cached_tokens(details):
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")
    usage = _usage(prompt_tokens_details=details)

    event = model.format_chunk({"chunk_type": "metadata", "data": usage})

    assert "cacheReadInputTokens" not in event["metadata"]["usage"]


def test_format_chunk_metadata_reports_zero_cached_tokens():
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")
    usage = _usage(prompt_tokens_details={"cached_tokens": 0})

    event = model.format_chunk({"chunk_type": "metadata", "data": usage})

    assert event["metadata"]["usage"]["cacheReadInputTokens"] == 0


async def test_stream_emits_cache_read_tokens_when_present(monkeypatch):
    chat = _FakeChat(
        stream_chunks=[
            _stream_chunk(content="ho"),
            _stream_chunk(
                content="la",
                finish_reason="stop",
                usage=_usage(prompt_tokens_details={"cached_tokens": 96}),
            ),
        ]
    )
    _install_fake_client(monkeypatch, chat)
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")

    events = await _collect(model)

    assert _metadata_usage(events) == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
        "cacheReadInputTokens": 96,
    }
    assert chat.requests[0]["reasoning_effort"] == "high"


async def test_stream_without_cached_tokens_keeps_plain_usage(monkeypatch):
    chat = _FakeChat(
        stream_chunks=[_stream_chunk(content="hola", finish_reason="stop", usage=_usage())]
    )
    _install_fake_client(monkeypatch, chat)
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")

    events = await _collect(model)

    assert _metadata_usage(events) == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
    }


async def test_non_streaming_emits_cache_read_tokens_when_present(monkeypatch):
    chat = _FakeChat(
        response=_completion_response(
            usage=_usage(prompt_tokens_details={"cached_tokens": 40}),
        )
    )
    _install_fake_client(monkeypatch, chat)
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5", stream=False)

    events = await _collect(model)

    assert _metadata_usage(events) == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
        "cacheReadInputTokens": 40,
    }
    assert chat.requests[0]["model"] == "mistral-medium-3.5"


async def test_non_streaming_without_cached_tokens_keeps_plain_usage(monkeypatch):
    chat = _FakeChat(response=_completion_response(usage=_usage()))
    _install_fake_client(monkeypatch, chat)
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5", stream=False)

    events = await _collect(model)

    assert _metadata_usage(events) == {
        "inputTokens": 120,
        "outputTokens": 8,
        "totalTokens": 128,
    }


def test_summarize_cache_usage_handles_mistral_accounting():
    """Mistral incluye los tokens cacheados en prompt_tokens, igual que OpenAI."""
    model = ShellMistralModel(api_key="test-key", model_id="mistral-medium-3.5")
    usage = _usage(prompt_tokens_details={"cached_tokens": 64})

    event = model.format_chunk({"chunk_type": "metadata", "data": usage})
    summary = summarize_cache_usage(event["metadata"]["usage"])

    assert summary == {
        "input_tokens": 120,
        "cached_tokens": 64,
        "written_tokens": 0,
        "percent": 53,
    }
