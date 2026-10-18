"""Pruebas del proveedor Google Gemini (configuración, fábrica y etiqueta de estado)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from smart_ai_sys_admin.agent.config import (
    DEFAULT_CACHE_CONFIGS,
    GEMINI_DEFAULT_API_KEY_ENV,
    AgentConfig,
    AgentConfigError,
    GeminiProviderConfig,
    ProviderCacheConfig,
    load_agent_config,
)
from smart_ai_sys_admin.agent.factory import AgentFactory
from smart_ai_sys_admin.agent.runtime import AgentRuntime
from tests.conftest import FakeSSHConnectionManager

KEY_ENVS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "MY_GEMINI_KEY")

ConfigBuilder = Callable[..., AgentConfig]


@pytest.fixture(autouse=True)
def _clean_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in KEY_ENVS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def gemini_config(minimal_agent_conf: Path) -> ConfigBuilder:
    """Carga el fixture con ``provider: gemini`` aplicando los cambios indicados al bloque."""

    def _build(block: dict[str, Any] | None = None, *, replace: bool = False) -> AgentConfig:
        payload = json.loads(minimal_agent_conf.read_text(encoding="utf-8"))
        payload["provider"] = "gemini"
        if replace:
            payload["providers"]["gemini"] = dict(block or {})
        elif block:
            payload["providers"]["gemini"].update(block)
        minimal_agent_conf.write_text(json.dumps(payload), encoding="utf-8")
        return load_agent_config(minimal_agent_conf)

    return _build


# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------


def test_gemini_config_parses_fixture(gemini_config: ConfigBuilder):
    config = gemini_config()
    provider = config.provider_config()
    assert isinstance(provider, GeminiProviderConfig)
    assert provider.model_id == "gemini-test"
    assert provider.api_key_env == "GEMINI_API_KEY"
    assert provider.show_thinking is False
    assert dict(provider.client_args) == {}
    # ``max_tokens`` se normaliza al nombre que entiende GenerateContentConfig.
    assert dict(provider.params) == {"temperature": 0.2, "max_output_tokens": 1024}


def test_gemini_api_key_env_defaults_when_absent(gemini_config: ConfigBuilder):
    config = gemini_config(
        {"system_prompt": "system_prompts/test.md", "model_id": "gemini-3.8-flash"},
        replace=True,
    )
    provider = config.provider_config()
    assert isinstance(provider, GeminiProviderConfig)
    assert provider.api_key_env == GEMINI_DEFAULT_API_KEY_ENV
    assert dict(provider.params) == {}
    assert provider.cache == ProviderCacheConfig(enabled=False)


def test_gemini_cache_defaults_disabled_and_overridable(gemini_config: ConfigBuilder):
    assert DEFAULT_CACHE_CONFIGS["gemini"] == ProviderCacheConfig(enabled=False)
    assert gemini_config().provider_config().cache.enabled is False
    enabled = gemini_config({"cache": {"enabled": True}}).provider_config().cache
    assert enabled.enabled is True


def test_gemini_explicit_max_output_tokens_wins(gemini_config: ConfigBuilder):
    config = gemini_config({"params": {"max_tokens": 10, "max_output_tokens": 20}})
    params = dict(config.provider_config().params)  # type: ignore[attr-defined]
    assert params == {"max_output_tokens": 20}


def test_gemini_client_args_and_show_thinking(gemini_config: ConfigBuilder):
    config = gemini_config(
        {
            "show_thinking": True,
            "api_key_env": "MY_GEMINI_KEY",
            "client_args": {"http_options": {"timeout": 60000}},
        }
    )
    provider = config.provider_config()
    assert isinstance(provider, GeminiProviderConfig)
    assert provider.show_thinking is True
    assert provider.api_key_env == "MY_GEMINI_KEY"
    assert dict(provider.client_args) == {"http_options": {"timeout": 60000}}


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ({"model_id": ""}, "model_id"),
        ({"model_id": None}, "model_id"),
        ({"api_key_env": ""}, "api_key_env"),
        ({"api_key_env": 42}, "api_key_env"),
        ({"api_key": "secret"}, "no admite 'api_key'"),
        ({"client_args": ["x"]}, "client_args"),
        ({"params": "temperature=1"}, "params"),
        ({"cache": {"enabled": "yes"}}, "providers.gemini.cache.enabled"),
    ],
)
def test_gemini_config_validation_errors(gemini_config: ConfigBuilder, block, message):
    with pytest.raises(AgentConfigError, match=message):
        gemini_config(block)


def test_gemini_requires_system_prompt(gemini_config: ConfigBuilder):
    with pytest.raises(AgentConfigError, match="system_prompt"):
        gemini_config({"model_id": "gemini-3.8-flash"}, replace=True)


# ----------------------------------------------------------------------
# Fábrica
# ----------------------------------------------------------------------


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_builds_gemini_model_with_env_key(
    mock_model_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    config = gemini_config()
    factory = AgentFactory(config)

    model = factory._build_model(config.provider_config())

    assert model is mock_model_cls.return_value
    mock_model_cls.assert_called_once_with(
        client_args={"api_key": "gemini-secret"},
        model_id="gemini-test",
        params={"temperature": 0.2, "max_output_tokens": 1024},
    )
    assert factory.cache_enabled is False


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_falls_back_to_google_api_key(
    mock_model_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret")
    config = gemini_config()
    AgentFactory(config)._build_model(config.provider_config())
    assert mock_model_cls.call_args.kwargs["client_args"] == {"api_key": "google-secret"}


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_prefers_configured_api_key_env(
    mock_model_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MY_GEMINI_KEY", "custom-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "default-secret")
    config = gemini_config({"api_key_env": "MY_GEMINI_KEY"})
    AgentFactory(config)._build_model(config.provider_config())
    assert mock_model_cls.call_args.kwargs["client_args"] == {"api_key": "custom-secret"}


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_merges_client_args_and_omits_empty_params(
    mock_model_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    config = gemini_config({"client_args": {"http_options": {"timeout": 1000}}, "params": {}})
    AgentFactory(config)._build_model(config.provider_config())
    kwargs = mock_model_cls.call_args.kwargs
    assert kwargs["client_args"] == {"http_options": {"timeout": 1000}, "api_key": "gemini-secret"}
    assert "params" not in kwargs


def test_factory_missing_key_raises_spanish_error(gemini_config: ConfigBuilder):
    config = gemini_config({"api_key_env": "MY_GEMINI_KEY"})
    factory = AgentFactory(config)
    with pytest.raises(AgentConfigError) as excinfo:
        factory._build_model(config.provider_config())
    message = str(excinfo.value)
    assert "No se encontró la clave de Gemini" in message
    assert "MY_GEMINI_KEY" in message
    assert "GEMINI_API_KEY" in message and "GOOGLE_API_KEY" in message


def test_factory_rejects_api_key_inside_client_args(
    gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    config = gemini_config({"client_args": {"api_key": "inline-secret"}})
    with pytest.raises(AgentConfigError, match="client_args no admite 'api_key'"):
        AgentFactory(config)._build_model(config.provider_config())


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_allows_vertex_ai_without_api_key(mock_model_cls, gemini_config: ConfigBuilder):
    config = gemini_config(
        {"client_args": {"vertexai": True, "project": "demo", "location": "europe-west1"}}
    )
    AgentFactory(config)._build_model(config.provider_config())
    assert mock_model_cls.call_args.kwargs["client_args"] == {
        "vertexai": True,
        "project": "demo",
        "location": "europe-west1",
    }


@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_factory_gemini_cache_enabled_warns_and_ignores(
    mock_model_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch, caplog
):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    config = gemini_config({"cache": {"enabled": True}})
    factory = AgentFactory(config)
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.factory"):
        factory._build_model(config.provider_config())
    assert "cache_config" not in mock_model_cls.call_args.kwargs
    assert any("providers.gemini.cache" in record.message for record in caplog.records)
    assert factory.cache_enabled is False


@patch("smart_ai_sys_admin.agent.factory.Agent")
@patch("smart_ai_sys_admin.agent.factory.GeminiModel")
def test_build_agent_gemini_propagates_show_thinking(
    mock_model_cls, mock_agent_cls, gemini_config: ConfigBuilder, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    mock_agent_cls.return_value = MagicMock()
    config = gemini_config({"show_thinking": True})
    result = AgentFactory(config).build_agent(tools=[])
    assert result.agent is mock_agent_cls.return_value
    assert mock_agent_cls.call_args.kwargs["model"] is mock_model_cls.return_value
    assert result.agent.show_thinking is True


# ----------------------------------------------------------------------
# Etiqueta de proveedor (pie de pantalla y /status)
# ----------------------------------------------------------------------


def test_runtime_label_for_gemini(gemini_config: ConfigBuilder):
    config = gemini_config()
    runtime = AgentRuntime(FakeSSHConnectionManager())
    runtime._config = config
    assert runtime._format_provider_label(config.provider_config()) == "Google Gemini"
