"""E2E live de MCP con Firecrawl real (``npx -y firecrawl-mcp``).

Dos niveles de coste:

- Con el modelo con guion (sin tokens de LLM): el TUI arranca el servidor de Firecrawl, lista
  sus tools y ejecuta un ``firecrawl_scrape`` real (consume créditos de Firecrawl, no tokens).
- Con un proveedor real (``live_provider``): el agente debe elegir una tool de Firecrawl por
  sí mismo para leer una página.

Requisitos: ``RUN_E2E=1``, ``FIRECRAWL_API_KEY`` y ``npx`` (Node.js) en ``PATH``; si falta
alguno, las pruebas se saltan con el motivo.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.agent_conf import shipped_system_prompt, write_agent_conf
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.live.conftest import LiveSession, _start_session
from tests.e2e.mcp_support import firecrawl_transport, firecrawl_unavailable_reason
from tests.e2e.providers import LiveProvider, run_e2e_enabled
from tests.e2e.ssh_server import ScriptedSSHServer

_FIRECRAWL_SKIP = firecrawl_unavailable_reason()

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not run_e2e_enabled(), reason="RUN_E2E=1 es necesario para las pruebas live"
    ),
    pytest.mark.skipif(_FIRECRAWL_SKIP is not None, reason=_FIRECRAWL_SKIP or ""),
]

SERVER_ID = "firecrawl-stdio"
EXPECTED_TOOLS = {"firecrawl_scrape", "firecrawl_search", "firecrawl_map"}
PAGE_URL = "https://example.com"
PAGE_MARKERS = ("example", "ejemplo", "documentation", "documentación", "domain", "dominio")
STARTUP_TIMEOUT_S = 120


def _tool_result_text(result: dict) -> str:
    return "\n".join(block.get("text", "") for block in result.get("content", []))


def _mcp_block() -> dict:
    return {"transports": [firecrawl_transport(SERVER_ID, timeout_seconds=STARTUP_TIMEOUT_S)]}


def _ready_count(status: str) -> int:
    """Número de tools que ``/status`` atribuye al servidor de Firecrawl."""

    prefix = _("agent.mcp.status.ready", id=SERVER_ID, transport="stdio", count=0, message="")
    marker = prefix.split("0", 1)[0]
    for line in status.splitlines():
        if marker in line:
            digits = "".join(ch for ch in line.split(marker, 1)[1] if ch.isdigit() or ch == " ")
            return int(digits.split()[0])
    raise AssertionError(f"`{SERVER_ID}` no aparece como listo en /status:\n{status}")


# ---------------------------------------------------------------------- modelo con guion
@pytest.fixture
def firecrawl_scripted_conf(e2e_env: SimpleNamespace) -> SimpleNamespace:
    write_agent_conf(e2e_env.conf_dir, mcp=_mcp_block())
    return e2e_env


async def test_firecrawl_server_starts_and_registers_tools(
    firecrawl_scripted_conf, tui, scripted_model: ScriptedModel
):
    scripted_model.enqueue(text_turn("tools listas"))

    async with tui() as driver:
        assert driver.runtime.ready, driver.runtime.error_message
        statuses = {status.identifier: status for status in driver.runtime.mcp_statuses}
        assert statuses[SERVER_ID].ready, statuses[SERVER_ID].message
        assert statuses[SERVER_ID].tool_count >= len(EXPECTED_TOOLS)
        assert not any("MCP" in text for text in driver.agent_messages()), driver.agent_messages()

        await driver.submit("hola")
        tool_names = set(scripted_model.calls[0].tool_names)
        assert EXPECTED_TOOLS <= tool_names, sorted(tool_names)

        status = await driver.submit("/status")
        assert _ready_count(status) == statuses[SERVER_ID].tool_count


async def test_firecrawl_scrape_roundtrip_with_scripted_model(
    firecrawl_scripted_conf, tui, scripted_model: ScriptedModel
):
    scripted_model.enqueue(
        tool_turn(
            "firecrawl_scrape",
            {"url": PAGE_URL, "formats": ["markdown"], "onlyMainContent": True},
            tool_use_id="tu-scrape",
        ),
        text_turn("La página es un dominio de ejemplo para documentación."),
    )

    async with tui() as driver:
        reply = await driver.submit(f"lee {PAGE_URL} con firecrawl", timeout=STARTUP_TIMEOUT_S)
        assert reply == "La página es un dominio de ejemplo para documentación."
        (result,) = scripted_model.tool_results()
        assert result["toolUseId"] == "tu-scrape"
        assert result["status"] == "success", _tool_result_text(result)[:500]
        text = _tool_result_text(result).lower()
        assert "example domain" in text or "documentation examples" in text, text[:500]


# ---------------------------------------------------------------------- proveedor real
@pytest.fixture
def firecrawl_live_conf(e2e_env: SimpleNamespace, live_provider: LiveProvider) -> SimpleNamespace:
    write_agent_conf(
        e2e_env.conf_dir,
        provider=live_provider.conf_key,
        model_id=live_provider.model_id,
        system_prompt=shipped_system_prompt(live_provider.conf_key),
        provider_block=live_provider.provider_block,
        api_key_env=live_provider.api_key_env,
        timeout_seconds=30,
        max_output_chars=5000,
        cache_key=f"{live_provider.cache_key}-mcp",
        cache_enabled=live_provider.cache_configurable,
        mcp=_mcp_block(),
    )
    return e2e_env


@pytest.fixture
async def firecrawl_live_app(  # type: ignore[no-untyped-def]
    firecrawl_live_conf, tui, live_provider: LiveProvider, ssh: ScriptedSSHServer
) -> AsyncIterator[LiveSession]:
    async for session in _start_session(tui, live_provider, ssh):
        yield session


async def test_live_agent_reads_a_page_through_firecrawl(firecrawl_live_app: LiveSession):
    session = firecrawl_live_app
    statuses = {status.identifier: status for status in session.driver.runtime.mcp_statuses}
    assert statuses[SERVER_ID].ready, statuses[SERVER_ID].message

    reply = await session.ask(
        f"Usa Firecrawl para leer {PAGE_URL} y dime en una sola frase de qué trata la página. "
        "No uses la sesión SSH."
    )

    session.assert_clean_reply(reply)
    used = [record.name for record in session.guard.tool_uses]
    assert any(name.startswith("firecrawl_") for name in used), session.guard.debug_report()
    assert "remote_ssh_command" not in used, session.guard.debug_report()
    assert any(marker in reply.lower() for marker in PAGE_MARKERS), reply
    assert os.environ.get("FIRECRAWL_API_KEY", "") not in reply
