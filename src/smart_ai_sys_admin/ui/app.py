"""Aplicación TUI principal."""

from __future__ import annotations

import logging
import os

from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical

from ..config import CONFIG, AppConfig
from ..connection import SSHConnectionManager
from .commands import SlashCommandProcessor
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

    def compose(self) -> ComposeResult:
        input_section = Vertical(
            CommandInput(self._config.ui.input_widget),
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

    def on_command_input_submitted(self, message: CommandInput.Submitted) -> None:
        message.stop()
        assert self._conversation is not None
        assert self._input is not None
        self._conversation.add_user_message(message.content)
        try:
            response = self._command_processor.process(message.content)
        except Exception as exc:  # pragma: no cover - protección ante errores inesperados.
            self._app_logger.exception("Error procesando la entrada del usuario")
            response = f"❌ Se produjo un error inesperado: {exc}"
        if not response:
            response = self._config.ui.output_panel.placeholder_response_markdown
        if message.content.strip().startswith("/"):
            self._update_connection_info()
        self._conversation.add_agent_markdown(response)
        self._input.focus_editor()

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


def run_app(config: AppConfig = CONFIG) -> None:
    """Ejecuta la aplicación TUI con la configuración suministrada."""
    SmartAISysAdminApp(config=config).run()


__all__ = ["SmartAISysAdminApp", "run_app"]
