"""Aplicación TUI principal."""

from __future__ import annotations

import asyncio
import logging
import os

from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical

from ..agent import AgentRuntime
from ..config import CONFIG, AppConfig
from ..connection import (
    ConnectionError,
    NoActiveConnection,
    SSHConnectionManager,
)
from .commands import SlashCommandProcessor
from .dialogs import ExitConfirmationModal
from .panels import CommandInput, ConnectionInfo, ConversationPanel


class SmartAISysAdminApp(App[None]):
    """Aplicación principal basada en Textual."""

    BINDINGS: list[tuple[str, str, str]] = []

    def __init__(self, config: AppConfig = CONFIG) -> None:
        super().__init__()
        self._config = config
        self._conversation: ConversationPanel | None = None
        self._input: CommandInput | None = None
        self._connection_info: ConnectionInfo | None = None
        self._exit_dialog_config = self._config.ui.dialogs.exit
        # Usamos un nombre distinto para no interferir con `App._logger`,
        # que Textual emplea para su propio sistema de logging.
        self._app_logger = logging.getLogger("smart_ai_sys_admin.ui.app")
        self._connection_manager = SSHConnectionManager(
            logging.getLogger("smart_ai_sys_admin.connection")
        )
        self._command_processor = SlashCommandProcessor(
            self._connection_manager,
            self._config.ui.output_panel,
            logging.getLogger("smart_ai_sys_admin.ui.commands"),
        )
        self._agent_runtime = AgentRuntime(
            self._connection_manager,
            logging.getLogger("smart_ai_sys_admin.agent.runtime"),
        )

    def compose(self) -> ComposeResult:
        input_section = Vertical(
            CommandInput(
                self._config.ui.input_widget,
                self._config.shortcuts.exit,
                self._config.ui.history_limit,
            ),
            ConnectionInfo(self._config.ui.connection_panel),
            id="input-section",
        )
        yield Grid(
            ConversationPanel(self._config),
            input_section,
            id="main-layout",
        )

    def on_mount(self) -> None:
        self.styles.background = self._config.ui.output_panel.background or "black"
        layout = self.query_one("#main-layout", Grid)
        layout.styles.grid_rows = "1fr auto"
        layout.styles.grid_columns = "1fr"
        layout.styles.height = "100%"
        layout.styles.width = "100%"
        layout.styles.row_gap = 1
        self._conversation = self.query_one(ConversationPanel)
        self._input = self.query_one(CommandInput)
        self._connection_info = self.query_one(ConnectionInfo)
        input_section = self.query_one("#input-section", Vertical)
        input_section.styles.height = "auto"
        input_section.styles.width = "100%"
        input_section.styles.gap = 1
        exit_shortcut = self._config.shortcuts.exit
        self.bind(exit_shortcut.binding, "quit", description=exit_shortcut.description)
        self._warn_if_term_incompatible()
        self._update_connection_info()
        self._initialize_agent_runtime()

    async def on_command_input_submitted(self, message: CommandInput.Submitted) -> None:
        message.stop()
        assert self._conversation is not None
        assert self._input is not None
        self._conversation.add_user_message(message.content)
        trimmed = message.content.strip()
        if not trimmed:
            self._conversation.add_agent_markdown("⚠️ Debes introducir una instrucción o comando.")
            self._input.focus_editor()
            return
        tokens = trimmed.split()
        if tokens and tokens[0].lower() == "/salir":
            if len(tokens) > 1:
                self._conversation.add_agent_markdown(
                    "⚠️ `/salir` no admite argumentos adicionales."
                )
                self._input.focus_editor()
                return
            self._handle_exit_request()
            return
        try:
            response = self._command_processor.process(message.content)
        except Exception as exc:  # pragma: no cover - protección ante errores inesperados.
            self._app_logger.exception("Error procesando la entrada del usuario")
            response = f"❌ Se produjo un error inesperado: {exc}"
        if response is not None:
            if response:
                self._conversation.add_agent_markdown(response)
            self._update_connection_info()
            self._input.focus_editor()
            return

        agent_output = await asyncio.to_thread(self._invoke_agent, trimmed)
        if not agent_output:
            agent_output = self._config.ui.output_panel.placeholder_response_markdown
        self._conversation.add_agent_markdown(agent_output)
        self._update_connection_info()
        self._input.focus_editor()

    def _handle_exit_request(self) -> None:
        assert self._conversation is not None
        self._conversation.add_agent_markdown(self._exit_dialog_config.prompt_markdown)
        self._show_exit_confirmation()

    def _warn_if_term_incompatible(self) -> None:
        assert self._conversation is not None
        term = os.environ.get("TERM", "")
        detected = term or self._config.terminal.unknown_label
        if term not in self._config.terminal.allowed_terms:
            warning_md = (
                f"{self._config.terminal.warning_icon} {self._config.terminal.warning_message}\n\n"
                f"{self._config.terminal.detected_label}: `{detected}`"
            )
            self._conversation.add_agent_markdown(warning_md)

    def _update_connection_info(self) -> None:
        if not self._connection_info:
            return
        self._connection_info.refresh_status(self._connection_manager.status_summary())

    def _show_exit_confirmation(self) -> None:
        modal = ExitConfirmationModal(self._exit_dialog_config)
        self.push_screen(modal, self._on_exit_confirmed)

    def _on_exit_confirmed(self, confirmed: bool | None) -> None:
        if confirmed:
            self._close_connection_safely()
            self._shutdown_agent()
            self.exit()
        elif self._input:
            self._input.focus_editor()

    def action_quit(self) -> None:
        """Intercepta la acción estándar de salida para cerrar la conexión activa."""
        self._close_connection_safely()
        self._shutdown_agent()
        super().action_quit()

    def _close_connection_safely(self) -> None:
        try:
            self._connection_manager.disconnect()
        except NoActiveConnection:
            self._update_connection_info()
            return
        except ConnectionError as exc:
            self._app_logger.warning(
                "Error cerrando la conexión al salir: %s",
                exc,
            )
        finally:
            self._update_connection_info()

    def _initialize_agent_runtime(self) -> None:
        assert self._conversation is not None
        self._agent_runtime.initialize()
        if self._agent_runtime.status_message:
            self._conversation.add_agent_markdown(self._agent_runtime.status_message)
        if self._agent_runtime.error_message:
            self._conversation.add_agent_markdown(self._agent_runtime.error_message)

    def _invoke_agent(self, prompt: str) -> str:
        if not self._agent_runtime.ready:
            return (
                self._agent_runtime.error_message
                or "⚠️ El agente IA no está disponible. Revisa la configuración."
            )
        return self._agent_runtime.invoke(prompt)

    def _shutdown_agent(self) -> None:
        self._agent_runtime.shutdown()


def run_app(config: AppConfig = CONFIG) -> None:
    """Ejecuta la aplicación TUI con la configuración suministrada."""
    SmartAISysAdminApp(config=config).run()


__all__ = ["SmartAISysAdminApp", "run_app"]
