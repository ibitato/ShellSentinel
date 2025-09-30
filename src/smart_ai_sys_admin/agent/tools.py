"""Registro de herramientas para el agente Strands."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from typing import Any

from strands import tool
from strands_tools import file_read, file_write, sleep
from strands_tools import shell as shell_tool

from ..connection import ConnectionError, NoActiveConnection, SSHConnectionManager

ToolCallable = Callable[..., Any]


DEFAULT_REMOTE_TIMEOUT = 900


@tool
async def remote_ssh_command(
    command: str,
    agent: Any,
    timeout_seconds: int | float | str | None = None,
) -> str:
    """Ejecuta un comando en el servidor remoto usando la sesión SSH activa.

    Args:
        command: instrucción a ejecutar a través de SSH.
        agent: referencia interna del agente Strands (inyectada automáticamente).
        timeout_seconds: opcional, límite en segundos para la ejecución. Si no se
            indica, se utiliza el valor por defecto configurado (15 minutos salvo
            que `conf/agent.conf` especifique otro).
    """

    manager = getattr(agent, "ssh_manager", None)
    if not isinstance(manager, SSHConnectionManager):
        return "❌ No hay una conexión SSH disponible. Usa `/conectar`."
    if not manager.is_connected:
        return "❌ No existe una sesión SSH activa. Usa `/conectar`."

    if timeout_seconds is None or timeout_seconds == "":
        timeout_seconds = getattr(agent, "remote_command_timeout", None)

    if timeout_seconds is None:
        timeout_seconds = DEFAULT_REMOTE_TIMEOUT

    try:
        timeout_int = int(float(timeout_seconds))
    except (TypeError, ValueError):
        return "❌ El parámetro `timeout_seconds` debe ser un número de segundos."

    if timeout_int <= 0:
        return "❌ `timeout_seconds` debe ser mayor que cero."

    timeout_seconds = timeout_int

    loop = asyncio.get_running_loop()

    logger.debug("remote_ssh_command ejecutando: '%s' (timeout=%ss)", command, timeout_seconds)

    def _run() -> tuple[int, str, str]:
        return manager.run_command(command, timeout=timeout_seconds)

    try:
        code, stdout, stderr = await loop.run_in_executor(None, _run)
    except NoActiveConnection as exc:
        logger.warning("remote_ssh_command sin conexión activa: %s", exc)
        return f"❌ {exc}"
    except ConnectionError as exc:
        logger.error("remote_ssh_command falló: %s", exc)
        return f"❌ {exc}"
    output = stdout.strip()
    error = stderr.strip()
    summary: list[str] = [f"Código de salida: {code}"]
    if output:
        summary.append("Salida:\n" + output)
    if error:
        summary.append("Errores:\n" + error)
    if not output and not error:
        summary.append("(sin salida)")
    stdout_preview = stdout.strip()
    stderr_preview = stderr.strip()
    logger.debug(
        "remote_ssh_command finalizado con código %s (stdout=%d bytes, stderr=%d bytes)",
        code,
        len(stdout_preview),
        len(stderr_preview),
    )
    if stdout_preview:
        logger.debug("stdout: %s", stdout_preview[:400])
    if stderr_preview:
        logger.debug("stderr: %s", stderr_preview[:400])
    return "\n\n".join(summary)


DEFAULT_STRANDS_TOOLS: tuple[ToolCallable, ...] = (
    shell_tool,
    file_read,
    file_write,
    sleep,
    remote_ssh_command,
)


def resolve_tools(custom_tools: Sequence[ToolCallable] | None = None) -> list[ToolCallable]:
    combined = list(DEFAULT_STRANDS_TOOLS)
    if custom_tools:
        combined.extend(custom_tools)
    return combined


__all__ = [
    "DEFAULT_STRANDS_TOOLS",
    "DEFAULT_REMOTE_TIMEOUT",
    "remote_ssh_command",
    "resolve_tools",
]
logger = logging.getLogger("smart_ai_sys_admin.agent.tools")
