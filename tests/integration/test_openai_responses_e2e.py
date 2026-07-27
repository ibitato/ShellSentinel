"""Pruebas e2e opcionales para OpenAI Responses API."""

from __future__ import annotations

import os
from typing import Any

import pytest
from strands import Agent, tool
from strands.models import OpenAIResponsesModel

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("RUN_E2E") != "1" or not os.getenv("OPENAI_API_KEY"),
        reason="Requiere RUN_E2E=1 y OPENAI_API_KEY",
    ),
]


def _model(**params: Any) -> OpenAIResponsesModel:
    return OpenAIResponsesModel(
        client_args={"api_key": os.environ["OPENAI_API_KEY"]},
        model_id="gpt-5.6-sol",
        params={"reasoning": {"effort": "medium"}, "max_output_tokens": 1024, **params},
        stateful=False,
    )


def test_responses_agent_invokes_function_tool() -> None:
    invocations: list[str] = []

    @tool
    def diagnostic_probe(target: str) -> str:
        """Registra y devuelve el estado de un objetivo de diagnóstico."""

        invocations.append(target)
        return f"{target}: healthy"

    agent = Agent(model=_model(), tools=[diagnostic_probe])

    result = agent(
        "Usa obligatoriamente diagnostic_probe con target='gateway' y después "
        "responde con el estado devuelto."
    )

    assert invocations == ["gateway"]
    assert "healthy" in str(result).lower()


class _ReasoningUsageModel(OpenAIResponsesModel):
    """Modelo instrumentado para conservar el detalle de uso que Strands descarta."""

    def __init__(self) -> None:
        super().__init__(
            client_args={"api_key": os.environ["OPENAI_API_KEY"]},
            model_id="gpt-5.6-sol",
            params={"reasoning": {"effort": "medium"}, "max_output_tokens": 2048},
            stateful=False,
        )
        self.reasoning_tokens = 0

    def _format_chunk(self, event: dict[str, Any]) -> Any:
        if event.get("chunk_type") == "metadata":
            output_details = getattr(event["data"], "output_tokens_details", None)
            self.reasoning_tokens += getattr(output_details, "reasoning_tokens", 0) or 0
        return super()._format_chunk(event)


def test_responses_agent_reports_reasoning_tokens_with_tools() -> None:
    @tool
    def inspect_label(label: str) -> str:
        """Devuelve una etiqueta sin modificar para mantener una function tool adjunta."""

        return label

    model = _ReasoningUsageModel()
    agent = Agent(model=model, tools=[inspect_label])

    agent(
        "Resuelve razonadamente este problema: hay tres cajas etiquetadas Manzanas, "
        "Naranjas y Mezcla; todas las etiquetas son incorrectas. Puedes extraer una "
        "sola fruta de una sola caja. Explica qué caja eliges y cómo corriges las tres etiquetas."
    )

    assert model.reasoning_tokens > 0
