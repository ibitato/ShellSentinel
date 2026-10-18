"""Guardas de coste para las pruebas e2e live, implementadas como hooks de Strands.

``E2EGuard`` cuenta cada intento de llamada al modelo (incluidos los reintentos por
throttling) y, al superar el presupuesto o la fecha límite, cancela la llamada con
``BeforeModelCallEvent.cancel``: Strands sintetiza entonces un ``end_turn`` con el
texto de cancelación y la invocación termina sin excepción ni recursión. También
registra cada ``toolUse`` con su entrada ya parseada, que es exactamente lo que
quedó vacío (``{}``) en el incidente del bucle con Mistral.
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from typing import Any

from strands.hooks import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)

GUARD_SENTINEL = "E2E_GUARD_TRIPPED"


@dataclass
class ToolUseRecord:
    """Una invocación de tool observada por el guarda."""

    name: str
    input: dict[str, Any]
    tool_use_id: str | None = None
    result_status: str | None = None
    result_text: str = ""


@dataclass
class E2EGuard(HookProvider):
    """Presupuesto de llamadas al modelo + fecha límite + registro de tool uses."""

    max_model_calls: int = 10
    deadline_s: float = 180.0
    model_calls: int = 0
    tool_uses: list[ToolUseRecord] = field(default_factory=list)
    model_errors: list[str] = field(default_factory=list)
    tripped: str | None = None
    _started: float = field(default_factory=time.monotonic)

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeModelCallEvent, self._before_model)
        registry.add_callback(AfterModelCallEvent, self._after_model)
        registry.add_callback(BeforeToolCallEvent, self._before_tool)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def restart_clock(self) -> None:
        """Reinicia la fecha límite (se llama al empezar cada turno del operador)."""

        self._started = time.monotonic()

    # ------------------------------------------------------------------ callbacks
    def _before_model(self, event: BeforeModelCallEvent) -> None:
        self.model_calls += 1
        if self.model_calls > self.max_model_calls:
            reason = f"model calls > {self.max_model_calls}"
        elif time.monotonic() - self._started > self.deadline_s:
            reason = f"wall-clock deadline {self.deadline_s:.0f}s exceeded"
        else:
            return
        if self.tripped is None:
            self.tripped = reason
        event.cancel = f"{GUARD_SENTINEL}: {reason}"

    def _after_model(self, event: AfterModelCallEvent) -> None:
        if event.exception is not None:
            self.model_errors.append(f"{type(event.exception).__name__}: {event.exception}")

    def _before_tool(self, event: BeforeToolCallEvent) -> None:
        tool_use = event.tool_use
        raw_input = tool_use.get("input", {})
        self.tool_uses.append(
            ToolUseRecord(
                name=str(tool_use.get("name", "")),
                input=(
                    copy.deepcopy(raw_input) if isinstance(raw_input, dict) else {"_raw": raw_input}
                ),
                tool_use_id=tool_use.get("toolUseId"),
            )
        )

    def _after_tool(self, event: AfterToolCallEvent) -> None:
        tool_use_id = event.tool_use.get("toolUseId")
        for record in reversed(self.tool_uses):
            if record.tool_use_id == tool_use_id and record.result_status is None:
                record.result_status = str(event.result.get("status", ""))
                record.result_text = "\n".join(
                    block.get("text", "")
                    for block in event.result.get("content", [])
                    if isinstance(block, dict)
                )
                break

    # ------------------------------------------------------------------ consultas
    def commands(self, tool_name: str = "remote_ssh_command") -> list[Any]:
        """Valores de ``command`` recibidos por ``tool_name`` (``None`` si faltaba)."""

        return [
            record.input.get("command") for record in self.tool_uses if record.name == tool_name
        ]

    def debug_report(self) -> str:
        lines = [
            f"model_calls={self.model_calls} (max {self.max_model_calls})",
            f"tripped={self.tripped!r}",
            f"model_errors={self.model_errors!r}",
            "tool_uses:",
        ]
        for record in self.tool_uses:
            lines.append(
                f"  - {record.name} input={json.dumps(record.input, ensure_ascii=False)[:300]}"
                f" status={record.result_status}"
            )
        return "\n".join(lines)


__all__ = ["GUARD_SENTINEL", "E2EGuard", "ToolUseRecord"]
