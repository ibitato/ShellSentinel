"""Pruebas para la carga de configuración del agente."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smart_ai_sys_admin.agent.config import (
    AgentConfigError,
    BedrockProviderConfig,
    CerebrasProviderConfig,
    LMStudioProviderConfig,
    LocalProviderConfig,
    OpenAIProviderConfig,
    load_agent_config,
)


def test_load_agent_config_success(minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    assert config.provider == "openai"
    assert config.tools.remote_command.timeout_seconds == 60
    assert config.tools.remote_command.max_output_chars == 5000
    assert config.tools.consent_bypass is True
    assert config.mcp.enabled is False


def test_load_agent_config_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.conf"
    with pytest.raises(AgentConfigError, match="No se encontró"):
        load_agent_config(missing)


def test_load_agent_config_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad.conf"
    bad.write_text("{invalid", encoding="utf-8")
    with pytest.raises(AgentConfigError, match="JSON válido"):
        load_agent_config(bad)


def test_load_agent_config_unsupported_version(minimal_agent_conf: Path):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["version"] = 2
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AgentConfigError, match="Versión"):
        load_agent_config(minimal_agent_conf)


def test_load_agent_config_invalid_provider(minimal_agent_conf: Path):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["provider"] = "unknown"
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AgentConfigError, match="proveedor válido"):
        load_agent_config(minimal_agent_conf)


def test_load_agent_config_provider_not_defined(minimal_agent_conf: Path):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["provider"] = "openai"
    del payload["providers"]["openai"]
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AgentConfigError, match="proveedor seleccionado"):
        load_agent_config(minimal_agent_conf)


def test_load_agent_config_missing_system_prompt(minimal_agent_conf: Path):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["providers"]["openai"]["system_prompt"] = "missing.md"
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AgentConfigError, match="system prompt"):
        load_agent_config(minimal_agent_conf)


def test_openai_max_tokens_migration(minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    provider = config.provider_config()
    assert isinstance(provider, OpenAIProviderConfig)
    assert "max_completion_tokens" in provider.params
    assert provider.params["max_completion_tokens"] == 512


@pytest.mark.parametrize(
    ("provider_name", "expected_type"),
    [
        ("bedrock", BedrockProviderConfig),
        ("openai", OpenAIProviderConfig),
        ("local", LocalProviderConfig),
        ("lmstudio", LMStudioProviderConfig),
        ("cerebras", CerebrasProviderConfig),
    ],
)
def test_provider_parsing(
    minimal_agent_conf: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    expected_type: type,
):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["provider"] = provider_name
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    assert isinstance(config.provider_config(), expected_type)


def test_conversation_strategy_summarizing(
    minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch
):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["agent"]["conversation"] = {
        "strategy": "summarizing",
        "summary_ratio": 0.2,
        "preserve_recent_messages": 5,
    }
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    assert config.options.conversation.strategy == "summarizing"


def test_mcp_transport_validation(minimal_agent_conf: Path):
    payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
    payload["mcp"] = {
        "enabled": True,
        "transports": [{"type": "stdio"}],
    }
    minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AgentConfigError, match="identificador"):
        load_agent_config(minimal_agent_conf)


def test_env_override_agent_config_file(minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    assert config.config_path == minimal_agent_conf.resolve()
