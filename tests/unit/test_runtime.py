"""Pruebas para AgentRuntime y MCPManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from smart_ai_sys_admin.agent.config import MCPConfig, MCPTransportConfig
from smart_ai_sys_admin.agent.runtime import AgentRuntime, MCPManager


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
