"""E2E live: inventario de hardware con el prompt literal del incidente de 2026-10-18."""

from __future__ import annotations

import re

from tests.e2e.live.conftest import LiveSession
from tests.e2e.ssh_server import SENTINEL_CPU_MODEL, SENTINEL_HOSTNAME, SENTINEL_KERNEL

INCIDENT_PROMPT = "dame las caracteristicas hardawre de este servidor"
SENTINELS = (SENTINEL_HOSTNAME, SENTINEL_CPU_MODEL, SENTINEL_KERNEL)


async def test_hardware_inventory_runs_remote_commands(connected_live_app: LiveSession):
    session = connected_live_app

    reply = await session.ask(INCIDENT_PROMPT)

    session.assert_clean_reply(reply)
    session.assert_commands_well_formed()
    assert session.ssh.recorded_commands, session.guard.debug_report()
    assert any(record.name == "remote_ssh_command" for record in session.guard.tool_uses)
    lowered = reply.lower()
    assert any(
        sentinel.lower() in lowered for sentinel in SENTINELS
    ), f"la respuesta no cita ningún dato del servidor:\n{reply}\n{session.guard.debug_report()}"
    cycle_count = session.driver.runtime._agent.event_loop_metrics.cycle_count
    assert 0 < cycle_count <= session.guard.model_calls, (cycle_count, session.guard.model_calls)


async def test_multistep_disk_and_kernel(connected_live_app: LiveSession):
    session = connected_live_app

    reply = await session.ask("¿cuánto espacio libre queda en / y qué kernel está corriendo?")

    session.assert_clean_reply(reply)
    session.assert_commands_well_formed()
    joined = "\n".join(session.ssh.recorded_commands)
    assert re.search(r"\bdf\b", joined), joined
    assert re.search(r"uname|/proc/version|hostnamectl", joined), joined
    lowered = reply.lower()
    assert (
        SENTINEL_KERNEL.lower() in lowered or "28g" in lowered or "sentinel-root" in lowered
    ), reply
