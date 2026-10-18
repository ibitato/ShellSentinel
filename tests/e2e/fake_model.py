"""Modelo Strands con guion para pruebas e2e deterministas del TUI.

``ScriptedModel`` implementa ``strands.models.Model`` y reproduce, en cada llamada a
``stream``, la siguiente lista de ``StreamEvent`` del guion. Los constructores
``text_turn`` y ``tool_turn`` generan las secuencias con la forma exacta que el
event loop de Strands 1.61 consume (verificado contra la librería instalada).
"""

from __future__ import annotations

import copy
import json
from collections.abc import AsyncGenerator, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from strands.models import Model
from strands.types.streaming import StreamEvent

Usage = dict[str, int]

DEFAULT_TOOL_USAGE: Usage = {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}


@dataclass
class ModelCall:
    """Registro de una invocación a ``stream``."""

    messages: list[dict[str, Any]]
    tool_names: list[str]
    system_prompt: str | None
    kwargs: dict[str, Any] = field(default_factory=dict)

    def tool_results(self) -> list[dict[str, Any]]:
        """Bloques ``toolResult`` presentes en los mensajes recibidos."""

        results: list[dict[str, Any]] = []
        for message in self.messages:
            for block in message.get("content", []):
                if isinstance(block, dict) and "toolResult" in block:
                    results.append(block["toolResult"])
        return results


class ScriptedModel(Model):
    """Reproduce turnos guionizados y registra lo que el agente le envía."""

    def __init__(
        self,
        turns: Iterable[list[StreamEvent]] = (),
        *,
        model_id: str = "scripted-model",
    ) -> None:
        self._config: dict[str, Any] = {"model_id": model_id}
        self.turns: list[list[StreamEvent]] = [list(turn) for turn in turns]
        self.calls: list[ModelCall] = []
        self.raise_on_exhausted: Exception = RuntimeError("scripted model: no more turns")

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return dict(self._config)

    def enqueue(self, *turns: list[StreamEvent]) -> None:
        self.turns.extend(list(turn) for turn in turns)

    def tool_results(self) -> list[dict[str, Any]]:
        """Todos los ``toolResult`` vistos en cualquier llamada."""

        return [result for call in self.calls for result in call.tool_results()]

    async def structured_output(  # type: ignore[override]
        self, output_model: Any, prompt: Any, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"output": None}

    async def stream(  # type: ignore[override]
        self,
        messages: Any,
        tool_specs: Sequence[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        self.calls.append(
            ModelCall(
                messages=copy.deepcopy(list(messages)),
                tool_names=[spec["name"] for spec in tool_specs or []],
                system_prompt=system_prompt,
                kwargs={key: value for key, value in kwargs.items() if key == "tool_choice"},
            )
        )
        if not self.turns:
            raise self.raise_on_exhausted
        for event in self.turns.pop(0):
            yield event


def _metadata(usage: Usage | None) -> list[StreamEvent]:
    if usage is None:
        return []
    return [{"metadata": {"usage": dict(usage), "metrics": {"latencyMs": 1}}}]  # type: ignore[list-item]


def text_turn(
    text: str, *, usage: Usage | None = None, stop_reason: str = "end_turn"
) -> list[StreamEvent]:
    """Turno que emite un único bloque de texto."""

    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {}}},
        {"contentBlockDelta": {"delta": {"text": text}}},
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": stop_reason}},  # type: ignore[typeddict-item]
        *_metadata(usage),
    ]


def split_json(payload: str, split: int | Sequence[str] | None) -> list[str]:
    """Trocea el JSON de entrada de una tool en fragmentos (entero = partes iguales)."""

    if split is None:
        return [payload]
    if isinstance(split, int):
        if split <= 1:
            return [payload]
        size = max(1, -(-len(payload) // split))
        return [payload[i : i + size] for i in range(0, len(payload), size)]
    fragments = list(split)
    assert "".join(fragments) == payload, "los fragmentos deben recomponer el JSON original"
    return fragments


def tool_turn(
    name: str,
    tool_input: dict[str, Any] | str,
    *,
    tool_use_id: str = "tu-1",
    split: int | Sequence[str] | None = None,
    usage: Usage | None = None,
) -> list[StreamEvent]:
    """Turno que pide ejecutar una tool, con el JSON de entrada opcionalmente troceado."""

    payload = tool_input if isinstance(tool_input, str) else json.dumps(tool_input)
    fragments = split_json(payload, split)
    return [
        {"messageStart": {"role": "assistant"}},
        {"contentBlockStart": {"start": {"toolUse": {"toolUseId": tool_use_id, "name": name}}}},
        *[
            {"contentBlockDelta": {"delta": {"toolUse": {"input": fragment}}}}
            for fragment in fragments
        ],
        {"contentBlockStop": {}},
        {"messageStop": {"stopReason": "tool_use"}},
        *_metadata(usage or DEFAULT_TOOL_USAGE),
    ]


__all__ = [
    "DEFAULT_TOOL_USAGE",
    "ModelCall",
    "ScriptedModel",
    "split_json",
    "text_turn",
    "tool_turn",
]
