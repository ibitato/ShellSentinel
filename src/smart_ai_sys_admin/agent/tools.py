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
from ..localization import _

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
        Nota: ajusta la sintaxis del comando a la plataforma remota (GNU/Linux,
        Unix o Windows con PowerShell/cmd).
    """

    manager = getattr(agent, "ssh_manager", None)
    if not isinstance(manager, SSHConnectionManager):
        return _("agent.tools.ssh_unavailable")
    if not manager.is_connected:
        return _("agent.tools.ssh_inactive")

    if timeout_seconds is None or timeout_seconds == "":
        timeout_seconds = getattr(agent, "remote_command_timeout", None)

    if timeout_seconds is None:
        timeout_seconds = DEFAULT_REMOTE_TIMEOUT

    try:
        timeout_int = int(float(timeout_seconds))
    except (TypeError, ValueError):
        return _("agent.tools.timeout_invalid")

    if timeout_int <= 0:
        return _("agent.tools.timeout_positive")

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
    summary: list[str] = [
        _("agent.tools.summary.exit_code", code=code)
    ]
    if output:
        summary.append(
            _("agent.tools.summary.stdout") + "\n" + output
        )
    if error:
        summary.append(
            _("agent.tools.summary.stderr") + "\n" + error
        )
    if not output and not error:
        summary.append(_("agent.tools.summary.empty"))
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


@tool
async def remote_sftp_transfer(
    action: str,
    local_path: str,
    remote_path: str,
    agent: Any,
    overwrite: bool | str | None = False,
) -> str:
    """Transfiere archivos entre la máquina local y el servidor remoto vía SFTP.

    Args:
        action: `"upload"`/`"put"` para subir o `"download"`/`"get"` para bajar archivos.
        local_path: ruta local de origen/destino según la acción.
        remote_path: ruta remota de destino/origen según la acción (formato POSIX,
            incluso en servidores Windows con SFTP).
        agent: referencia interna del agente Strands (inyectada automáticamente).
        overwrite: permite sobrescribir archivos existentes cuando es `True`.
    """

    manager = getattr(agent, "ssh_manager", None)
    if not isinstance(manager, SSHConnectionManager):
        return _("agent.tools.ssh_unavailable")
    if not manager.is_connected:
        return _("agent.tools.ssh_inactive")

    normalized_action = action.strip().lower()
    if normalized_action in {"upload", "put"}:
        direction = "upload"
    elif normalized_action in {"download", "get"}:
        direction = "download"
    else:
        return _("agent.tools.transfer.invalid_action")

    truthy_values = {"true", "1", "yes", "si", "sí", "ja", "wahr"}
    overwrite_flag = (
        bool(overwrite)
        if isinstance(overwrite, int | bool)
        else str(overwrite).lower() in truthy_values
    )

    loop = asyncio.get_running_loop()

    logger.debug(
        "remote_sftp_transfer ejecutando acción=%s local='%s' remote='%s' overwrite=%s",
        direction,
        local_path,
        remote_path,
        overwrite_flag,
    )

    def _run() -> str:
        if direction == "upload":
            manager.upload_file(local_path, remote_path, overwrite=overwrite_flag)
            return _(
                "agent.tools.transfer.upload_success",
                local=local_path,
                remote=remote_path,
            )
        local_result = manager.download_file(remote_path, local_path, overwrite=overwrite_flag)
        return _(
            "agent.tools.transfer.download_success",
            remote=remote_path,
            local=str(local_result),
        )

    try:
        return await loop.run_in_executor(None, _run)
    except NoActiveConnection as exc:
        logger.warning("remote_sftp_transfer sin conexión activa: %s", exc)
        return f"❌ {exc}"
    except ConnectionError as exc:
        logger.error("remote_sftp_transfer falló: %s", exc)
        return f"❌ {exc}"


DEFAULT_STRANDS_TOOLS: tuple[ToolCallable, ...] = (
    shell_tool,
    file_read,
    file_write,
    sleep,
    remote_ssh_command,
    remote_sftp_transfer,
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
    "remote_sftp_transfer",
    "resolve_tools",
]
logger = logging.getLogger("smart_ai_sys_admin.agent.tools")
