"""Pruebas para AgentFactory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from smart_ai_sys_admin.agent.config import (
    MISTRAL_DEFAULT_MAX_TOKENS,
    AgentConfigError,
    load_agent_config,
)
from smart_ai_sys_admin.agent.factory import AgentFactory
from smart_ai_sys_admin.agent.providers import ShellMistralModel


@pytest.fixture
def agent_config(minimal_agent_conf, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    return load_agent_config()


@patch("smart_ai_sys_admin.agent.factory.Agent")
@patch("smart_ai_sys_admin.agent.factory.OpenAIModel")
def test_build_agent_openai(
    mock_model_cls, mock_agent_cls, agent_config, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_agent_cls.return_value = MagicMock()
    factory = AgentFactory(agent_config)
    result = factory.build_agent(tools=[])
    assert result.agent is mock_agent_cls.return_value
    mock_model_cls.assert_called_once()


def test_build_openai_missing_api_key(agent_config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    factory = AgentFactory(agent_config)
    with pytest.raises(AgentConfigError, match="OPENAI_API_KEY"):
        factory._build_openai_model(agent_config.provider_config())  # type: ignore[arg-type]


@patch("smart_ai_sys_admin.agent.factory.Agent")
@patch("smart_ai_sys_admin.agent.factory.OllamaModel")
def test_build_local_model(
    mock_model_cls, mock_agent_cls, minimal_agent_conf, monkeypatch: pytest.MonkeyPatch
):
    payload = minimal_agent_conf.read_text(encoding="utf-8")
    import json

    data = json.loads(payload)
    data["provider"] = "local"
    minimal_agent_conf.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    mock_agent_cls.return_value = MagicMock()
    factory = AgentFactory(config)
    factory.build_agent()
    mock_model_cls.assert_called_once()


def test_conversation_manager_sliding_window(agent_config):
    factory = AgentFactory(agent_config)
    manager = factory._build_conversation_manager(agent_config.options)
    assert manager is not None


def test_conversation_manager_summarizing(minimal_agent_conf, monkeypatch: pytest.MonkeyPatch):
    import json

    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["agent"]["conversation"] = {
        "strategy": "summarizing",
        "summary_ratio": 0.25,
        "preserve_recent_messages": 4,
    }
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    factory = AgentFactory(config)
    manager = factory._build_conversation_manager(config.options)
    assert manager is not None


def test_conversation_manager_none(minimal_agent_conf, monkeypatch: pytest.MonkeyPatch):
    import json

    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["agent"]["conversation"] = {"strategy": "none"}
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    factory = AgentFactory(config)
    manager = factory._build_conversation_manager(config.options)
    assert manager is not None


def test_factory_properties(agent_config):
    factory = AgentFactory(agent_config)
    assert factory.remote_command.timeout_seconds == 60
    assert factory.consent_bypass is True
    assert factory.mcp_config.enabled is False


def test_build_mistral_model_defaults(minimal_agent_conf, monkeypatch):
    import json

    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["provider"] = "mistral"
    payload["providers"]["mistral"] = {
        "system_prompt": "system_prompts/test.md",
        "model_id": "mistral-medium-3.5",
        "api_key_env": "MISTRAL_API_KEY",
        "reasoning_effort": "high",
        "params": {"temperature": 0.3},
    }
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key")
    config = load_agent_config()
    factory = AgentFactory(config)
    model = factory._build_mistral_model(config.provider_config())  # type: ignore[arg-type]
    assert isinstance(model, ShellMistralModel)
    assert model.get_config()["max_tokens"] == MISTRAL_DEFAULT_MAX_TOKENS
    assert model.reasoning_effort == "high"


def test_build_mistral_missing_api_key(minimal_agent_conf, monkeypatch):
    import json

    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["provider"] = "mistral"
    payload["providers"]["mistral"] = {
        "system_prompt": "system_prompts/test.md",
        "model_id": "mistral-medium-3.5",
        "api_key_env": "MISTRAL_API_KEY",
        "params": {},
    }
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    config = load_agent_config()
    factory = AgentFactory(config)
    with pytest.raises(AgentConfigError, match="MISTRAL_API_KEY"):
        factory._build_mistral_model(config.provider_config())  # type: ignore[arg-type]
