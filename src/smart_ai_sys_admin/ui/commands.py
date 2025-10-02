"""Procesador de comandos slash para la interfaz TUI."""

from __future__ import annotations

import logging
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import OutputPanelConfig
from ..connection import (
    ConnectionAlreadyOpen,
    ConnectionError,
    NoActiveConnection,
    SSHConnectionManager,
)
from ..localization import _
from ..plugins.types import PluginSlashCommand

if TYPE_CHECKING:  # pragma: no cover
    from ..agent.runtime import AgentRuntime

PRIMARY_CONNECT = "/connect"
PRIMARY_DISCONNECT = "/disconnect"
PRIMARY_HELP = "/help"
PRIMARY_EXIT = "/exit"
PRIMARY_STATUS = "/status"

CONNECT_ALIASES = frozenset({PRIMARY_CONNECT, "/conectar", "/verbinden"})
DISCONNECT_ALIASES = frozenset({PRIMARY_DISCONNECT, "/desconectar", "/trennen"})
HELP_ALIASES = frozenset({PRIMARY_HELP, "/ayuda", "/hilfe"})
EXIT_ALIASES = frozenset({PRIMARY_EXIT, "/salir", "/quit", "/beenden"})
STATUS_ALIASES = frozenset({PRIMARY_STATUS, "/estado"})


