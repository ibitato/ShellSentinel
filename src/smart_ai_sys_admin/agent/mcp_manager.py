"""Conexión con servidores MCP: transportes, arranque acotado en el tiempo y estado."""

from __future__ import annotations

import asyncio
import logging
import math
import os
import threading
import time
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import anyio
import httpx2
from mcp import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

from ..localization import _
from .config import MCPConfig, MCPTransportConfig
from .mcp_diagnostics import MCPFailure, MCPFailureKind, classify_mcp_failure, describe_mcp_failure

# Timeout general (conexión, escritura, pool) de los transportes HTTP si no se configura.
DEFAULT_HTTP_TIMEOUT_SECONDS = 30.0
# Margen de lectura para flujos SSE de larga duración (mismo valor que el SDK de MCP).
SSE_READ_TIMEOUT_SECONDS = 300.0
# Tiempo máximo de arranque por servidor si no se configura ``timeout_seconds``.
DEFAULT_STARTUP_TIMEOUT_SECONDS = 30
# Margen sobre el ``startup_timeout`` de Strands antes de abandonar un arranque bloqueado.
STARTUP_GRACE_SECONDS = 5.0


@dataclass(frozen=True)
class MCPServerStatus:
    """Estado de un servidor MCP tras el arranque, pensado para mostrarse en la TUI."""

    identifier: str
    transport_type: str
    ready: bool
    tool_count: int = 0
    message: str | None = None


class _HTTPStatusProbe:
    """Recuerda el último estado HTTP de error recibido por un cliente httpx2.

    mcp 2.x convierte un 401/403/5xx de Streamable HTTP en un ``MCPError`` genérico; con
    esta sonda se puede indicar al operador la causa concreta.
    """

    def __init__(self) -> None:
        self.last_error_status: int | None = None

    async def __call__(self, response: httpx2.Response) -> None:
        if response.status_code >= 400:
            self.last_error_status = response.status_code


