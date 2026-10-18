"""Pruebas unitarias del arnés e2e (guardas, registro de proveedores, agent.conf, servidor SSH)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from strands.hooks import AfterToolCallEvent, BeforeModelCallEvent, BeforeToolCallEvent

from smart_ai_sys_admin.agent.config import load_agent_config
from smart_ai_sys_admin.agent.factory import AgentFactory
from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.fake_model import split_json, text_turn, tool_turn
from tests.e2e.guards import GUARD_SENTINEL, E2EGuard
from tests.e2e.providers import (
    MAX_MODEL_CALLS_ENV,
    PROVIDERS_ENV,
    REGISTRY,
    live_params,
    max_model_calls,
    select_providers,
)
from tests.e2e.ssh_server import SENTINEL_HOSTNAME, CommandResult, ScriptedSSHServer, split_compound

# ---------------------------------------------------------------------- E2EGuard


def _before_model(agent: MagicMock) -> BeforeModelCallEvent:
    return BeforeModelCallEvent(agent=agent)


def test_guard_cancels_model_call_beyond_budget():
    agent = MagicMock()
    guard = E2EGuard(max_model_calls=2, deadline_s=60)

    first = _before_model(agent)
    second = _before_model(agent)
    third = _before_model(agent)
    guard._before_model(first)
    guard._before_model(second)
    guard._before_model(third)

    assert first.cancel is False and second.cancel is False
    assert isinstance(third.cancel, str) and third.cancel.startswith(GUARD_SENTINEL)
    assert guard.model_calls == 3
    assert guard.tripped == "model calls > 2"


def test_guard_cancels_model_call_after_deadline():
    guard = E2EGuard(max_model_calls=10, deadline_s=0.01)
    time.sleep(0.02)

    event = _before_model(MagicMock())
    guard._before_model(event)

    assert isinstance(event.cancel, str) and "deadline" in event.cancel
    assert guard.tripped is not None and "deadline" in guard.tripped


def test_guard_records_tool_inputs_and_results():
    agent = MagicMock()
    guard = E2EGuard()
    tool_use = {"toolUseId": "t1", "name": "remote_ssh_command", "input": {"command": "uname -a"}}
    guard._before_tool(
        BeforeToolCallEvent(agent=agent, selected_tool=None, tool_use=tool_use, invocation_state={})
    )
    guard._before_tool(
        BeforeToolCallEvent(
            agent=agent,
            selected_tool=None,
            tool_use={"toolUseId": "t2", "name": "remote_ssh_command", "input": {}},
            invocation_state={},
        )
    )
    guard._after_tool(
        AfterToolCallEvent(
            agent=agent,
            selected_tool=None,
            tool_use=tool_use,
            invocation_state={},
            result={"toolUseId": "t1", "status": "success", "content": [{"text": "Exit code: 0"}]},
        )
    )

    assert guard.commands() == ["uname -a", None]
    assert guard.tool_uses[0].result_status == "success"
    assert "Exit code: 0" in guard.tool_uses[0].result_text
    assert guard.tool_uses[1].result_status is None
    assert "remote_ssh_command" in guard.debug_report()


# ---------------------------------------------------------------------- providers


def test_select_providers_defaults_to_whole_registry():
    assert select_providers({}) == list(REGISTRY)


def test_select_providers_filters_and_deduplicates():
    selected = select_providers({PROVIDERS_ENV: "mistral, openai,mistral"})
    assert [provider.name for provider in selected] == ["mistral", "openai"]


def test_select_providers_rejects_unknown_name():
    with pytest.raises(pytest.UsageError, match="desconocido"):
        select_providers({PROVIDERS_ENV: "gemini"})


def test_live_params_skip_without_api_key():
    params = live_params({PROVIDERS_ENV: "openai,mistral", "OPENAI_API_KEY": "x"})
    by_id = {param.id: param for param in params}
    assert not by_id["openai"].marks
    assert by_id["mistral"].marks and by_id["mistral"].marks[0].name == "skipif"


def test_max_model_calls_env_override():
    provider = REGISTRY[0]
    assert max_model_calls(provider, {}) == provider.max_model_calls
    assert max_model_calls(provider, {MAX_MODEL_CALLS_ENV: "3"}) == 3
    with pytest.raises(pytest.UsageError):
        max_model_calls(provider, {MAX_MODEL_CALLS_ENV: "many"})


# ---------------------------------------------------------------------- agent_conf


def test_write_agent_conf_offline_defaults(tmp_path: Path):
    conf_path = write_agent_conf(tmp_path / "conf")
    config = load_agent_config(conf_path)
    factory = AgentFactory(config)

    assert config.provider == "openai"
    assert factory.default_tool_names == ()
    assert factory.remote_command.timeout_seconds == 60
    assert factory.remote_command.max_output_chars == 500
    assert factory.consent_bypass is True
    assert config.mcp.enabled is False
    assert "You are a test system prompt" in config.provider_config().system_prompt
    payload = json.loads(conf_path.read_text(encoding="utf-8"))
    assert set(payload["providers"]) == {"openai"}


def test_write_agent_conf_mistral_live_shape(tmp_path: Path):
    conf_path = write_agent_conf(
        tmp_path / "conf",
        provider="mistral",
        model_id="zai-glm-5-3",
        api_key_env="SOME_KEY_ENV",
        provider_block={"params": {"temperature": 0.3}},
        cache_key="shell-sentinel-e2e-test",
        timeout_seconds=30,
    )
    payload = json.loads(conf_path.read_text(encoding="utf-8"))
    block = payload["providers"]["mistral"]

    assert payload["provider"] == "mistral"
    assert block["model_id"] == "zai-glm-5-3"
    assert block["api_key_env"] == "SOME_KEY_ENV"
    assert block["params"] == {"temperature": 0.3}
    assert block["cache"] == {"enabled": True, "cache_key": "shell-sentinel-e2e-test"}
    assert "SOME_KEY_ENV" in conf_path.read_text(encoding="utf-8")
    config = load_agent_config(conf_path)
    assert config.provider_config().cache.cache_key == "shell-sentinel-e2e-test"


def test_write_agent_conf_openai_key_env_goes_to_client_args(tmp_path: Path):
    conf_path = write_agent_conf(tmp_path / "conf", provider="openai", api_key_env="OTHER_KEY")
    payload = json.loads(conf_path.read_text(encoding="utf-8"))
    assert payload["providers"]["openai"]["client_args"]["api_key_env"] == "OTHER_KEY"


# ---------------------------------------------------------------------- fake model


def test_split_json_fragments_recompose_payload():
    payload = json.dumps({"command": "uname -a"})
    assert "".join(split_json(payload, 3)) == payload
    assert split_json(payload, None) == [payload]
    with pytest.raises(AssertionError):
        split_json(payload, ["{", "oops"])


def test_turn_builders_shape():
    turn = tool_turn("remote_ssh_command", {"command": "uname -a"}, split=2)
    assert turn[0] == {"messageStart": {"role": "assistant"}}
    assert turn[1]["contentBlockStart"]["start"]["toolUse"]["name"] == "remote_ssh_command"
    deltas = [event for event in turn if "contentBlockDelta" in event]
    assert len(deltas) == 2
    assert turn[-2] == {"messageStop": {"stopReason": "tool_use"}}
    assert "usage" in turn[-1]["metadata"]

    text = text_turn("hola", usage={"inputTokens": 1, "outputTokens": 1, "totalTokens": 2})
    assert text[2] == {"contentBlockDelta": {"delta": {"text": "hola"}}}
    assert text[-1]["metadata"]["usage"]["totalTokens"] == 2


# ---------------------------------------------------------------------- ssh server guion


def test_split_compound_commands():
    assert split_compound("uname -a; echo '---'; df -h | head -n 5 && free -h") == [
        "uname -a",
        "echo '---'",
        "df -h | head -n 5",
        "free -h",
    ]


def test_resolve_prefers_exact_then_patterns_then_default():
    server = ScriptedSSHServer()
    server.script["uname -a"] = CommandResult(0, "exact\n")
    server.load_hardware_profile()

    assert server.resolve("uname -a").stdout == "exact\n"
    hardware = server.resolve("hostname; lscpu | head -n 5")
    assert SENTINEL_HOSTNAME in hardware.stdout and "Model name" in hardware.stdout
    assert hardware.exit_code == 0
    missing = server.resolve("frobnicate --now")
    assert missing.exit_code == 127 and "command not found" in missing.stderr


def test_resolve_combines_exit_code_and_delay():
    server = ScriptedSSHServer()
    server.script["a"] = CommandResult(0, "A", delay=0.1)
    server.script["b"] = CommandResult(2, "", "bad", delay=0.2)

    result = server.resolve("a && b")
    assert (result.exit_code, result.stdout, result.stderr) == (2, "A", "bad")
    assert result.delay == pytest.approx(0.3)
