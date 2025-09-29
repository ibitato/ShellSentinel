"""Inicialización y ejecución del agente Strands."""

from __future__ import annotations

import logging
from contextlib import ExitStack
from typing import Any

from mcp import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from strands.agent.agent_result import AgentResult
from strands.tools.mcp import MCPClient

from ..connection import SSHConnectionManager
from .config import AgentConfig, AgentConfigError, MCPConfig, MCPTransportConfig, load_agent_config
from .factory import AgentFactory
from .tools import remote_ssh_command, resolve_tools


class MCPManager:
    """Gestiona la conexión con servidores MCP según la configuración."""

    def __init__(self, config: MCPConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger
        self._clients: list[MCPClient] = []
        self._stack: ExitStack | None = None

    def activate(self) -> list[Any]:
        if not self._config.enabled or not self._config.transports:
            return []
        tools: list[Any] = []
        self._stack = ExitStack()
        for transport in self._config.transports:
            try:
                client = self._create_client(transport)
            except Exception as exc:  # pragma: no cover - defensivo
                self._logger.warning(
                    "No se pudo crear el cliente MCP '%s': %s", transport.identifier, exc
                )
                continue
            try:
                self._stack.enter_context(client)
            except Exception as exc:  # pragma: no cover - depende del entorno
                self._logger.warning(
                    "No se pudo iniciar el cliente MCP '%s': %s", transport.identifier, exc
                )
                continue
            self._clients.append(client)
            try:
                tools.extend(client.list_tools_sync())
            except Exception as exc:  # pragma: no cover - depende del servidor MCP
                self._logger.warning(
                    "Error obteniendo herramientas del servidor MCP '%s': %s",
                    transport.identifier,
                    exc,
                )
        return tools

    def close(self) -> None:
        if self._stack:
            self._stack.close()
        self._stack = None
        self._clients.clear()

    def _create_client(self, cfg: MCPTransportConfig) -> MCPClient:
        if cfg.transport_type == "stdio":
            if not cfg.command:
                raise ValueError("El transporte MCP 'stdio' requiere el campo 'command'.")
            params = StdioServerParameters(
                command=cfg.command,
                args=list(cfg.args),
                env=dict(cfg.env),
                cwd=cfg.cwd,
            )
            return MCPClient(lambda: stdio_client(params))
        if cfg.transport_type == "sse":
            if not cfg.url:
                raise ValueError("El transporte MCP 'sse' requiere el campo 'url'.")
            return MCPClient(lambda: sse_client(cfg.url, headers=dict(cfg.headers)))
        if cfg.transport_type == "streamable_http":
            if not cfg.url:
                raise ValueError("El transporte MCP 'streamable_http' requiere el campo 'url'.")
            return MCPClient(
                lambda: streamablehttp_client(
                    cfg.url,
                    headers=dict(cfg.headers),
                    timeout=cfg.timeout_seconds,
                )
            )
        raise ValueError(f"Tipo de transporte MCP no soportado: {cfg.transport_type}")


class AgentRuntime:
    """Orquesta la vida del agente Strands dentro de la aplicación TUI."""

    def __init__(
        self,
        connection_manager: SSHConnectionManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._logger = logger or logging.getLogger("smart_ai_sys_admin.agent.runtime")
        self._config: AgentConfig | None = None
        self._factory: AgentFactory | None = None
        self._mcp_manager: MCPManager | None = None
        self._agent = None
        self._status_message: str | None = None
        self._error_message: str | None = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready and self._agent is not None

    @property
    def status_message(self) -> str | None:
        return self._status_message

    @property
    def error_message(self) -> str | None:
        return self._error_message

    def initialize(self) -> None:
        try:
            config = load_agent_config()
        except AgentConfigError as exc:
            self._error_message = (
                "⚠️ No se pudo cargar `conf/agent.conf`: "
                f"{exc}. El modo agente permanecerá deshabilitado."
            )
            self._logger.error("Error cargando la configuración del agente: %s", exc)
            return

        self._config = config
        self._factory = AgentFactory(config)

        tool_name = self._factory.remote_command.name
        if tool_name and tool_name != remote_ssh_command.tool.spec.get("name"):
            remote_ssh_command.tool.spec["name"] = tool_name

        base_tools = list(resolve_tools())
        self._mcp_manager = MCPManager(config.mcp, self._logger)
        try:
            mcp_tools = self._mcp_manager.activate()
        except Exception as exc:  # pragma: no cover - defensivo
            self._logger.error("Error activando transporte MCP: %s", exc)
            mcp_tools = []
        all_tools = [*base_tools, *mcp_tools]

        try:
            build = self._factory.build_agent(all_tools)
        except Exception as exc:  # pragma: no cover - depende del entorno
            self._logger.error("Error inicializando el agente Strands: %s", exc)
            self._error_message = (
                "⚠️ No fue posible inicializar el agente Strands. Revisa los registros "
                "para más detalles."
            )
            if self._mcp_manager:
                self._mcp_manager.close()
            return

        self._agent = build.agent
        # Compartimos la conexión SSH con la tool personalizada
        self._agent.ssh_manager = self._connection_manager  # type: ignore[attr-defined]
        timeout = self._factory.remote_command.timeout_seconds
        if timeout is not None:
            self._agent.remote_command_timeout = timeout  # type: ignore[attr-defined]
        self._ready = True
        config_path = config.config_path
        self._status_message = f"✅ Agente Strands inicializado (configuración: `{config_path}`)"

    def invoke(self, prompt: str) -> str:
        if not self.ready:
            raise RuntimeError("El agente no está disponible.")
        assert self._agent is not None
        try:
            result = self._agent(prompt)
        except Exception as exc:  # pragma: no cover - depende del proveedor
            self._logger.exception("Error ejecutando el agente")
            return f"❌ El agente falló al procesar la instrucción: {exc}"
        if isinstance(result, AgentResult):
            text = str(result).strip()
            return text or "(sin respuesta)"
        return str(result)

    def shutdown(self) -> None:
        if self._mcp_manager:
            self._mcp_manager.close()
        self._mcp_manager = None
        self._ready = False


__all__ = ["AgentRuntime"]