class _TransportAbort:
    """Permite cancelar desde otro hilo un transporte MCP cuyo saludo nunca termina.

    ``MCPClient.stop()`` de Strands solo resuelve un futuro que el hilo de fondo espera
    *después* de completar el saludo; si el servidor acepta la conexión pero no responde al
    ``initialize``, ``stop()`` se queda en ``join()`` y el subproceso ``stdio`` sigue vivo.
    El transporte se ejecuta dentro de un ``CancelScope`` de anyio que ``abort()`` cancela en
    el bucle de eventos del cliente: ``stdio_client`` mata el árbol de procesos al cancelarse,
    la cancelación la absorbe el propio scope y el hilo de fondo termina limpiamente.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._scope: anyio.CancelScope | None = None
        self._requested = False

    @property
    def requested(self) -> bool:
        return self._requested

    def abort(self) -> None:
        with self._lock:
            self._requested = True
            loop, scope = self._loop, self._scope
        if loop is None or scope is None:
            return
        try:
            loop.call_soon_threadsafe(scope.cancel)
        except RuntimeError:  # pragma: no cover - el bucle ya se cerró
            pass

    @asynccontextmanager
    async def wrap(self, transport: AbstractAsyncContextManager[Any]) -> AsyncIterator[Any]:
        with anyio.CancelScope() as scope:
            with self._lock:
                self._loop, self._scope = asyncio.get_running_loop(), scope
                if self._requested:
                    scope.cancel()
            try:
                async with transport as streams:
                    yield streams
            finally:
                with self._lock:
                    self._loop = self._scope = None


class _AbortableTransportFactory:
    """Factoría de transporte para ``MCPClient`` que envuelve la real en ``_TransportAbort``."""

    def __init__(
        self, inner: Callable[[], AbstractAsyncContextManager[Any]], abort: _TransportAbort
    ) -> None:
        self.inner = inner
        self.abort = abort

    def __call__(self) -> AbstractAsyncContextManager[Any]:
        return self.abort.wrap(self.inner())


def _http_timeout(timeout_seconds: float | None) -> httpx2.Timeout:
    """``timeout_seconds`` cubre conexión, escritura y pool; la lectura mantiene el margen SSE."""

    general = DEFAULT_HTTP_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
    return httpx2.Timeout(general, read=SSE_READ_TIMEOUT_SECONDS)


def _http_client_factory(probe: _HTTPStatusProbe):
    """Factoría compatible con ``McpHttpClientFactory`` de mcp, sin depender de módulos privados."""

    def factory(
        headers: dict[str, str] | None = None,
        timeout: httpx2.Timeout | None = None,
        auth: httpx2.Auth | None = None,
    ) -> httpx2.AsyncClient:
        kwargs: dict[str, Any] = {
            "follow_redirects": True,
            "timeout": timeout if timeout is not None else _http_timeout(None),
            "event_hooks": {"response": [probe]},
        }
        if headers is not None:
            kwargs["headers"] = headers
        if auth is not None:
            kwargs["auth"] = auth
        return httpx2.AsyncClient(**kwargs)

    return factory


@asynccontextmanager
async def _streamable_http_transport(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float | None,
    probe: _HTTPStatusProbe,
) -> AsyncIterator[Any]:
    """Abre un transporte Streamable HTTP de mcp 2.x con cabeceras y timeout propios.

    mcp 2.x ya no acepta ``headers``/``timeout`` sueltos: hay que pasarle un cliente
    httpx2 configurado. ``streamable_http_client`` solo cierra los clientes que crea él
    mismo, así que el nuestro se cierra aquí junto al transporte.
    """

    factory = _http_client_factory(probe)
    async with (
        factory(headers=dict(headers), timeout=_http_timeout(timeout_seconds)) as http_client,
        streamable_http_client(url, http_client=http_client) as streams,
    ):
        yield streams


def _startup_timeout(cfg: MCPTransportConfig) -> int:
    if cfg.timeout_seconds is None or cfg.timeout_seconds <= 0:
        return DEFAULT_STARTUP_TIMEOUT_SECONDS
    return max(1, math.ceil(cfg.timeout_seconds))


@dataclass
class _StartAttempt:
    cfg: MCPTransportConfig
    launched_at: float
    client: MCPClient | None = None
    abort: _TransportAbort | None = None
    tools: list[Any] = field(default_factory=list)
    error: BaseException | None = None
    started: bool = False
    abandoned: bool = False
    # El recolector ya ha lanzado el cierre del cliente; el hilo de arranque no debe repetirlo.
    stopping: bool = False
    done: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)


class MCPManager:
    """Gestiona la conexión con servidores MCP según la configuración.

    Todos los servidores arrancan en paralelo y cada uno dispone de un plazo máximo; un
    servidor que no responde se marca como fallido en lugar de bloquear el arranque.
    """

    def __init__(
        self,
        config: MCPConfig,
        logger: logging.Logger,
        *,
        startup_grace_seconds: float = STARTUP_GRACE_SECONDS,
    ) -> None:
        self._config = config
        self._logger = logger
        self._startup_grace_seconds = startup_grace_seconds
        self._clients: list[MCPClient] = []
        self._statuses: list[MCPServerStatus] = []
        self._probes: dict[str, _HTTPStatusProbe] = {}
        self._abort_handles: dict[str, _TransportAbort] = {}
        self._missing_env: dict[str, tuple[str, ...]] = {}

    @property
    def statuses(self) -> tuple[MCPServerStatus, ...]:
        return tuple(self._statuses)

    def activate(self) -> list[Any]:
        self._statuses = []
        if not self._config.enabled or not self._config.transports:
            return []
        attempts = [self._launch(cfg) for cfg in self._config.transports]
        tools: list[Any] = []
        for attempt in attempts:
            tools.extend(self._collect(attempt))
        return tools

    def close(self) -> None:
        clients, self._clients = self._clients, []
        for client in clients:
            self._stop_client(client)

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------

    def _launch(self, cfg: MCPTransportConfig) -> _StartAttempt:
        attempt = _StartAttempt(cfg=cfg, launched_at=time.monotonic())
        try:
            attempt.client = self._create_client(cfg)
            attempt.abort = self._abort_handles.get(cfg.identifier)
        except Exception as exc:
            attempt.error = exc
            attempt.done.set()
            return attempt
        threading.Thread(
            target=self._start_client,
            args=(attempt,),
            name=f"mcp-start-{cfg.identifier}",
            daemon=True,
        ).start()
        return attempt

    def _start_client(self, attempt: _StartAttempt) -> None:
        assert attempt.client is not None
        try:
            attempt.client.start()
            # Se publica antes de listar herramientas para que el recolector sepa que ya hay
            # un proceso o sesión que cerrar si el listado se queda colgado.
            with attempt.lock:
                attempt.started = True
                abandoned = attempt.abandoned
            # Si el plazo venció durante el saludo nadie usará este cliente: no se listan
            # herramientas (podría colgarse) y se cierra más abajo.
            if not abandoned:
                attempt.tools = list(attempt.client.list_tools_sync())
        except Exception as exc:
            attempt.error = exc
        finally:
            with attempt.lock:
                cleanup_here = attempt.abandoned and attempt.started and not attempt.stopping
                attempt.done.set()
        if cleanup_here:
            # El plazo ya venció y nadie gestionará este cliente: se cierra aquí.
            self._stop_client(attempt.client)

    def _collect(self, attempt: _StartAttempt) -> list[Any]:
        cfg = attempt.cfg
        deadline = attempt.launched_at + _startup_timeout(cfg) + self._startup_grace_seconds
        attempt.done.wait(max(0.0, deadline - time.monotonic()))
        with attempt.lock:
            if not attempt.done.is_set():
                attempt.abandoned = True
                if attempt.started:
                    # Saludo completado pero el listado de herramientas no responde: se cierra
                    # en segundo plano para no bloquear la TUI ni dejar el proceso huérfano.
                    attempt.stopping = True
                    threading.Thread(
                        target=self._stop_client,
                        args=(attempt.client,),
                        name=f"mcp-stop-{cfg.identifier}",
                        daemon=True,
                    ).start()
                elif attempt.abort is not None:
                    # Saludo colgado: ``stop()`` de Strands no lo desbloquea, así que se cancela
                    # el transporte (mata el subproceso stdio o cierra la sesión HTTP).
                    attempt.abort.abort()
                failure = MCPFailure(MCPFailureKind.TIMEOUT, "startup deadline exceeded")
                self._record_failure(cfg, failure)
                return []

        if attempt.started and attempt.client is not None:
            self._clients.append(attempt.client)

        if attempt.error is not None:
            probe = self._probes.get(cfg.identifier)
            failure = classify_mcp_failure(
                attempt.error,
                cfg.transport_type,
                http_status=probe.last_error_status if probe else None,
            )
            self._logger.debug(
                "Traza completa del fallo MCP '%s'", cfg.identifier, exc_info=attempt.error
            )
            self._record_failure(cfg, failure)
            return []

        missing_env = self._missing_env.get(cfg.identifier, ())
        warning = _("agent.mcp.missing_env", names=", ".join(missing_env)) if missing_env else None
        self._statuses.append(
            MCPServerStatus(
                identifier=cfg.identifier,
                transport_type=cfg.transport_type,
                ready=True,
                tool_count=len(attempt.tools),
                message=warning,
            )
        )
        self._logger.info(
            "Servidor MCP '%s' listo con %d herramientas", cfg.identifier, len(attempt.tools)
        )
        return attempt.tools

    def _record_failure(self, cfg: MCPTransportConfig, failure: MCPFailure) -> None:
        message = describe_mcp_failure(
            failure,
            command=cfg.command,
            url=cfg.url,
            timeout_seconds=_startup_timeout(cfg),
            missing_env=self._missing_env.get(cfg.identifier, ()),
        )
        self._logger.warning(
            "Servidor MCP '%s' no disponible (%s): %s", cfg.identifier, failure.kind, failure.detail
        )
        self._statuses.append(
            MCPServerStatus(
                identifier=cfg.identifier,
                transport_type=cfg.transport_type,
                ready=False,
                message=message,
            )
        )

    def _stop_client(self, client: MCPClient) -> None:
        try:
            client.stop(None, None, None)
        except Exception as exc:  # pragma: no cover - depende del servidor MCP
            self._logger.warning("Error cerrando el cliente MCP: %s", exc)

    # ------------------------------------------------------------------
    # Transportes
    # ------------------------------------------------------------------

    def _create_client(self, cfg: MCPTransportConfig) -> MCPClient:
        factory = self._create_transport_factory(cfg)
        abort = _TransportAbort()
        self._abort_handles[cfg.identifier] = abort
        return MCPClient(
            _AbortableTransportFactory(factory, abort), startup_timeout=_startup_timeout(cfg)
        )

    def _create_transport_factory(
        self, cfg: MCPTransportConfig
    ) -> Callable[[], AbstractAsyncContextManager[Any]]:
        if cfg.transport_type == "stdio":
            if not cfg.command:
                raise ValueError("El transporte MCP 'stdio' requiere el campo 'command'.")
            env = {
                name: value
                for name in cfg.env_passthrough
                if (value := os.getenv(name)) is not None
            }
            missing_env = tuple(sorted(set(cfg.env_passthrough) - env.keys()))
            if missing_env:
                self._missing_env[cfg.identifier] = missing_env
                self._logger.warning(
                    "Variables de entorno MCP no definidas para '%s': %s",
                    cfg.identifier,
                    ", ".join(missing_env),
                )
            env.update(cfg.env)
            params = StdioServerParameters(
                command=cfg.command,
                args=list(cfg.args),
                env=env,
                cwd=cfg.cwd,
            )
            return lambda: stdio_client(params)
        if cfg.transport_type == "sse":
            if not cfg.url:
                raise ValueError("El transporte MCP 'sse' requiere el campo 'url'.")
            probe = self._probes.setdefault(cfg.identifier, _HTTPStatusProbe())
            general = (
                DEFAULT_HTTP_TIMEOUT_SECONDS if cfg.timeout_seconds is None else cfg.timeout_seconds
            )
            return lambda: sse_client(
                cfg.url,
                headers=dict(cfg.headers),
                timeout=general,
                sse_read_timeout=SSE_READ_TIMEOUT_SECONDS,
                httpx_client_factory=_http_client_factory(probe),
            )
        if cfg.transport_type == "streamable_http":
            if not cfg.url:
                raise ValueError("El transporte MCP 'streamable_http' requiere el campo 'url'.")
            probe = self._probes.setdefault(cfg.identifier, _HTTPStatusProbe())
            return lambda: _streamable_http_transport(
                cfg.url, cfg.headers, cfg.timeout_seconds, probe
            )
        raise ValueError(f"Tipo de transporte MCP no soportado: {cfg.transport_type}")
