"""Pruebas de configuración y factoría para las APIs de OpenAI."""

from __future__ import annotations

from pathlib import Path

import pytest
from strands.models import OpenAIResponsesModel
from strands.models.openai import OpenAIModel

from smart_ai_sys_admin.agent.config import (
    AgentConfigError,
    OpenAIProviderConfig,
    _normalize_openai_params,
    load_agent_config,
)
from smart_ai_sys_admin.agent.factory import AgentFactory


@pytest.mark.parametrize(
    ("api", "reasoning_input", "expected_reasoning", "expected_token_key"),
    [
        (
            "chat_completions",
            {"reasoning_effort": "medium"},
            {"reasoning_effort": "medium"},
            "max_completion_tokens",
        ),
        (
            "chat_completions",
            {"reasoning": {"effort": "medium"}},
            {"reasoning_effort": "medium"},
            "max_completion_tokens",
        ),
        (
            "responses",
            {"reasoning_effort": "medium"},
            {"reasoning": {"effort": "medium"}},
            "max_output_tokens",
        ),
        (
            "responses",
            {"reasoning": {"effort": "medium"}},
            {"reasoning": {"effort": "medium"}},
            "max_output_tokens",
        ),
    ],
)
def test_normalize_openai_params_by_api(
    api: str,
    reasoning_input: dict[str, object],
    expected_reasoning: dict[str, object],
    expected_token_key: str,
) -> None:
    params = {**reasoning_input, "max_tokens": 65536}

    normalized = _normalize_openai_params(params, api)

    assert normalized == {**expected_reasoning, expected_token_key: 65536}


@pytest.mark.parametrize(
    ("api", "params", "expected"),
    [
        (
            "chat_completions",
            {
                "max_tokens": 1024,
                "max_completion_tokens": 32768,
                "max_output_tokens": 2048,
            },
            {"max_completion_tokens": 32768},
        ),
        (
            "responses",
            {
                "max_tokens": 1024,
                "max_completion_tokens": 2048,
                "max_output_tokens": 32768,
            },
            {"max_output_tokens": 32768},
        ),
        (
            "chat_completions",
            {"max_output_tokens": 4096},
            {"max_completion_tokens": 4096},
        ),
        (
            "responses",
            {"max_completion_tokens": 4096},
            {"max_output_tokens": 4096},
        ),
    ],
)
def test_normalize_openai_params_resolves_token_limit_collisions(
    api: str, params: dict[str, int], expected: dict[str, int]
) -> None:
    assert _normalize_openai_params(params, api) == expected


def test_normalize_openai_params_rejects_unknown_api() -> None:
    with pytest.raises(AgentConfigError, match="API de OpenAI desconocida"):
        _normalize_openai_params({}, "legacy")


def _provider_config(api: str) -> OpenAIProviderConfig:
    token_key = "max_output_tokens" if api == "responses" else "max_completion_tokens"
    reasoning = {"reasoning": {"effort": "medium"}}
    if api == "chat_completions":
        reasoning = {"reasoning_effort": "medium"}
    return OpenAIProviderConfig(
        system_prompt_path=Path("system_prompts/openai.md"),
        system_prompt="Prompt de prueba",
        show_thinking=False,
        model_id="gpt-test",
        api=api,  # type: ignore[arg-type]
        stateful=True,
        client_args={"api_key_env": "OPENAI_API_KEY"},
        params={**reasoning, token_key: 256},
    )


@pytest.mark.parametrize(
    ("api", "expected_class"),
    [
        ("chat_completions", OpenAIModel),
        ("responses", OpenAIResponsesModel),
    ],
)
def test_factory_selects_openai_model_by_api(
    monkeypatch: pytest.MonkeyPatch,
    api: str,
    expected_class: type[OpenAIModel] | type[OpenAIResponsesModel],
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    cfg = _provider_config(api)
    factory = AgentFactory(None)  # type: ignore[arg-type]

    model = factory._build_model(cfg)

    assert isinstance(model, expected_class)
    assert model.get_config()["params"] == dict(cfg.params)
    if api == "responses":
        assert model.get_config()["stateful"] is True


def test_factory_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    factory = AgentFactory(None)  # type: ignore[arg-type]

    with pytest.raises(AgentConfigError, match="OPENAI_API_KEY"):
        factory._build_model(_provider_config("responses"))


_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_CONFIGS = [(_REPO_ROOT / "conf" / "agent.conf.example", 32768)]
_REAL_CONFIG = _REPO_ROOT / "conf" / "agent.conf"
if _REAL_CONFIG.is_file():
    _REPOSITORY_CONFIGS.append((_REAL_CONFIG, 65536))


@pytest.mark.parametrize(("config_path", "expected_tokens"), _REPOSITORY_CONFIGS)
def test_repository_configs_enable_reasoning_with_responses(
    config_path: Path, expected_tokens: int
) -> None:
    config = load_agent_config(config_path)
    provider = config.providers["openai"]

    assert isinstance(provider, OpenAIProviderConfig)
    assert provider.model_id == "gpt-5.6-sol"
    assert provider.api == "responses"
    assert provider.params["reasoning"] == {"effort": "medium"}
    assert provider.params["max_output_tokens"] == expected_tokens
