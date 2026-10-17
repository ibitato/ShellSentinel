"""Diagnóstico de fallos al iniciar servidores MCP.

Strands envuelve los errores de arranque en ``MCPClientInitializationError`` y mcp 2.x
los anida en grupos de excepciones de anyio, de modo que el mensaje visible suele ser
``unhandled errors in a TaskGroup``. Este módulo recorre la cadena completa, localiza
la causa real y la traduce a un mensaje con la acción que debe tomar la persona operadora.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import StrEnum

import httpx2
from mcp.shared.exceptions import MCPError

from ..localization import _


class MCPFailureKind(StrEnum):
    COMMAND_NOT_FOUND = "command_not_found"
    COMMAND_NOT_EXECUTABLE = "command_not_executable"
    PROCESS_EXITED = "process_exited"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    HTTP_ERROR = "http_error"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"
    INVALID_CONFIG = "invalid_config"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MCPFailure:
    kind: MCPFailureKind
    detail: str
    status_code: int | None = None


# Mensajes que mcp 2.x sintetiza cuando el servidor responde con un estado HTTP de error
# sin cuerpo JSON-RPC (ver ``mcp.client.streamable_http``).
_MCP_NOT_FOUND = "Not Found"
_MCP_HTTP_ERROR = "Server returned an error response"
_MCP_CONNECTION_CLOSED = "Connection closed"


def iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    """Recorre en profundidad grupos de excepciones, ``__cause__`` y ``__context__``."""

    pending: list[BaseException] = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        nested: list[BaseException] = list(getattr(current, "exceptions", ()) or ())
        if current.__cause__ is not None:
            nested.append(current.__cause__)
        elif current.__context__ is not None and not current.__suppress_context__:
            nested.append(current.__context__)
        # Se apilan en orden inverso para visitar primero el primer hijo.
        pending.extend(reversed(nested))


def _root_detail(chain: Sequence[BaseException]) -> str:
    for candidate in reversed(chain):
        text = str(candidate).strip()
        if text:
            return text.splitlines()[0]
    return type(chain[-1]).__name__ if chain else ""


def _status_failure(status: int, detail: str) -> MCPFailure:
    if status in (401, 403):
        return MCPFailure(MCPFailureKind.UNAUTHORIZED, detail, status)
    if status == 404:
        return MCPFailure(MCPFailureKind.NOT_FOUND, detail, status)
    return MCPFailure(MCPFailureKind.HTTP_ERROR, detail, status)


def classify_mcp_failure(
    exc: BaseException,
    transport_type: str,
    http_status: int | None = None,
) -> MCPFailure:
    """Clasifica un fallo de arranque MCP.

    ``http_status`` es el último estado HTTP de error observado por el cliente httpx2 del
    transporte; permite distinguir un 401 de un 500 aunque mcp 2.x solo exponga un
    ``MCPError`` genérico.
    """

    chain = list(iter_exception_chain(exc))
    detail = _root_detail(chain)
    is_stdio = transport_type == "stdio"

    for item in chain:
        if isinstance(item, ValueError) and item is exc:
            return MCPFailure(MCPFailureKind.INVALID_CONFIG, detail)
        if is_stdio and isinstance(item, FileNotFoundError):
            return MCPFailure(MCPFailureKind.COMMAND_NOT_FOUND, str(item))
        if is_stdio and isinstance(item, PermissionError):
            return MCPFailure(MCPFailureKind.COMMAND_NOT_EXECUTABLE, str(item))
        if isinstance(item, httpx2.HTTPStatusError):
            return _status_failure(item.response.status_code, detail)
        if isinstance(item, (httpx2.TimeoutException, TimeoutError)):
            return MCPFailure(MCPFailureKind.TIMEOUT, detail)
        if isinstance(item, (httpx2.ConnectError, ConnectionRefusedError, socket.gaierror)):
            return MCPFailure(MCPFailureKind.UNREACHABLE, detail)

    if http_status is not None and http_status >= 400:
        return _status_failure(http_status, detail)

    for item in chain:
        if not isinstance(item, MCPError):
            continue
        if item.message == _MCP_NOT_FOUND:
            return MCPFailure(MCPFailureKind.NOT_FOUND, detail, 404)
        if item.message == _MCP_HTTP_ERROR:
            return MCPFailure(MCPFailureKind.HTTP_ERROR, detail)
        if item.message == _MCP_CONNECTION_CLOSED and is_stdio:
            return MCPFailure(MCPFailureKind.PROCESS_EXITED, detail)

    return MCPFailure(MCPFailureKind.UNKNOWN, detail)


def describe_mcp_failure(
    failure: MCPFailure,
    *,
    command: str | None = None,
    url: str | None = None,
    timeout_seconds: float | None = None,
    missing_env: Sequence[str] = (),
) -> str:
    """Devuelve un mensaje localizado con la causa y la acción recomendada."""

    status = failure.status_code if failure.status_code is not None else "?"
    message = _(
        f"agent.mcp.failure.{failure.kind.value}",
        command=command or "",
        url=url or "",
        status=status,
        timeout=timeout_seconds if timeout_seconds is not None else "",
        detail=failure.detail,
    )
    if missing_env:
        message += " " + _("agent.mcp.missing_env", names=", ".join(missing_env))
    return message
