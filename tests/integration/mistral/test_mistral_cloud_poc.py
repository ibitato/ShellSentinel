"""PoC de integración Mistral cloud para validar ShellMistralModel (Camino A+).

Requiere MISTRAL_API_KEY. Ejecutar acotado:

    make test-mistral

Modelo: mistral-medium-3.5 con reasoning_effort=high.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from strands.models.mistral import MistralModel

from smart_ai_sys_admin.agent.config import load_agent_config
from smart_ai_sys_admin.agent.factory import AgentFactory
from smart_ai_sys_admin.agent.providers import ShellMistralModel
from tests.integration.mistral.conftest import (
    MISTRAL_POC_MODEL,
    MISTRAL_REASONING_EFFORT,
    collect_strands_stream,
    extract_visible_text,
    first_tool_call,
    mistral_client,
    remote_ssh_tool_spec,
    requires_mistral_api_key,
    strands_tool_spec_from_openai,
    synthetic_admin_tools,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mistral,
    requires_mistral_api_key,
]


def test_target_model_is_available_and_capable() -> None:
    """El modelo objetivo existe en la cuenta y soporta chat, tools y reasoning."""
    with mistral_client() as client:
        models = {m.id: m for m in client.models.list().data}

    assert MISTRAL_POC_MODEL in models, f"{MISTRAL_POC_MODEL} no listado en la API"
    caps = models[MISTRAL_POC_MODEL].capabilities
    assert caps.completion_chat is True
    assert caps.function_calling is True
    assert caps.reasoning is True


@pytest.mark.asyncio
async def test_chat_with_reasoning_high() -> None:
    """Chat básico con reasoning high devuelve contenido utilizable."""
    with mistral_client() as client:
        response = await client.chat.complete_async(
            model=MISTRAL_POC_MODEL,
            messages=[{"role": "user", "content": "Reply with exactly: MISTRAL_POC_OK"}],
            max_tokens=128,
            stream=False,
            reasoning_effort=MISTRAL_REASONING_EFFORT,
        )

    message = response.choices[0].message
    text = extract_visible_text(message.content).upper()
    assert message.tool_calls in (None, []) or len(message.tool_calls) == 0
    assert "MISTRAL_POC_OK" in text or "POC" in text or len(text) > 0


@pytest.mark.asyncio
async def test_single_tool_call_remote_ssh_shape() -> None:
    """Function calling con esquema tipo remote_ssh_command y reasoning high."""
    tools = [remote_ssh_tool_spec()]
    with mistral_client() as client:
        response = await client.chat.complete_async(
            model=MISTRAL_POC_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Call remote_ssh_command once with command 'uname -a'. "
                        "Do not explain; only use the tool."
                    ),
                }
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=256,
            stream=False,
            reasoning_effort=MISTRAL_REASONING_EFFORT,
        )

    parsed = first_tool_call(response.choices[0].message)
    assert parsed is not None
    name, args = parsed
    assert name == "remote_ssh_command"
    assert args.get("command") == "uname -a"


@pytest.mark.asyncio
async def test_tool_selection_with_many_schemas() -> None:
    """Con ~20 tools sintéticas + remote_ssh_command, el modelo elige la correcta."""
    tools = synthetic_admin_tools(count=20)
    with mistral_client() as client:
        response = await client.chat.complete_async(
            model=MISTRAL_POC_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Use remote_ssh_command to run: echo mistral-many-tools-ok. "
                        "Only invoke that tool."
                    ),
                }
            ],
            tools=tools,
            tool_choice="auto",
            max_tokens=512,
            stream=False,
            reasoning_effort=MISTRAL_REASONING_EFFORT,
        )

    parsed = first_tool_call(response.choices[0].message)
    assert parsed is not None
    name, args = parsed
    assert name == "remote_ssh_command"
    assert "mistral-many-tools-ok" in args.get("command", "")


@pytest.mark.asyncio
async def test_strands_mistral_model_streams_text() -> None:
    """Strands MistralModel: streaming de texto sin error de formato."""
    model = MistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        max_tokens=32,
        stream=True,
        temperature=0.1,
    )
    messages = [{"role": "user", "content": [{"text": "Say hi in one short word."}]}]

    async with collect_strands_stream(model.stream(messages)) as events:
        pass

    assert any("messageStart" in event for event in events)
    assert any("contentBlockDelta" in event for event in events)
    assert any(event.get("messageStop", {}).get("stopReason") == "end_turn" for event in events)


@pytest.mark.asyncio
async def test_strands_mistral_model_single_tool_use() -> None:
    """Strands MistralModel: emite tool_use con stopReason tool_use."""
    tool = strands_tool_spec_from_openai(remote_ssh_tool_spec())
    model = MistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        max_tokens=128,
        stream=True,
        temperature=0.0,
    )
    messages = [
        {
            "role": "user",
            "content": [{"text": "Invoke remote_ssh_command with command 'id'."}],
        }
    ]

    async with collect_strands_stream(model.stream(messages, tool_specs=[tool])) as events:
        pass

    tool_starts = [
        event["contentBlockStart"]["start"]["toolUse"]["name"]
        for event in events
        if event.get("contentBlockStart", {}).get("start", {}).get("toolUse")
    ]
    stop_reasons = [
        event["messageStop"]["stopReason"] for event in events if "messageStop" in event
    ]

    assert "remote_ssh_command" in tool_starts
    assert "tool_use" in stop_reasons


@pytest.mark.asyncio
async def test_strands_format_request_includes_many_tools() -> None:
    """El adaptador Strands serializa correctamente un lote grande de tool_specs."""
    openai_tools = synthetic_admin_tools(count=15)
    strands_tools = [strands_tool_spec_from_openai(t) for t in openai_tools]
    model = MistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        max_tokens=64,
        stream=False,
    )
    request = model.format_request(
        messages=[{"role": "user", "content": [{"text": "probe"}]}],
        tool_specs=strands_tools,
    )

    assert request["model"] == MISTRAL_POC_MODEL
    assert len(request["tools"]) == len(strands_tools)
    names = {t["function"]["name"] for t in request["tools"]}
    assert "remote_ssh_command" in names
    remote = next(t for t in request["tools"] if t["function"]["name"] == "remote_ssh_command")
    assert remote["function"]["parameters"]["required"] == ["command"]


@pytest.mark.asyncio
async def test_reasoning_high_rejects_unsupported_effort_values() -> None:
    """mistral-medium-3.5 solo admite reasoning_effort high|none (documenta restricción)."""
    with mistral_client() as client:
        with pytest.raises(Exception) as exc_info:
            await client.chat.complete_async(
                model=MISTRAL_POC_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
                stream=False,
                reasoning_effort="medium",
            )

    assert "reasoning_effort" in str(exc_info.value).lower() or "400" in str(exc_info.value)


def test_shell_mistral_model_reasoning_in_request() -> None:
    """ShellMistralModel inyecta reasoning_effort=high en cada request."""
    model = ShellMistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        stream=False,
    )
    request = model.format_request(
        messages=[{"role": "user", "content": [{"text": "probe"}]}],
    )
    assert request["reasoning_effort"] == MISTRAL_REASONING_EFFORT


@pytest.mark.asyncio
async def test_shell_mistral_stream_with_reasoning_high() -> None:
    """ShellMistralModel: streaming con reasoning high vía wrapper Strands."""
    model = ShellMistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        max_tokens=512,
        stream=True,
        temperature=0.1,
        reasoning_effort="high",
    )
    messages = [{"role": "user", "content": [{"text": "Say hi in one short word."}]}]

    async with collect_strands_stream(model.stream(messages)) as events:
        pass

    assert any("messageStart" in event for event in events)
    assert any("contentBlockDelta" in event for event in events)
    stop_reasons = [
        event["messageStop"]["stopReason"] for event in events if "messageStop" in event
    ]
    assert stop_reasons
    assert stop_reasons[0] in {"end_turn", "max_tokens"}


@pytest.mark.asyncio
async def test_shell_mistral_tool_use_with_reasoning_high() -> None:
    """ShellMistralModel: tool_use con reasoning_effort=high."""
    tool = strands_tool_spec_from_openai(remote_ssh_tool_spec())
    model = ShellMistralModel(
        api_key=os.environ["MISTRAL_API_KEY"],
        model_id=MISTRAL_POC_MODEL,
        max_tokens=256,
        stream=True,
        temperature=0.1,
        reasoning_effort="high",
    )
    messages = [
        {
            "role": "user",
            "content": [{"text": "Invoke remote_ssh_command with command 'id'."}],
        }
    ]

    async with collect_strands_stream(model.stream(messages, tool_specs=[tool])) as events:
        pass

    tool_starts = [
        event["contentBlockStart"]["start"]["toolUse"]["name"]
        for event in events
        if event.get("contentBlockStart", {}).get("start", {}).get("toolUse")
    ]
    stop_reasons = [
        event["messageStop"]["stopReason"] for event in events if "messageStop" in event
    ]

    assert "remote_ssh_command" in tool_starts
    assert "tool_use" in stop_reasons


def test_factory_builds_shell_mistral_from_config(
    fixtures_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AgentFactory construye ShellMistralModel desde agent.conf."""
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    prompts_dir = conf_dir / "system_prompts"
    prompts_dir.mkdir()
    (prompts_dir / "test.md").write_text("test prompt", encoding="utf-8")
    payload = {
        "version": 1,
        "provider": "mistral",
        "agent": {"streaming": True, "conversation": {"strategy": "none"}},
        "providers": {
            "mistral": {
                "system_prompt": "system_prompts/test.md",
                "model_id": MISTRAL_POC_MODEL,
                "api_key_env": "MISTRAL_API_KEY",
                "reasoning_effort": "high",
                "params": {"max_tokens": 16184},
            }
        },
        "tools": {"default": [], "remote_command": {}, "consent": {"bypass": True}},
        "mcp": {"enabled": False, "transports": []},
    }
    config_path = conf_dir / "agent.conf"
    config_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("MISTRAL_API_KEY", os.environ["MISTRAL_API_KEY"])

    config = load_agent_config()
    factory = AgentFactory(config)
    model = factory._build_mistral_model(config.provider_config())  # type: ignore[arg-type]
    assert isinstance(model, ShellMistralModel)
    assert model.reasoning_effort == "high"
    assert model.get_config()["max_tokens"] == 16184
