"""Pruebas unitarias del proveedor ShellMistralModel."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from mistralai.client.models import PromptTokensDetails

from smart_ai_sys_admin.agent.providers.mistral import (
    DEFAULT_REASONING_EFFORT,
    ShellMistralModel,
)
from smart_ai_sys_admin.agent.runtime import summarize_cache_usage
from tests.e2e.fake_mistral_sdk import (
    FakeChat,
    completion_response,
    install_fake_mistral,
    stream_chunk,
    tool_call_delta,
    usage_info,
)


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


_FakeChat = FakeChat
_usage = usage_info
_completion_response = completion_response


def _stream_chunk(*, content=None, finish_reason=None, usage=None):
    return stream_chunk(content=content, finish_reason=finish_reason, usage=usage)


def _metadata_usage(events):
    metadata_events = [event["metadata"] for event in events if "metadata" in event]
    assert len(metadata_events) == 1
    return metadata_events[0]["usage"]


def _install_fake_client(monkeypatch, chat: _FakeChat):
    install_fake_mistral(monkeypatch, chat)


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


# --- Tool calls: reensamblado de fragmentos repartidos en varios deltas -------------


def _tool_use_blocks(events):
    """Reconstruye los bloques ``toolUse`` (start + input concatenado) del stream."""
    blocks = []
    current = None
    for event in events:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"]["start"]
            current = {"start": start.get("toolUse"), "input": ""} if "toolUse" in start else None
        elif "contentBlockDelta" in event and current is not None:
            delta = event["contentBlockDelta"]["delta"]
            if "toolUse" in delta:
                current["input"] += delta["toolUse"]["input"]
        elif "contentBlockStop" in event and current is not None:
            blocks.append(current)
            current = None
    return blocks


def _stop_reasons(events):
    return [event["messageStop"]["stopReason"] for event in events if "messageStop" in event]


async def _stream_tool_calls(monkeypatch, chunks):
    chat = _FakeChat(stream_chunks=chunks)
    _install_fake_client(monkeypatch, chat)
    model = ShellMistralModel(api_key="test-key", model_id="zai-glm-5-3")
    return await _collect(model)


async def test_stream_reassembles_arguments_split_across_deltas_with_null_ids(monkeypatch):
    """Incidente 2026-10-18: id y nombre solo en el primer delta, resto con id ``"null"``."""
    events = await _stream_tool_calls(
        monkeypatch,
        [
            _stream_chunk(),
            stream_chunk(tool_calls=[tool_call_delta("call_1", "remote_ssh_command", '{"comm')]),
            stream_chunk(tool_calls=[tool_call_delta(None, None, 'and": "una')]),
            stream_chunk(tool_calls=[tool_call_delta(None, "", 'me -a"}')]),
            stream_chunk(finish_reason="tool_calls", usage=_usage()),
        ],
    )

    assert _tool_use_blocks(events) == [
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_1"},
            "input": '{"command": "uname -a"}',
        }
    ]
    assert _stop_reasons(events) == ["tool_use"]


async def test_stream_keeps_parallel_tool_calls_separate(monkeypatch):
    events = await _stream_tool_calls(
        monkeypatch,
        [
            stream_chunk(
                tool_calls=[
                    tool_call_delta("call_a", "remote_ssh_command", '{"command": ', index=0),
                    tool_call_delta("call_b", "local_datetime", "{", index=1),
                ]
            ),
            stream_chunk(tool_calls=[tool_call_delta(None, None, '"uptime"}', index=0)]),
            stream_chunk(tool_calls=[tool_call_delta(None, None, "}", index=1)]),
            stream_chunk(finish_reason="tool_calls", usage=_usage()),
        ],
    )

    assert _tool_use_blocks(events) == [
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_a"},
            "input": '{"command": "uptime"}',
        },
        {"start": {"name": "local_datetime", "toolUseId": "call_b"}, "input": "{}"},
    ]


async def test_stream_separates_parallel_tool_calls_sharing_index_zero(monkeypatch):
    """Dos llamadas con ids reales distintos no se mezclan aunque ambas lleguen con index 0."""
    events = await _stream_tool_calls(
        monkeypatch,
        [
            stream_chunk(tool_calls=[tool_call_delta("call_a", "remote_ssh_command", '{"comm')]),
            stream_chunk(tool_calls=[tool_call_delta(None, None, 'and": "uptime"}')]),
            stream_chunk(tool_calls=[tool_call_delta("call_b", "remote_ssh_command", '{"comm')]),
            stream_chunk(tool_calls=[tool_call_delta(None, None, 'and": "df -h"}')]),
            stream_chunk(finish_reason="tool_calls", usage=_usage()),
        ],
    )

    assert _tool_use_blocks(events) == [
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_a"},
            "input": '{"command": "uptime"}',
        },
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_b"},
            "input": '{"command": "df -h"}',
        },
    ]


async def test_stream_falls_back_to_last_open_tool_call_without_id_or_index(monkeypatch):
    events = await _stream_tool_calls(
        monkeypatch,
        [
            stream_chunk(tool_calls=[tool_call_delta("call_1", "remote_ssh_command", '{"comm')]),
            stream_chunk(tool_calls=[tool_call_delta(None, None, 'and": "una', index=None)]),
            stream_chunk(tool_calls=[tool_call_delta("", None, 'me -a"}', index=None)]),
            stream_chunk(finish_reason="tool_calls", usage=_usage()),
        ],
    )

    assert _tool_use_blocks(events) == [
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_1"},
            "input": '{"command": "uname -a"}',
        }
    ]


async def test_stream_single_delta_tool_call(monkeypatch):
    events = await _stream_tool_calls(
        monkeypatch,
        [
            stream_chunk(
                tool_calls=[tool_call_delta("call_1", "remote_ssh_command", '{"command": "id"}')],
                finish_reason="tool_calls",
                usage=_usage(),
            ),
        ],
    )

    assert _tool_use_blocks(events) == [
        {
            "start": {"name": "remote_ssh_command", "toolUseId": "call_1"},
            "input": '{"command": "id"}',
        }
    ]
    assert _stop_reasons(events) == ["tool_use"]


async def test_stream_serializes_dict_arguments_as_json(monkeypatch):
    events = await _stream_tool_calls(
        monkeypatch,
        [
            stream_chunk(
                tool_calls=[tool_call_delta("call_1", "remote_ssh_command", {"command": "id"})],
                finish_reason="tool_calls",
                usage=_usage(),
            ),
        ],
    )

    assert _tool_use_blocks(events)[0]["input"] == '{"command": "id"}'


async def test_stream_warns_when_reassembled_arguments_are_not_json(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.providers.mistral"):
        events = await _stream_tool_calls(
            monkeypatch,
            [
                stream_chunk(
                    tool_calls=[tool_call_delta("call_1", "remote_ssh_command", '{"comm')]
                ),
                stream_chunk(finish_reason="tool_calls", usage=_usage()),
            ],
        )

    assert _tool_use_blocks(events)[0]["input"] == '{"comm'
    assert "remote_ssh_command" in caplog.text
    assert "JSON inválidos" in caplog.text


async def test_stream_warns_when_tool_call_has_no_arguments(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.providers.mistral"):
        await _stream_tool_calls(
            monkeypatch,
            [
                stream_chunk(
                    tool_calls=[tool_call_delta("call_1", "remote_ssh_command", "")],
                    finish_reason="tool_calls",
                    usage=_usage(),
                ),
            ],
        )

    assert "sin argumentos" in caplog.text
    assert "remote_ssh_command" in caplog.text


async def test_stream_does_not_warn_for_well_formed_tool_call(monkeypatch, caplog):
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.providers.mistral"):
        await _stream_tool_calls(
            monkeypatch,
            [
                stream_chunk(
                    tool_calls=[
                        tool_call_delta("call_1", "remote_ssh_command", '{"command": "id"}')
                    ],
                    finish_reason="tool_calls",
                    usage=_usage(),
                ),
            ],
        )

    assert caplog.text == ""
