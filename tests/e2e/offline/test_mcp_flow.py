"""E2E offline de MCP: el TUI real arranca servidores MCP reales (subprocesos ``stdio`` y
endpoints HTTP locales), registra sus tools en el agente Strands y diagnostica los fallos.

No necesita red ni claves: el servidor ``stdio`` es ``tests/e2e/mcp_server.py`` sobre el SDK
``mcp`` 2.x, y los transportes HTTP apuntan a servidores locales de estado fijo.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.mcp_support import (
    FixedStatusHTTPServer,
    closed_port_url,
    http_transport,
    missing_command_transport,
    process_alive,
    read_pid,
    scripted_mcp_transport,
    wait_for_process_exit,
)
from tests.e2e.ssh_server import CommandResult, ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline

SCRIPTED_TOOLS = {"echo", "add", "env_value", "fail", "crash"}
CUSTOM_TOOLS = {"local_datetime", "remote_ssh_command", "remote_sftp_transfer"}
TOKEN_ENV = "SHELL_SENTINEL_E2E_MCP_TOKEN"
MISSING_ENV = "SHELL_SENTINEL_E2E_MCP_MISSING"


def _tool_result_text(result: dict) -> str:
    return "\n".join(block.get("text", "") for block in result.get("content", []))


def _ready_line(identifier: str, count: int, transport: str = "stdio") -> str:
    return _("agent.mcp.status.ready", id=identifier, transport=transport, count=count, message="")


def _failed_line(identifier: str, message: str, transport: str = "stdio") -> str:
    return _(
        "agent.mcp.status.failed", id=identifier, transport=transport, count=0, message=message
    )


def _mcp_report(driver, failed: int, total: int) -> str:  # type: ignore[no-untyped-def]
    """Mensaje del agente con el informe de arranque MCP (la bienvenida va antes)."""

    summary = _("agent.mcp.status.summary_failed", failed=failed, total=total)
    matches = [text for text in driver.agent_messages() if summary in text]
    assert len(matches) == 1, (summary, driver.agent_messages())
    return matches[0]


def _assert_failure_reported(report: str, identifier: str, transport: str, message: str) -> None:
    """El informe contiene la línea del servidor; ``message`` admite el marcador ``DETAIL``
    para la parte no determinista (texto de la excepción)."""

    line = _failed_line(identifier, message, transport)
    if "DETAIL" not in message:
        assert line in report, f"falta {line!r} en:\n{report}"
        return
    head, tail = line.split("DETAIL", 1)
    assert head in report and tail in report, f"falta {head!r}...{tail!r} en:\n{report}"


@pytest.fixture
def status_servers() -> Iterator[dict[int, FixedStatusHTTPServer]]:
    servers = {code: FixedStatusHTTPServer(code).start() for code in (401, 404)}
    try:
        yield servers
    finally:
        for server in servers.values():
            server.stop()


# ---------------------------------------------------------------------- camino feliz
async def test_mcp_tools_are_registered_callable_and_stopped_on_shutdown(
    tui, e2e_env: SimpleNamespace, scripted_model: ScriptedModel, tmp_path: Path
):
    pid_file = tmp_path / "mcp-server.pid"
    write_agent_conf(
        e2e_env.conf_dir,
        mcp={"transports": [scripted_mcp_transport(pid_file=pid_file)]},
    )
    scripted_model.enqueue(
        tool_turn("echo", {"text": "hola mcp"}, tool_use_id="tu-echo"),
        tool_turn("add", {"a": 40, "b": 2}, tool_use_id="tu-add"),
        text_turn("echo y suma hechos"),
    )

    async with tui() as driver:
        pid = read_pid(pid_file)
        assert process_alive(pid)
        assert driver.runtime.ready, driver.runtime.error_message
        # Sin fallos de arranque no hay informe MCP en la conversación.
        assert not any(
            _("ui.commands.status.mcp") in text or "MCP" in text for text in driver.agent_messages()
        ), driver.agent_messages()

        reply = await driver.submit("usa las tools MCP")
        assert reply == "echo y suma hechos"

        first_call = scripted_model.calls[0]
        assert SCRIPTED_TOOLS <= set(first_call.tool_names)
        assert CUSTOM_TOOLS <= set(first_call.tool_names)

        results = {result["toolUseId"]: result for result in scripted_model.tool_results()}
        assert results["tu-echo"]["status"] == "success"
        assert _tool_result_text(results["tu-echo"]) == "echo: hola mcp"
        assert results["tu-add"]["status"] == "success"
        assert "42" in _tool_result_text(results["tu-add"])

        status = await driver.submit("/status")
        assert f"- {_('ui.commands.status.mcp')}:" in status
        assert f"  - {_ready_line('e2e-stdio', len(SCRIPTED_TOOLS))}" in status

    # Al salir del TUI el runtime se apaga y el subproceso del servidor debe morir con él.
    assert wait_for_process_exit(pid), f"el servidor MCP (pid {pid}) sigue vivo tras shutdown"


async def test_mcp_env_passthrough_reaches_server_and_missing_vars_are_flagged(
    tui, e2e_env: SimpleNamespace, scripted_model: ScriptedModel, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(TOKEN_ENV, "token-e2e-123")
    monkeypatch.delenv(MISSING_ENV, raising=False)
    write_agent_conf(
        e2e_env.conf_dir,
        mcp={
            "transports": [
                scripted_mcp_transport(
                    "env-stdio",
                    env={"SHELL_SENTINEL_E2E_MCP_STATIC": "static-value"},
                    env_passthrough=[TOKEN_ENV, MISSING_ENV],
                )
            ]
        },
    )
    scripted_model.enqueue(
        tool_turn("env_value", {"name": TOKEN_ENV}, tool_use_id="tu-token"),
        tool_turn("env_value", {"name": "SHELL_SENTINEL_E2E_MCP_STATIC"}, tool_use_id="tu-static"),
        tool_turn("env_value", {"name": MISSING_ENV}, tool_use_id="tu-missing"),
        text_turn("ok"),
    )

    async with tui() as driver:
        await driver.submit("lee el entorno del servidor")
        results = {result["toolUseId"]: result for result in scripted_model.tool_results()}
        assert _tool_result_text(results["tu-token"]) == "token-e2e-123"
        assert _tool_result_text(results["tu-static"]) == "static-value"
        assert _tool_result_text(results["tu-missing"]) == "<unset>"

        status = await driver.submit("/status")
        warning = _("agent.mcp.missing_env", names=MISSING_ENV)
        assert f"  - {_ready_line('env-stdio', len(SCRIPTED_TOOLS))} — {warning}" in status


async def test_mcp_tool_errors_reach_model_and_tui_stays_responsive(
    tui, e2e_env: SimpleNamespace, scripted_model: ScriptedModel
):
    """Un ``ToolError`` declarado lleva su mensaje al modelo; un crash llega como error
    genérico sin filtrar el detalle (comportamiento de mcp 2.x). El agente sigue en ambos
    casos."""

    write_agent_conf(e2e_env.conf_dir, mcp={"transports": [scripted_mcp_transport()]})
    scripted_model.enqueue(
        tool_turn("fail", {"message": "boom from mcp"}, tool_use_id="tu-fail"),
        tool_turn("crash", {"secret": "do-not-leak"}, tool_use_id="tu-crash"),
        text_turn("las tools fallaron, lo tengo en cuenta"),
    )

    async with tui() as driver:
        reply = await driver.submit("provoca errores en las tools MCP")
        assert reply == "las tools fallaron, lo tengo en cuenta"
        results = {result["toolUseId"]: result for result in scripted_model.tool_results()}
        assert results["tu-fail"]["status"] == "error"
        assert "boom from mcp" in _tool_result_text(results["tu-fail"])
        assert results["tu-crash"]["status"] == "error"
        crash_text = _tool_result_text(results["tu-crash"])
        assert "crash" in crash_text and "do-not-leak" not in crash_text, crash_text
        assert driver.app._busy is False
        assert _("connection.status.thinking") not in driver.footer()


async def test_mcp_disabled_registers_no_server_tools(
    tui, e2e_env: SimpleNamespace, scripted_model: ScriptedModel
):
    write_agent_conf(
        e2e_env.conf_dir,
        mcp={"enabled": False, "transports": [scripted_mcp_transport()]},
    )
    scripted_model.enqueue(text_turn("sin mcp"))

    async with tui() as driver:
        await driver.submit("hola")
        assert not (SCRIPTED_TOOLS & set(scripted_model.calls[0].tool_names))
        status = await driver.submit("/status")
        assert _("ui.commands.status.mcp") not in status


# ---------------------------------------------------------------------- fallos de arranque
async def test_failed_mcp_servers_are_diagnosed_and_agent_keeps_working(
    tui,
    e2e_env: SimpleNamespace,
    scripted_model: ScriptedModel,
    ssh: ScriptedSSHServer,
    connect_line: str,
    status_servers: dict[int, FixedStatusHTTPServer],
):
    unreachable_url = closed_port_url()
    url_401 = status_servers[401].url()
    url_404 = status_servers[404].url()
    transports = [
        scripted_mcp_transport("good-stdio"),
        missing_command_transport("missing-cmd"),
        scripted_mcp_transport("exits-stdio", mode="exit"),
        http_transport("http-401", url_401),
        http_transport("http-404", url_404),
        http_transport("unreachable", unreachable_url),
    ]
    write_agent_conf(e2e_env.conf_dir, mcp={"transports": transports})
    ssh.script["uptime"] = CommandResult(0, "up 3 days\n")
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "uptime"}, tool_use_id="tu-ssh"),
        tool_turn("echo", {"text": "sigo vivo"}, tool_use_id="tu-echo"),
        text_turn("todo en orden"),
    )

    async with tui() as driver:
        assert driver.runtime.ready, driver.runtime.error_message
        report = _mcp_report(driver, failed=5, total=6)
        exits_transport = transports[2]
        _assert_failure_reported(
            report,
            "missing-cmd",
            "stdio",
            _("agent.mcp.failure.command_not_found", command=transports[1]["command"]),
        )
        _assert_failure_reported(
            report,
            "exits-stdio",
            "stdio",
            _("agent.mcp.failure.process_exited", command=exits_transport["command"]),
        )
        _assert_failure_reported(
            report,
            "http-401",
            "streamable_http",
            _("agent.mcp.failure.unauthorized", url=url_401, status=401),
        )
        _assert_failure_reported(
            report,
            "http-404",
            "streamable_http",
            _("agent.mcp.failure.not_found", url=url_404),
        )
        _assert_failure_reported(
            report,
            "unreachable",
            "streamable_http",
            _("agent.mcp.failure.unreachable", url=unreachable_url, detail="DETAIL"),
        )
        assert "good-stdio" not in report
        assert status_servers[401].requests, "el cliente MCP nunca llegó al servidor 401"

        await driver.submit(connect_line)
        reply = await driver.submit("comprueba el servidor y saluda por MCP")
        assert reply == "todo en orden"
        assert ssh.recorded_commands == ["uptime"]
        assert SCRIPTED_TOOLS <= set(scripted_model.calls[0].tool_names)
        results = {result["toolUseId"]: result for result in scripted_model.tool_results()}
        assert results["tu-ssh"]["status"] == "success"
        assert _tool_result_text(results["tu-echo"]) == "echo: sigo vivo"

        status = await driver.submit("/status")
        assert f"  - {_ready_line('good-stdio', len(SCRIPTED_TOOLS))}" in status
        for identifier in ("missing-cmd", "exits-stdio", "http-401", "http-404", "unreachable"):
            assert f"`{identifier}`" in status


async def test_hung_mcp_server_is_abandoned_within_timeout_and_killed(
    tui, e2e_env: SimpleNamespace, scripted_model: ScriptedModel, tmp_path: Path
):
    pid_file = tmp_path / "hung.pid"
    timeout_seconds = 1
    write_agent_conf(
        e2e_env.conf_dir,
        mcp={
            "transports": [
                scripted_mcp_transport(
                    "hung-stdio", mode="hang", pid_file=pid_file, timeout_seconds=timeout_seconds
                ),
                scripted_mcp_transport("good-stdio"),
            ]
        },
    )
    scripted_model.enqueue(text_turn("listo"))

    started = time.monotonic()
    async with tui() as driver:
        elapsed = time.monotonic() - started
        assert driver.runtime.ready, driver.runtime.error_message
        # El saludo colgado no puede retener el arranque más allá del timeout más el margen.
        assert elapsed < timeout_seconds + 10, f"el TUI tardó {elapsed:.1f}s en arrancar"
        pid = read_pid(pid_file)

        report = _mcp_report(driver, failed=1, total=2)
        _assert_failure_reported(
            report,
            "hung-stdio",
            "stdio",
            _("agent.mcp.failure.timeout", timeout=timeout_seconds),
        )

        reply = await driver.submit("hola")
        assert reply == "listo"
        assert SCRIPTED_TOOLS <= set(scripted_model.calls[0].tool_names)

    assert wait_for_process_exit(pid), f"el servidor colgado (pid {pid}) sigue vivo tras shutdown"
