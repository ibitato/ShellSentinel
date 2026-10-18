"""Pruebas para AgentRuntime y MCPManager."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from strands.agent.agent_result import AgentResult
from strands.telemetry.metrics import EventLoopMetrics

from smart_ai_sys_admin.agent.config import MCPConfig, MCPTransportConfig
from smart_ai_sys_admin.agent.mcp_manager import MCPServerStatus
from smart_ai_sys_admin.agent.runtime import AgentRuntime, MCPManager
from smart_ai_sys_admin.localization import _


def test_agent_summary_before_initialize(agent_runtime: AgentRuntime):
    summary = agent_runtime.agent_summary()
    assert summary["ready"] is False
    assert summary["error"] is None


@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_initialize_missing_config(mock_load, agent_runtime: AgentRuntime):
    from smart_ai_sys_admin.agent.config import AgentConfigError

    mock_load.side_effect = AgentConfigError("missing")
    agent_runtime.initialize()
    assert agent_runtime.ready is False
    assert agent_runtime.error_message is not None


@patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[])
@patch("smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent")
@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_initialize_success(
    mock_load,
    mock_build,
    mock_mcp,
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
):
    from smart_ai_sys_admin.agent.config import load_agent_config
    from smart_ai_sys_admin.agent.factory import AgentBuildResult

    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    mock_load.return_value = config
    agent = MagicMock()
    mock_build.return_value = AgentBuildResult(agent=agent, mcp_config=config.mcp)

    agent_runtime.initialize()

    assert agent_runtime.ready is True
    assert agent.ssh_manager is agent_runtime._connection_manager
    assert agent.remote_command_timeout == 60
    assert agent.remote_command_max_output_chars == 5000


@patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[])
@patch("smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent")
@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_initialize_factory_failure(
    mock_load,
    mock_build,
    mock_mcp,
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
):
    from smart_ai_sys_admin.agent.config import load_agent_config

    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    mock_load.return_value = load_agent_config()
    mock_build.side_effect = RuntimeError("boom")
    agent_runtime.initialize()
    assert agent_runtime.ready is False
    assert agent_runtime.error_message is not None


def test_invoke_requires_ready(agent_runtime: AgentRuntime):
    with pytest.raises(RuntimeError):
        agent_runtime.invoke("hello")


@patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[])
@patch("smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent")
@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_invoke_returns_rendered_result(
    mock_load,
    mock_build,
    mock_mcp,
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
):
    from smart_ai_sys_admin.agent.config import load_agent_config
    from smart_ai_sys_admin.agent.factory import AgentBuildResult

    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    mock_load.return_value = config
    agent = MagicMock(return_value="hello")
    mock_build.return_value = AgentBuildResult(agent=agent, mcp_config=config.mcp)
    agent_runtime.initialize()
    result = agent_runtime.invoke("test prompt")
    assert "hello" in result


def test_render_agent_result_strips_thinking(agent_runtime: AgentRuntime):
    agent_runtime._hide_thinking = True
    rendered = agent_runtime._render_agent_result("text <think>secret</think> visible")
    assert "secret" not in rendered
    assert "visible" in rendered


def test_mcp_manager_disabled_returns_empty():
    manager = MCPManager(
        MCPConfig(enabled=False, load_server_tools=True, transports=()),
        MagicMock(),
    )
    assert manager.activate() == []


def test_mcp_manager_stdio_missing_command_logs_warning():
    logger = MagicMock()
    transport = MCPTransportConfig(identifier="bad", transport_type="stdio", command=None)
    config = MCPConfig(enabled=True, load_server_tools=True, transports=(transport,))
    manager = MCPManager(config, logger)
    tools = manager.activate()
    assert tools == []
    assert logger.warning.called


def test_shutdown_idempotent(agent_runtime: AgentRuntime):
    agent_runtime.shutdown()
    agent_runtime.shutdown()
    assert agent_runtime.ready is False


@patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[])
@patch("smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent")
@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_agent_summary_after_initialize(
    mock_load,
    mock_build,
    mock_mcp,
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
):
    from smart_ai_sys_admin.agent.config import load_agent_config
    from smart_ai_sys_admin.agent.factory import AgentBuildResult

    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    mock_load.return_value = config
    agent = MagicMock()
    mock_build.return_value = AgentBuildResult(agent=agent, mcp_config=config.mcp)
    agent_runtime.initialize()
    summary = agent_runtime.agent_summary()
    assert summary["ready"] is True
    assert summary["provider"] == "OpenAI"
    assert summary["model"] == "gpt-test"
    assert summary["config_path"] == str(minimal_agent_conf.resolve())


def _runtime_with_statuses(agent_runtime: AgentRuntime, *statuses: MCPServerStatus) -> AgentRuntime:
    manager = MagicMock()
    manager.statuses = statuses
    agent_runtime._mcp_manager = manager
    return agent_runtime


def test_mcp_startup_report_none_without_failures(agent_runtime: AgentRuntime):
    assert agent_runtime.mcp_startup_report() is None
    _runtime_with_statuses(
        agent_runtime, MCPServerStatus("docs", "stdio", ready=True, tool_count=4)
    )
    assert agent_runtime.mcp_startup_report() is None


def test_mcp_startup_report_lists_failed_servers(agent_runtime: AgentRuntime):
    _runtime_with_statuses(
        agent_runtime,
        MCPServerStatus("docs", "stdio", ready=True, tool_count=4),
        MCPServerStatus("remote", "streamable_http", ready=False, message="cannot connect"),
    )
    report = agent_runtime.mcp_startup_report()
    assert report is not None
    assert "1 of 2 MCP servers unavailable" in report
    assert "`remote` (streamable_http): cannot connect" in report
    assert "docs" not in report


def test_agent_summary_describes_mcp_servers(agent_runtime: AgentRuntime):
    _runtime_with_statuses(
        agent_runtime,
        MCPServerStatus("docs", "stdio", ready=True, tool_count=4, message="env missing"),
        MCPServerStatus("remote", "sse", ready=False, message="HTTP 401"),
    )
    servers = agent_runtime.agent_summary()["mcp_servers"]
    assert servers == [
        "✅ `docs` (stdio): 4 tools — env missing",
        "⚠️ `remote` (sse): HTTP 401",
    ]


# ---------------------------------------------------------------- límite de turnos
def _agent_result(text: str, stop_reason: str) -> AgentResult:
    return AgentResult(
        stop_reason=stop_reason,  # type: ignore[arg-type]
        message={"role": "assistant", "content": [{"text": text}]},
        metrics=EventLoopMetrics(),
        state={},
    )


def _initialize_with_agent(
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
    agent: MagicMock,
    *,
    max_turns: object = 25,
    present: bool = True,
) -> None:
    from smart_ai_sys_admin.agent.config import load_agent_config
    from smart_ai_sys_admin.agent.factory import AgentBuildResult

    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    if present:
        payload["agent"]["max_turns"] = max_turns
    else:
        payload["agent"].pop("max_turns", None)
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    with (
        patch("smart_ai_sys_admin.agent.runtime.load_agent_config", return_value=config),
        patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[]),
        patch(
            "smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent",
            return_value=AgentBuildResult(agent=agent, mcp_config=config.mcp),
        ),
    ):
        agent_runtime.initialize()
    assert agent_runtime.ready is True


def test_invoke_passes_turn_limit_to_strands(
    agent_runtime: AgentRuntime, minimal_agent_conf, monkeypatch: pytest.MonkeyPatch
):
    agent = MagicMock(return_value=_agent_result("done", "end_turn"))
    _initialize_with_agent(agent_runtime, minimal_agent_conf, monkeypatch, agent, max_turns=7)

    assert agent_runtime.max_turns == 7
    assert agent_runtime.invoke("prompt") == "done"
    agent.assert_called_once_with("prompt", limits={"turns": 7})
    assert agent_runtime.agent_summary()["max_turns"] == 7


def test_invoke_without_turn_limit_passes_no_limits(
    agent_runtime: AgentRuntime, minimal_agent_conf, monkeypatch: pytest.MonkeyPatch
):
    agent = MagicMock(return_value=_agent_result("done", "end_turn"))
    _initialize_with_agent(agent_runtime, minimal_agent_conf, monkeypatch, agent, max_turns=None)

    assert agent_runtime.max_turns is None
    agent_runtime.invoke("prompt")
    agent.assert_called_once_with("prompt")
    assert agent_runtime.agent_summary()["max_turns"] is None


def test_invoke_renders_turn_limit_notice(
    agent_runtime: AgentRuntime,
    minimal_agent_conf,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    agent = MagicMock(return_value=_agent_result("partial answer", "limit_turns"))
    _initialize_with_agent(agent_runtime, minimal_agent_conf, monkeypatch, agent, max_turns=3)

    with caplog.at_level(logging.WARNING, logger="test.agent.runtime"):
        rendered = agent_runtime.invoke("prompt")

    notice = _("agent.invoke.turn_limit", limit=3)
    assert rendered == f"partial answer\n\n{notice}"
    assert "3 turns" in notice
    assert any(
        record.levelno == logging.WARNING and "limit_turns" in record.getMessage()
        for record in caplog.records
    )


def test_invoke_turn_limit_notice_without_text(
    agent_runtime: AgentRuntime, minimal_agent_conf, monkeypatch: pytest.MonkeyPatch
):
    agent = MagicMock(return_value=_agent_result("", "limit_turns"))
    _initialize_with_agent(agent_runtime, minimal_agent_conf, monkeypatch, agent, max_turns=3)

    assert agent_runtime.invoke("prompt") == _("agent.invoke.turn_limit", limit=3)


def test_agent_summary_has_no_turn_limit_before_initialize(agent_runtime: AgentRuntime):
    assert "max_turns" not in agent_runtime.agent_summary()
    assert agent_runtime.max_turns is None
