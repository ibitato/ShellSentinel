"""E2E live: una clave inválida se muestra como error en el panel y el TUI sigue operativo.

No consume tokens: el proveedor rechaza la petición antes de generar nada.
"""

from __future__ import annotations

import re

from smart_ai_sys_admin.localization import _
from tests.e2e.live.conftest import LiveSession


async def test_invalid_api_key_surfaces_error_and_app_stays_responsive(
    bad_key_app: LiveSession, connect_line: str
):
    session = bad_key_app
    await session.driver.submit(connect_line)

    reply = await session.ask("dime el kernel del servidor")

    assert reply.startswith("❌"), reply
    # OpenAI/Mistral responden 401; Gemini devuelve 400 con "API key not valid" (API_KEY_INVALID).
    assert re.search(
        r"401|unauthori[sz]ed|invalid.{0,40}key|key.{0,20}not valid|api_key_invalid|authentication",
        reply,
        re.I,
    ), reply
    assert session.guard.model_calls == 1, session.guard.debug_report()
    assert session.guard.tool_uses == [], session.guard.debug_report()
    assert session.driver.app._busy is False

    status = await session.driver.submit("/status")
    assert _("ui.commands.status.header") in status
    assert f"- {_('ui.commands.status.agent_ready')}: {_('common.yes')}" in status