class SlashCommandProcessor:
    """Encapsula la lógica de comandos personalizados del agente."""

    def __init__(
        self,
        connection_manager: SSHConnectionManager,
        agent_runtime: AgentRuntime,
        output_config: OutputPanelConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._agent_runtime = agent_runtime
        self._output_config = output_config
        self._logger = logger or logging.getLogger("smart_ai_sys_admin.ui.commands")
        self._plugin_commands: list[PluginSlashCommand] = []
        self._plugin_alias_index: dict[str, PluginSlashCommand] = {}
        self._reserved_aliases = set(
            alias.lower()
            for group in [
                CONNECT_ALIASES,
                DISCONNECT_ALIASES,
                HELP_ALIASES,
                EXIT_ALIASES,
                STATUS_ALIASES,
            ]
            for alias in group
        )

    def process(self, content: str) -> str | None:
        content = content.strip()
        if not content:
            return ""
        if not content.startswith("/"):
            return None
        return self._execute_command(content)

    def register_plugin_commands(self, commands: list[PluginSlashCommand]) -> None:
        for command in commands:
            aliases = {alias.lower() for alias in command.iter_aliases()}
            if any(alias in self._reserved_aliases for alias in aliases):
                self._logger.warning(
                    "Se ignoró el comando del plugin '%s' por conflicto de alias",
                    command.name,
                )
                continue
            if any(alias in self._plugin_alias_index for alias in aliases):
                self._logger.warning(
                    "Se ignoró el comando del plugin '%s' por alias duplicado",
                    command.name,
                )
                continue
            self._plugin_commands.append(command)
            for alias in aliases:
                self._plugin_alias_index[alias] = command
            self._reserved_aliases.update(aliases)

    def suggestion_for(self, raw_value: str) -> str | None:
        trimmed = raw_value.strip()
        if not trimmed:
            return None
        tokens = trimmed.split()
        if not tokens:
            return None
        command_raw = tokens[0]
        command = command_raw.lower()
        if command in CONNECT_ALIASES:
            return self._suggest_connect(command_raw, tokens)
        if command in DISCONNECT_ALIASES:
            return self._suggest_disconnect(command_raw, tokens)
        if command in HELP_ALIASES:
            return self._suggest_help(command_raw, tokens)
        if command in EXIT_ALIASES:
            return self._suggest_exit(command_raw, tokens)
        if command in STATUS_ALIASES:
            return self._suggest_status(command_raw, tokens)
        plugin = self._plugin_alias_index.get(command)
        if plugin is None:
            return None
        args = tokens[1:]
        if plugin.suggestion:
            try:
                return plugin.suggestion(command_raw, args)
            except Exception:  # pragma: no cover - depende del plugin
                self._logger.exception(
                    "Error en la sugerencia del comando plugin '%s'", plugin.name
                )
                return None
        if plugin.usage_key:
            return _(plugin.usage_key, command=command_raw)
        return None

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
        elif command in STATUS_ALIASES:
            handler = self._command_status
        else:
            plugin = self._plugin_alias_index.get(command)
            if plugin:
                return self._execute_plugin_command(plugin, parts[1:], command)
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

    def _execute_plugin_command(
        self, command: PluginSlashCommand, args: list[str], alias: str
    ) -> str:
        self._logger.info(
            "Procesando comando de plugin %s con argumentos %s", command.name, args
        )
        try:
            return command.handler(args)
        except Exception as exc:  # pragma: no cover - depende del plugin
            self._logger.exception(
                "Error interno procesando el comando plugin '%s'", command.name
            )
            return _(
                "ui.commands.internal_error",
                command=alias,
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
        extra_args = args[3:]
        port = 22
        if extra_args:
            if len(extra_args) > 1:
                self._logger.info(
                    "Argumentos extra ignorados en %s: %s",
                    PRIMARY_CONNECT,
                    extra_args,
                )
                return self._format_help(
                    _("ui.commands.connect.too_many_args", command=PRIMARY_CONNECT),
                    self._connect_help(),
                )
            port_str = extra_args[0]
            try:
                port = int(port_str)
            except ValueError:
                self._logger.info(
                    "Puerto inválido para %s: %s",
                    PRIMARY_CONNECT,
                    port_str,
                )
                return self._format_help(
                    _("connection.errors.invalid_port", port=port_str),
                    self._connect_help(),
                )
            if port <= 0 or port > 65535:
                self._logger.info(
                    "Puerto fuera de rango para %s: %s",
                    PRIMARY_CONNECT,
                    port,
                )
                return self._format_help(
                    _("connection.errors.invalid_port", port=port),
                    self._connect_help(),
                )
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
                port=port,
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
            "Conexión abierta con %s@%s:%s usando %s",
            details.username,
            details.host,
            details.port,
            details.auth_method,
        )
        auth_label = self._auth_label(details.auth_method)
        return _(
            "ui.commands.connect.success",
            username=details.username,
            host=details.host,
            port=details.port,
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
        if not args:
            return self._help_overview()
        target = args[0].lower()
        if target in CONNECT_ALIASES:
            return self._connect_help()
        if target in DISCONNECT_ALIASES:
            return self._disconnect_help()
        if target in HELP_ALIASES:
            return self._help_usage()
        if target in EXIT_ALIASES:
            return self._exit_help()
        plugin = self._plugin_alias_index.get(target)
        if plugin:
            if plugin.help_key:
                return _(plugin.help_key, command=plugin.name)
            description = _(
                plugin.description_key, command=plugin.name
            ) if plugin.description_key else plugin.name
            usage = _(plugin.usage_key, command=plugin.name) if plugin.usage_key else plugin.name
            return f"{description}\n\n{usage}"
        return self._format_help(
            _("ui.commands.help.unknown", command=target),
            self._help_overview(),
        )

    def _format_help(self, title: str, body: str) -> str:
        return f"{title}\n\n{body}"

    def _help_overview(self) -> str:
        base = _(
            "ui.commands.overview",
            connect_usage=self._connect_usage(),
            disconnect_usage=self._disconnect_usage(),
            help_usage=self._help_usage(),
            status_usage=self._status_usage(),
            exit_command=PRIMARY_EXIT,
        )
        if not self._plugin_commands:
            return base
        lines = [base, "", _("ui.commands.plugins.header")]
        for command in sorted(self._plugin_commands, key=lambda c: c.name.lower()):
            description = _(
                command.description_key, command=command.name
            ) if command.description_key else command.name
            lines.append(f"- `{command.name}` {description}")
        return "\n".join(lines)

    def _suggest_connect(self, command_raw: str, tokens: list[str]) -> str | None:
        usage = self._connect_usage()
        if len(tokens) <= 1:
            return _(
                "ui.input.suggestions.connect.full_usage",
                command=command_raw,
                usage=usage,
            )
        if len(tokens) == 2:
            host = tokens[1]
            return _(
                "ui.input.suggestions.connect.missing_user",
                command=command_raw,
                host=host,
                usage=usage,
            )
        if len(tokens) == 3:
            host, user = tokens[1], tokens[2]
            return _(
                "ui.input.suggestions.connect.missing_secret",
                command=command_raw,
                host=host,
                user=user,
                usage=usage,
            )
        return _(
            "ui.input.suggestions.connect.port_hint",
            command=command_raw,
            usage=usage,
        ) if len(tokens) == 4 else None

    def _suggest_disconnect(self, command_raw: str, tokens: list[str]) -> str | None:
        if len(tokens) > 1:
            return _(
                "ui.input.suggestions.disconnect.no_args",
                command=command_raw,
            )
        return _(
            "ui.input.suggestions.disconnect.description",
            command=command_raw,
        )

    def _suggest_help(self, command_raw: str, tokens: list[str]) -> str | None:
        if len(tokens) > 1:
            return _(
                "ui.input.suggestions.help.no_args",
                command=command_raw,
            )
        return _(
            "ui.input.suggestions.help.description",
            command=command_raw,
            primary=PRIMARY_HELP,
        )

    def _suggest_exit(self, command_raw: str, tokens: list[str]) -> str | None:
        if len(tokens) > 1:
            return _(
                "ui.input.suggestions.exit.no_args",
                command=command_raw,
            )
        return _(
            "ui.input.suggestions.exit.description",
            command=command_raw,
            primary=PRIMARY_EXIT,
        )

    def _suggest_status(self, command_raw: str, tokens: list[str]) -> str | None:
        if len(tokens) > 1:
            return _(
                "ui.input.suggestions.status.no_args",
                command=command_raw,
            )
        return _(
            "ui.input.suggestions.status.description",
            command=command_raw,
        )

    def _connect_help(self) -> str:
        return _(
            "ui.commands.connect.help",
            command=PRIMARY_CONNECT,
            password_example=f"{PRIMARY_CONNECT} server.local admin s3cr3t",
            key_example=f"{PRIMARY_CONNECT} server.local admin ~/.ssh/id_ed25519",
            port_example=f"{PRIMARY_CONNECT} server.local admin s3cr3t 2222",
            default_port=22,
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

    def _status_usage(self) -> str:
        return PRIMARY_STATUS

    def _exit_help(self) -> str:
        return _(
            "ui.input.suggestions.exit.description",
            command=PRIMARY_EXIT,
            primary=PRIMARY_EXIT,
        )

    def _auth_label(self, method: str) -> str:
        key = f"connection.auth.method.{method}"
        try:
            return _(key)
        except KeyError:
            return method

    def _command_status(self, args: list[str]) -> str:
        if args:
            return self._format_help(
                _("ui.commands.status.no_args", command=PRIMARY_STATUS),
                self._status_help(),
            )
        lines: list[str] = [_("ui.commands.status.header")]
        connection_summary = self._connection_manager.status_summary()
        lines.append(
            f"- {_('ui.commands.status.connection')}: {connection_summary}"
        )
        if self._agent_runtime:
            summary = self._agent_runtime.agent_summary()
            yes_label = _("common.yes")
            no_label = _("common.no")
            ready_value = yes_label if summary.get("ready") else no_label
            streaming_value = (
                yes_label if summary.get("streaming") else no_label
            )
            if summary.get("provider"):
                lines.append(
                    f"- {_('ui.commands.status.provider')}: {summary['provider']}"
                )
            if summary.get("model"):
                lines.append(
                    f"- {_('ui.commands.status.model')}: {summary['model']}"
                )
            lines.append(
                f"- {_('ui.commands.status.agent_ready')}: {ready_value}"
            )
            lines.append(
                f"- {_('ui.commands.status.streaming')}: {streaming_value}"
            )
            if summary.get("config_path"):
                lines.append(
                    f"- {_('ui.commands.status.config_path')}: `{summary['config_path']}`"
                )
            if summary.get("status"):
                lines.append(f"- {summary['status']}")
            if summary.get("error"):
                lines.append(
                    f"- {_('ui.commands.status.error')}: {summary['error']}"
                )
        return "\n".join(lines)

    def _status_help(self) -> str:
        return _(
            "ui.commands.status.help",
            command=PRIMARY_STATUS,
        )
