"""Procesador de comandos slash para la interfaz TUI."""

from __future__ import annotations

import logging
import shlex
import textwrap
from pathlib import Path

from ..config import OutputPanelConfig
from ..connection import (
    ConnectionAlreadyOpen,
    ConnectionError,
    NoActiveConnection,
    SSHConnectionManager,
)


class SlashCommandProcessor:
    """Encapsula la lógica de comandos personalizados del agente."""

    CONNECT_COMMAND = "/conectar"
    DISCONNECT_COMMAND = "/desconectar"
    HELP_COMMAND = "/ayuda"

    CONNECT_HELP = textwrap.dedent(
        """
        **Uso `/conectar`**
        - Argumentos: `<host> <usuario> <password|ruta_clave>`
        - Ejemplo con contraseña: `/conectar server.local admin s3cr3t`
        - Ejemplo con clave: `/conectar server.local admin ~/.ssh/id_ed25519`
        """
    ).strip()

    DISCONNECT_HELP = textwrap.dedent(
        """
        **Uso `/desconectar`**
        - Cierra la sesión SSH/SFTP activa.
        - No acepta argumentos adicionales.
        """
    ).strip()

    COMMAND_OVERVIEW = textwrap.dedent(
        """
        **Comandos disponibles**
        - `/conectar <host> <usuario> <password|ruta_clave>` abre la sesión remota.
        - `/desconectar` cierra la sesión activa.
        - `/ayuda` resume todos los comandos disponibles.
        - `/salir` solicita confirmación para cerrar la aplicación.
        """
    ).strip()

    def __init__(
        self,
        connection_manager: SSHConnectionManager,
        output_config: OutputPanelConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._output_config = output_config
        self._logger = logger or logging.getLogger("smart_ai_sys_admin.ui.commands")

    def process(self, content: str) -> str:
        content = content.strip()
        if not content:
            return ""
        if not content.startswith("/"):
            return self._output_config.placeholder_response_markdown
        return self._execute_command(content)

    def _execute_command(self, raw_command: str) -> str:
        try:
            parts = shlex.split(raw_command)
        except ValueError as exc:
            self._logger.warning("Comando inválido: %s", exc)
            return self._format_help(
                f"⚠️ No se pudo interpretar el comando: {exc}",
                self.COMMAND_OVERVIEW,
            )
        if not parts:
            return self._output_config.placeholder_response_markdown
        command = parts[0].lower()
        handlers = {
            self.CONNECT_COMMAND: self._command_connect,
            self.DISCONNECT_COMMAND: self._command_disconnect,
            self.HELP_COMMAND: self._command_help,
            "/connect": self._command_connect,
            "/disconnect": self._command_disconnect,
        }
        handler = handlers.get(command)
        if not handler:
            return self._format_help(
                f"⚠️ Comando desconocido `{command}`.",
                self.COMMAND_OVERVIEW,
            )
        self._logger.info("Procesando comando %s con argumentos %s", command, parts[1:])
        try:
            return handler(parts[1:])
        except Exception as exc:  # pragma: no cover - salvaguarda adicional
            self._logger.exception("Error interno procesando %s", command)
            return f"❌ Se produjo un error inesperado al ejecutar `{command}`: {exc}"

    def _command_connect(self, args: list[str]) -> str:
        if len(args) < 3:
            self._logger.info("Parámetros insuficientes para /conectar: %s", args)
            return self._format_help(
                "⚠️ Faltan argumentos para `/conectar`.",
                self.CONNECT_HELP,
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
            return self._format_help(str(exc), self.DISCONNECT_HELP)
        except ConnectionError as exc:
            self._logger.warning("Fallo en /conectar: %s", exc)
            return self._format_help(
                f"❌ No se pudo establecer la conexión: {exc}",
                self.CONNECT_HELP,
            )
        self._logger.info(
            "Conexión abierta con %s@%s usando %s",
            details.username,
            details.host,
            details.auth_method,
        )
        auth_label = "clave" if details.auth_method == "key" else "contraseña"
        return f"✅ Conexión abierta con `{details.username}@{details.host}` usando {auth_label}."

    def _command_disconnect(
        self, args: list[str]
    ) -> str:  # noqa: ARG002 - placeholder para futuros argumentos
        if args:
            self._logger.info("Se ignorarán argumentos extra en /desconectar: %s", args)
            return self._format_help(
                "⚠️ `/desconectar` no admite argumentos.",
                self.DISCONNECT_HELP,
            )
        try:
            self._connection_manager.disconnect()
        except NoActiveConnection:
            self._logger.info("Solicitud de /desconectar sin sesión activa")
            return self._format_help(
                "⚠️ No hay una conexión activa que cerrar.",
                self.DISCONNECT_HELP,
            )
        except ConnectionError as exc:
            self._logger.error("Fallo cerrando la conexión: %s", exc)
            return self._format_help(
                f"❌ No se pudo cerrar la conexión: {exc}",
                self.DISCONNECT_HELP,
            )
        self._logger.info("Conexión cerrada correctamente")
        return "✅ Conexión cerrada."

    def _command_help(self, args: list[str]) -> str:  # noqa: ARG002 - no se esperan argumentos
        return self.COMMAND_OVERVIEW

    def _format_help(self, title: str, body: str) -> str:
        return f"{title}\n\n{body}"
