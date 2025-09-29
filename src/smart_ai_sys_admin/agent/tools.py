"""Registro de herramientas para el agente Strands."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import Any

from strands import tool
from strands_tools import file_read, file_write, sleep
from strands_tools import shell as shell_tool

from ..connection import ConnectionError, NoActiveConnection, SSHConnectionManager

ToolCallable = Callable[..., Any]


@tool
async def remote_ssh_command(
    command: str,
    agent: Any,
    timeout_seconds: int | None = None,
) -> str:
    """Ejecuta un comando en el servidor remoto usando la sesión SSH activa."""

    manager = getattr(agent, "ssh_manager", None)
    if not isinstance(manager, SSHConnectionManager):
        return "❌ No hay una conexión SSH disponible. Usa `/conectar`."
    if not manager.is_connected:
        return "❌ No existe una sesión SSH activa. Usa `/conectar`."

    if timeout_seconds is None:
        timeout_seconds = getattr(agent, "remote_command_timeout", None)

    loop = asyncio.get_running_loop()

    def _run() -> tuple[int, str, str]:
        return manager.run_command(command, timeout=timeout_seconds)

    try:
        code, stdout, stderr = await loop.run_in_executor(None, _run)
    except NoActiveConnection as exc:
        return f"❌ {exc}"
    except ConnectionError as exc:
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
    "remote_ssh_command",
    "resolve_tools",
]
