"""Procesador de comandos slash para la interfaz TUI."""

from __future__ import annotations

import logging
import shlex
from collections.abc import Callable
from pathlib import Path

from ..config import OutputPanelConfig
from ..connection import (
    ConnectionAlreadyOpen,
    ConnectionError,
    NoActiveConnection,
    SSHConnectionManager,
)
from ..localization import _

PRIMARY_CONNECT = "/connect"
PRIMARY_DISCONNECT = "/disconnect"
PRIMARY_HELP = "/help"
PRIMARY_EXIT = "/exit"

CONNECT_ALIASES = frozenset({PRIMARY_CONNECT, "/conectar", "/verbinden"})
DISCONNECT_ALIASES = frozenset({PRIMARY_DISCONNECT, "/desconectar", "/trennen"})
HELP_ALIASES = frozenset({PRIMARY_HELP, "/ayuda", "/hilfe"})
EXIT_ALIASES = frozenset({PRIMARY_EXIT, "/salir", "/quit", "/beenden"})


class SlashCommandProcessor:
    """Encapsula la lógica de comandos personalizados del agente."""

    def __init__(
        self,
        connection_manager: SSHConnectionManager,
        output_config: OutputPanelConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._output_config = output_config
        self._logger = logger or logging.getLogger("smart_ai_sys_admin.ui.commands")

    def process(self, content: str) -> str | None:
        content = content.strip()
        if not content:
            return ""
        if not content.startswith("/"):
            return None
        return self._execute_command(content)

    def _execute_command(self, raw_command: str) -> str:
        try:
            parts = shlex.split(raw_command)
        except ValueError as exc:
            self._logger.warning("Comando inválido: %s", exc)
            return self._format_help(
                _("ui.commands.parse_error", error=str(exc)),
                self._help_overview(),
            )
        if not parts:
            return self._output_config.placeholder_response_markdown
        command = parts[0].lower()
        handler: Callable[[list[str]], str] | None
        if command in CONNECT_ALIASES:
            handler = self._command_connect
        elif command in DISCONNECT_ALIASES:
            handler = self._command_disconnect
        elif command in HELP_ALIASES:
            handler = self._command_help
        else:
            self._logger.info("Comando desconocido: %s", command)
            return self._format_help(
                _("ui.commands.unknown", command=command),
                self._help_overview(),
            )
        self._logger.info("Procesando comando %s con argumentos %s", command, parts[1:])
        try:
            return handler(parts[1:])
        except Exception as exc:  # pragma: no cover - salvaguarda adicional
            self._logger.exception("Error interno procesando %s", command)
            return _(
                "ui.commands.internal_error",
                command=command,
                error=str(exc),
            )

    def _command_connect(self, args: list[str]) -> str:
        if len(args) < 3:
            self._logger.info("Parámetros insuficientes para %s: %s", PRIMARY_CONNECT, args)
            return self._format_help(
                _("ui.commands.connect.missing_args", command=PRIMARY_CONNECT),
                self._connect_help(),
            )
        host, username, secret = args[0], args[1], args[2]
        password: str | None = None
        key_path: str | None = None
        candidate = Path(secret).expanduser()
        if candidate.exists():
            key_path = str(candidate)
        else:
            password = secret
        try:
            details = self._connection_manager.connect(
                host,
                username,
                password=password,
                key_path=key_path,
            )
        except ConnectionAlreadyOpen as exc:
            self._logger.info("Intento de reconectar mientras existe una sesión activa")
            return self._format_help(str(exc), self._disconnect_help())
        except ConnectionError as exc:
            self._logger.warning("Fallo en %s: %s", PRIMARY_CONNECT, exc)
            return self._format_help(
                _("ui.commands.connect.failure", error=str(exc)),
                self._connect_help(),
            )
        self._logger.info(
            "Conexión abierta con %s@%s usando %s",
            details.username,
            details.host,
            details.auth_method,
        )
        auth_label = self._auth_label(details.auth_method)
        return _(
            "ui.commands.connect.success",
            username=details.username,
            host=details.host,
            auth_label=auth_label,
        )

    def _command_disconnect(
        self, args: list[str]
    ) -> str:  # noqa: ARG002 - placeholder para futuros argumentos
        if args:
            self._logger.info("Se ignorarán argumentos extra en %s: %s", PRIMARY_DISCONNECT, args)
            return self._format_help(
                _("ui.commands.disconnect.extra_args", command=PRIMARY_DISCONNECT),
                self._disconnect_help(),
            )
        try:
            self._connection_manager.disconnect()
        except NoActiveConnection:
            self._logger.info("Solicitud de /desconectar sin sesión activa")
            return self._format_help(
                _("ui.commands.disconnect.no_active"),
                self._disconnect_help(),
            )
        except ConnectionError as exc:
            self._logger.error("Fallo cerrando la conexión: %s", exc)
            return self._format_help(
                _("ui.commands.disconnect.failure", error=str(exc)),
                self._disconnect_help(),
            )
        self._logger.info("Conexión cerrada correctamente")
        return _("ui.commands.disconnect.success")

    def _command_help(self, args: list[str]) -> str:  # noqa: ARG002 - no se esperan argumentos
        return self._help_overview()

    def _format_help(self, title: str, body: str) -> str:
        return f"{title}\n\n{body}"

    def _help_overview(self) -> str:
        return _(
            "ui.commands.overview",
            connect_usage=self._connect_usage(),
            disconnect_usage=self._disconnect_usage(),
            help_usage=self._help_usage(),
            exit_command=PRIMARY_EXIT,
        )

    def _connect_help(self) -> str:
        return _(
            "ui.commands.connect.help",
            command=PRIMARY_CONNECT,
            password_example=f"{PRIMARY_CONNECT} server.local admin s3cr3t",
            key_example=f"{PRIMARY_CONNECT} server.local admin ~/.ssh/id_ed25519",
            disconnect=PRIMARY_DISCONNECT,
        )

    def _disconnect_help(self) -> str:
        return _(
            "ui.commands.disconnect.help",
            command=PRIMARY_DISCONNECT,
        )

    def _connect_usage(self) -> str:
        return _(
            "ui.commands.connect.usage",
            command=PRIMARY_CONNECT,
        )

    def _disconnect_usage(self) -> str:
        return PRIMARY_DISCONNECT

    def _help_usage(self) -> str:
        return PRIMARY_HELP

    def _auth_label(self, method: str) -> str:
        key = f"connection.auth.method.{method}"
        try:
            return _(key)
        except KeyError:
            return method
