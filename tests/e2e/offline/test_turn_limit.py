"""E2E offline: ``agent.max_turns`` corta un agente en bucle antes del ``RecursionError``.

Reproduce el incidente del 2026-10-18 (``zai-glm-5-3`` vía Mistral): el modelo pide
``remote_ssh_command`` con entrada vacía una y otra vez. Sin límite, Strands recurría
hasta agotar la pila (305 llamadas); con ``max_turns`` la invocación termina con
``stop_reason="limit_turns"`` y el panel muestra el aviso localizado.
"""

from __future__ import annotations

import logging

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.ssh_server import ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline

MAX_TURNS = 3
LOOP_PROMPT = "dame las características hardware de este servidor"


def _empty_tool_turns(count: int) -> list[list]:
    """``count`` turnos que piden ``remote_ssh_command`` sin argumentos (entrada ``{}``)."""

    return [
        tool_turn("remote_ssh_command", {}, tool_use_id=f"tu-loop-{index}")
        for index in range(count)
    ]


async def test_looping_tool_calls_stop_at_max_turns(
    tui,
    e2e_env,
    ssh: ScriptedSSHServer,
    connect_line: str,
    scripted_model: ScriptedModel,
    caplog: pytest.LogCaptureFixture,
):
    write_agent_conf(e2e_env.conf_dir, max_turns=MAX_TURNS)
    # Muchos más turnos de los permitidos: si el límite no actuara, el modelo seguiría.
    scripted_model.enqueue(*_empty_tool_turns(MAX_TURNS * 10))

    async with tui() as driver:
        await driver.submit(connect_line)
        with caplog.at_level(logging.WARNING, logger="smart_ai_sys_admin.agent.runtime"):
            reply = await driver.submit(LOOP_PROMPT)

        notice = _("agent.invoke.turn_limit", limit=MAX_TURNS)
        assert reply.endswith(notice)
        assert "RecursionError" not in reply
        assert not reply.startswith("❌")

        # Strands corta exactamente en ``max_turns`` llamadas al modelo y nunca ejecuta
        # nada por SSH: la entrada vacía no pasa la validación de la tool.
        assert len(scripted_model.calls) == MAX_TURNS
        assert ssh.recorded_commands == []
        assert len(scripted_model.turns) == MAX_TURNS * 10 - MAX_TURNS
        tool_results = scripted_model.calls[-1].tool_results()
        assert tool_results and tool_results[-1]["status"] == "error"

        assert any(
            record.levelno == logging.WARNING and "limit_turns" in record.getMessage()
            for record in caplog.records
        )
        assert driver.app._busy is False

        status = await driver.submit("/status")
        assert f"- {_('ui.commands.status.max_turns')}: {MAX_TURNS}" in status


async def test_agent_recovers_after_turn_limit(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    """Tras el corte, la siguiente instrucción vuelve a tener ``max_turns`` turnos."""

    write_agent_conf(e2e_env.conf_dir, max_turns=MAX_TURNS)
    scripted_model.enqueue(*_empty_tool_turns(MAX_TURNS), text_turn("all good now"))

    async with tui() as driver:
        await driver.submit(connect_line)
        first = await driver.submit(LOOP_PROMPT)
        assert first.endswith(_("agent.invoke.turn_limit", limit=MAX_TURNS))

        second = await driver.submit("otra instrucción")
        assert second == "all good now"
        assert len(scripted_model.calls) == MAX_TURNS + 1


async def test_turn_limit_disabled_lets_scripted_flow_finish(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    """Con ``max_turns: null`` no se pasa ningún límite y el flujo termina por sí mismo."""

    write_agent_conf(e2e_env.conf_dir, max_turns=None)
    scripted_model.enqueue(*_empty_tool_turns(MAX_TURNS + 2), text_turn("finished"))

    async with tui() as driver:
        await driver.submit(connect_line)
        reply = await driver.submit(LOOP_PROMPT)

        assert reply == "finished"
        assert len(scripted_model.calls) == MAX_TURNS + 3
        status = await driver.submit("/status")
        assert (
            f"- {_('ui.commands.status.max_turns')}: "
            f"{_('ui.commands.status.max_turns_disabled')}" in status
        )
