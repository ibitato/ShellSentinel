"""Pruebas unitarias del proveedor ShellMistralModel."""

from __future__ import annotations

import pytest

from smart_ai_sys_admin.agent.providers.mistral import (
    DEFAULT_REASONING_EFFORT,
    ShellMistralModel,
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
