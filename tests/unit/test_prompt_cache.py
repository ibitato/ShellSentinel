"""Pruebas de la configuración de prompt caching por proveedor."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from strands.models.model import CacheConfig

from smart_ai_sys_admin.agent.config import (
    DEFAULT_CACHE_CONFIGS,
    AgentConfigError,
    ProviderCacheConfig,
    load_agent_config,
)
from smart_ai_sys_admin.agent.factory import (
    CACHE_KEY_PREFIX,
    AgentFactory,
    build_strands_cache_config,
    derive_cache_key,
)
from smart_ai_sys_admin.agent.runtime import AgentRuntime, summarize_cache_usage
from smart_ai_sys_admin.ui.commands import SlashCommandProcessor


def _rewrite(conf_path: Path, mutate) -> None:
    payload = json.loads(conf_path.read_text(encoding="utf-8"))
    mutate(payload)
    conf_path.write_text(json.dumps(payload), encoding="utf-8")


# ----------------------------------------------------------------------
# Carga de configuración
# ----------------------------------------------------------------------


def test_cache_defaults_when_block_absent(minimal_agent_conf: Path):
    def mutate(payload):
        for provider in payload["providers"].values():
            provider.pop("cache", None)

    _rewrite(minimal_agent_conf, mutate)
    config = load_agent_config(minimal_agent_conf)

    assert config.providers["bedrock"].cache == ProviderCacheConfig(enabled=True, strategy="auto")
    assert config.providers["openai"].cache == ProviderCacheConfig(enabled=True)
    assert config.providers["mistral"].cache == ProviderCacheConfig(enabled=True)
    assert config.providers["local"].cache.enabled is False
    assert config.providers["lmstudio"].cache.enabled is False
    assert config.providers["cerebras"].cache.enabled is False
    for provider, cfg in config.providers.items():
        assert cfg.cache == DEFAULT_CACHE_CONFIGS[provider]


def test_cache_block_overrides_only_given_keys(minimal_agent_conf: Path):
    def mutate(payload):
        payload["providers"]["bedrock"]["cache"] = {
            "ttl": "1h",
            "system_prompt_ttl": "5m",
            "tools_ttl": True,
        }
        payload["providers"]["openai"]["cache"] = {"cache_key": "  ops-team  ", "ttl": "24h"}
        payload["providers"]["mistral"]["cache"] = {"enabled": False}
        payload["providers"]["local"]["cache"] = {"enabled": True}

    _rewrite(minimal_agent_conf, mutate)
    config = load_agent_config(minimal_agent_conf)

    bedrock = config.providers["bedrock"].cache
    assert bedrock.enabled is True
    assert bedrock.strategy == "auto"
    assert bedrock.ttl == "1h"
    assert bedrock.system_prompt_ttl == "5m"
    assert bedrock.tools_ttl is True

    openai = config.providers["openai"].cache
    assert openai.enabled is True
    assert openai.cache_key == "ops-team"
    assert openai.ttl == "24h"

    assert config.providers["mistral"].cache.enabled is False
    assert config.providers["local"].cache.enabled is True


def test_cache_key_false_opts_out_of_routing(minimal_agent_conf: Path):
    _rewrite(
        minimal_agent_conf,
        lambda payload: payload["providers"]["openai"].__setitem__("cache", {"cache_key": False}),
    )
    config = load_agent_config(minimal_agent_conf)
    assert config.providers["openai"].cache.cache_key is False


@pytest.mark.parametrize(
    ("block", "match"),
    [
        ({"enabled": "yes"}, "cache.enabled"),
        ({"strategy": "manual"}, "cache.strategy"),
        ({"ttl": "2h"}, "cache.ttl"),
        ({"ttl": True}, "cache.ttl"),
        ({"system_prompt_ttl": "10m"}, "cache.system_prompt_ttl"),
        ({"tools_ttl": 5}, "cache.tools_ttl"),
        ({"cache_key": ""}, "cache.cache_key"),
        ({"cache_key": 42}, "cache.cache_key"),
        ({"unexpected": 1}, "claves desconocidas"),
        ("auto", "debe ser un objeto"),
    ],
)
def test_cache_block_invalid_values(minimal_agent_conf: Path, block, match):
    _rewrite(
        minimal_agent_conf,
        lambda payload: payload["providers"]["bedrock"].__setitem__("cache", block),
    )
    with pytest.raises(AgentConfigError, match=match):
        load_agent_config(minimal_agent_conf)


# ----------------------------------------------------------------------
# Traducción a Strands y fábrica
# ----------------------------------------------------------------------


def test_build_strands_cache_config_disabled_returns_none():
    assert build_strands_cache_config(ProviderCacheConfig(enabled=False)) is None
    assert (
        build_strands_cache_config(
            ProviderCacheConfig(enabled=False, strategy="anthropic"), default_cache_key="x"
        )
        is None
    )


def test_build_strands_cache_config_keeps_strands_defaults():
    cache_config = build_strands_cache_config(ProviderCacheConfig(enabled=True, strategy="auto"))
    assert cache_config == CacheConfig(strategy="auto")
    assert cache_config.system_prompt_ttl is True
    assert cache_config.tools_ttl is None
    assert cache_config.cache_key is None


def test_build_strands_cache_config_explicit_key_wins_over_default():
    cache = ProviderCacheConfig(enabled=True, cache_key="pinned", ttl="24h")
    cache_config = build_strands_cache_config(cache, default_cache_key="derived")
    assert cache_config.cache_key == "pinned"
    assert cache_config.ttl == "24h"

    opt_out = build_strands_cache_config(
        ProviderCacheConfig(enabled=True, cache_key=False), default_cache_key="derived"
    )
    assert opt_out.cache_key is False


def test_derive_cache_key_is_stable_and_model_specific(tmp_path: Path):
    path = tmp_path / "agent.conf"
    first = derive_cache_key(path, "gpt-test")
    second = derive_cache_key(path, "gpt-test")
    assert first == second
    assert first.startswith(CACHE_KEY_PREFIX)
    assert len(first) == len(CACHE_KEY_PREFIX) + 16
    assert derive_cache_key(path, "other-model") != first
    assert derive_cache_key(tmp_path / "other.conf", "gpt-test") != first


@pytest.fixture
def factory_for(minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch):
    def _build(provider: str, cache_block=None, *, drop_cache: bool = False) -> AgentFactory:
        def mutate(payload):
            payload["provider"] = provider
            if drop_cache:
                payload["providers"][provider].pop("cache", None)
            if cache_block is not None:
                payload["providers"][provider]["cache"] = cache_block

        _rewrite(minimal_agent_conf, mutate)
        monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
        return AgentFactory(load_agent_config())

    return _build


@patch("smart_ai_sys_admin.agent.factory.BedrockModel")
def test_bedrock_receives_auto_cache_config(mock_model_cls, factory_for):
    factory = factory_for("bedrock", drop_cache=True)
    factory._build_model(factory._config.provider_config())
    kwargs = mock_model_cls.call_args.kwargs
    assert kwargs["cache_config"] == CacheConfig(strategy="auto")
    assert factory.cache_enabled is True


@patch("smart_ai_sys_admin.agent.factory.BedrockModel")
def test_bedrock_cache_config_forwards_ttls(mock_model_cls, factory_for):
    factory = factory_for(
        "bedrock",
        {"strategy": "anthropic", "ttl": "1h", "system_prompt_ttl": "5m", "tools_ttl": False},
    )
    factory._build_model(factory._config.provider_config())
    cache_config = mock_model_cls.call_args.kwargs["cache_config"]
    assert cache_config.strategy == "anthropic"
    assert cache_config.ttl == "1h"
    assert cache_config.system_prompt_ttl == "5m"
    assert cache_config.tools_ttl is False
    assert cache_config.cache_key is None


@patch("smart_ai_sys_admin.agent.factory.BedrockModel")
def test_bedrock_cache_disabled_omits_cache_config(mock_model_cls, factory_for):
    factory = factory_for("bedrock", {"enabled": False})
    factory._build_model(factory._config.provider_config())
    assert "cache_config" not in mock_model_cls.call_args.kwargs
    assert factory.cache_enabled is False


@patch("smart_ai_sys_admin.agent.factory.OpenAIModel")
def test_openai_chat_receives_derived_cache_key(
    mock_model_cls, factory_for, minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    factory = factory_for("openai", drop_cache=True)
    factory._build_model(factory._config.provider_config())
    cache_config = mock_model_cls.call_args.kwargs["cache_config"]
    assert cache_config == CacheConfig(cache_key=derive_cache_key(minimal_agent_conf, "gpt-test"))
    assert cache_config.cache_key.startswith(CACHE_KEY_PREFIX)


@patch("smart_ai_sys_admin.agent.factory.OpenAIResponsesModel")
def test_openai_responses_receives_cache_config(
    mock_model_cls, factory_for, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    factory = factory_for("openai", {"cache_key": "pinned-key", "ttl": "in_memory"})
    provider_cfg = factory._config.provider_config()
    object.__setattr__(provider_cfg, "api", "responses")
    factory._build_model(provider_cfg)
    kwargs = mock_model_cls.call_args.kwargs
    assert kwargs["stateful"] is False
    assert kwargs["cache_config"] == CacheConfig(cache_key="pinned-key", ttl="in_memory")


@patch("smart_ai_sys_admin.agent.factory.OpenAIModel")
def test_openai_cache_disabled_passes_none(
    mock_model_cls, factory_for, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    factory = factory_for("openai", {"enabled": False})
    factory._build_model(factory._config.provider_config())
    assert mock_model_cls.call_args.kwargs["cache_config"] is None
    assert factory.cache_enabled is False


@patch("smart_ai_sys_admin.agent.factory.ShellMistralModel")
def test_mistral_receives_cache_config(
    mock_model_cls, factory_for, minimal_agent_conf: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-mistral-key")
    factory = factory_for("mistral", drop_cache=True)
    factory._build_model(factory._config.provider_config())
    kwargs = mock_model_cls.call_args.kwargs
    expected_key = derive_cache_key(minimal_agent_conf, "mistral-medium-3.5")
    assert kwargs["cache_config"] == CacheConfig(cache_key=expected_key)
    assert kwargs["reasoning_effort"] == "high"


def test_shell_mistral_model_forwards_cache_config_to_strands():
    from smart_ai_sys_admin.agent.providers import ShellMistralModel

    cache_config = CacheConfig(cache_key="pinned")
    model = ShellMistralModel(
        api_key="test-key", model_id="mistral-medium-3.5", cache_config=cache_config
    )
    assert model.get_config()["cache_config"] is cache_config


@patch("smart_ai_sys_admin.agent.factory.OpenAIModel")
def test_lmstudio_cache_disabled_by_default(mock_model_cls, factory_for):
    factory = factory_for("lmstudio", drop_cache=True)
    factory._build_model(factory._config.provider_config())
    assert mock_model_cls.call_args.kwargs["cache_config"] is None


@patch("smart_ai_sys_admin.agent.factory.OpenAIModel")
def test_lmstudio_cache_enabled_sends_routing_key(mock_model_cls, factory_for):
    factory = factory_for("lmstudio", {"enabled": True})
    factory._build_model(factory._config.provider_config())
    cache_config = mock_model_cls.call_args.kwargs["cache_config"]
    assert cache_config.cache_key.startswith(CACHE_KEY_PREFIX)


@patch("smart_ai_sys_admin.agent.factory.OllamaModel")
def test_local_cache_enabled_warns_and_ignores(mock_model_cls, factory_for, caplog):
    factory = factory_for("local", {"enabled": True})
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.factory"):
        factory._build_model(factory._config.provider_config())
    assert "cache_config" not in mock_model_cls.call_args.kwargs
    assert any("providers.local.cache" in record.message for record in caplog.records)
    assert factory.cache_enabled is False


@patch("smart_ai_sys_admin.agent.factory.OllamaModel")
def test_local_cache_disabled_is_silent(mock_model_cls, factory_for, caplog):
    factory = factory_for("local", drop_cache=True)
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.factory"):
        factory._build_model(factory._config.provider_config())
    assert not [r for r in caplog.records if "cache" in r.message]


@patch("smart_ai_sys_admin.agent.factory.CerebrasModel")
def test_cerebras_cache_enabled_warns_and_ignores(mock_model_cls, factory_for, caplog):
    factory = factory_for("cerebras", {"enabled": True})
    with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.factory"):
        factory._build_model(factory._config.provider_config())
    assert "cache_config" not in mock_model_cls.call_args.kwargs
    assert any("providers.cerebras.cache" in record.message for record in caplog.records)
    assert factory.cache_enabled is False


# ----------------------------------------------------------------------
# Métricas de caché en el runtime y en /status
# ----------------------------------------------------------------------


def test_summarize_cache_usage_bedrock_style():
    # Bedrock no incluye los tokens cacheados en inputTokens.
    usage = {
        "inputTokens": 200,
        "outputTokens": 50,
        "totalTokens": 1250,
        "cacheReadInputTokens": 900,
        "cacheWriteInputTokens": 100,
    }
    assert summarize_cache_usage(usage) == {
        "input_tokens": 1200,
        "cached_tokens": 900,
        "written_tokens": 100,
        "percent": 75,
    }


def test_summarize_cache_usage_openai_style():
    # OpenAI incluye cached_tokens dentro de prompt_tokens.
    usage = {
        "inputTokens": 1000,
        "outputTokens": 50,
        "totalTokens": 1050,
        "cacheReadInputTokens": 800,
    }
    assert summarize_cache_usage(usage) == {
        "input_tokens": 1000,
        "cached_tokens": 800,
        "written_tokens": 0,
        "percent": 80,
    }


def test_summarize_cache_usage_without_cache_fields():
    usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    assert summarize_cache_usage(usage) == {
        "input_tokens": 0,
        "cached_tokens": 0,
        "written_tokens": 0,
        "percent": 0,
    }


def test_record_cache_usage_prefers_last_invocation(agent_runtime: AgentRuntime, caplog):
    accumulated = {"inputTokens": 5000, "outputTokens": 500, "totalTokens": 5500}
    last = {
        "inputTokens": 1000,
        "outputTokens": 100,
        "totalTokens": 1100,
        "cacheReadInputTokens": 600,
    }
    result = SimpleNamespace(
        metrics=SimpleNamespace(
            accumulated_usage=accumulated,
            agent_invocations=[
                SimpleNamespace(usage=accumulated),
                SimpleNamespace(usage=last),
            ],
        )
    )
    with caplog.at_level(logging.INFO, logger="test.agent.runtime"):
        agent_runtime._record_cache_usage(result)  # type: ignore[arg-type]
    assert agent_runtime.last_cache_usage == {
        "input_tokens": 1000,
        "cached_tokens": 600,
        "written_tokens": 0,
        "percent": 60,
    }
    assert any("600 de 1000" in record.getMessage() for record in caplog.records)
    assert agent_runtime.agent_summary()["cache_usage"]["cached_tokens"] == 600


def test_record_cache_usage_without_metrics(agent_runtime: AgentRuntime):
    agent_runtime._record_cache_usage(SimpleNamespace(metrics=None))  # type: ignore[arg-type]
    assert agent_runtime.last_cache_usage is None
    assert agent_runtime.agent_summary()["cache_usage"] is None


@patch("smart_ai_sys_admin.agent.runtime.MCPManager.activate", return_value=[])
@patch("smart_ai_sys_admin.agent.runtime.AgentFactory.build_agent")
@patch("smart_ai_sys_admin.agent.runtime.load_agent_config")
def test_agent_summary_reports_cache_enabled(
    mock_load,
    mock_build,
    mock_mcp,
    agent_runtime: AgentRuntime,
    minimal_agent_conf: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from smart_ai_sys_admin.agent.factory import AgentBuildResult

    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(minimal_agent_conf))
    config = load_agent_config()
    mock_load.return_value = config
    mock_build.return_value = AgentBuildResult(agent=MagicMock(), mcp_config=config.mcp)

    assert agent_runtime.agent_summary()["cache_enabled"] is None
    agent_runtime.initialize()
    assert agent_runtime.agent_summary()["cache_enabled"] is True


def test_status_shows_cache_lines(slash_processor: SlashCommandProcessor, fake_agent_runtime):
    fake_agent_runtime._summary["cache_enabled"] = True
    fake_agent_runtime._summary["cache_usage"] = {
        "input_tokens": 12345,
        "cached_tokens": 9876,
        "written_tokens": 0,
        "percent": 80,
    }
    result = slash_processor.process("/status")
    assert result is not None
    assert "Prompt caching: yes" in result
    assert "9,876 of 12,345 input tokens read from cache (80%)" in result


def test_status_shows_cache_disabled_without_usage(
    slash_processor: SlashCommandProcessor, fake_agent_runtime
):
    fake_agent_runtime._summary["cache_enabled"] = False
    result = slash_processor.process("/status")
    assert result is not None
    assert "Prompt caching: no" in result
    assert "read from cache" not in result


def test_status_omits_cache_lines_when_unknown(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/status")
    assert result is not None
    assert "Prompt caching" not in result
