"""Componentes de la interfaz TUI para Smart-AI-Sys-Admin."""

from __future__ import annotations

import os

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import RichLog, Static, TextArea

from .config import CONFIG, AppConfig, InputConfig, PanelConfig


class ConversationPanel(Static):
    """Panel encargado de renderizar la conversación en formato Markdown."""

    def __init__(self, app_config: AppConfig) -> None:
        super().__init__(id="conversation-panel")
        self._ui = app_config.ui
        self._history: list[Panel] = []
        self._log: RichLog | None = None

    def compose(self) -> ComposeResult:
        self._log = RichLog(auto_scroll=True, markup=True, wrap=True, id="conversation-log")
        self._log.border_title = self._ui.output_panel.title
        self._log.border_style = self._ui.output_panel.border_style
        yield self._log

    def on_mount(self) -> None:
        assert self._log is not None
        self.styles.height = "1fr"
        self.styles.width = "100%"
        if self._ui.output_panel.background:
            self._log.styles.background = self._ui.output_panel.background
        self._register_panel(
            self._build_agent_panel(self._ui.output_panel.initial_markdown)
        )

    def add_user_message(self, content: str) -> None:
        panel = self._build_panel(
            label_config=self._ui.user_panel,
            body=Text(content, style=self._ui.user_panel.text_style),
        )
        self._register_panel(panel)

    def add_agent_markdown(self, markdown_text: str) -> None:
        panel = self._build_agent_panel(markdown_text)
        self._register_panel(panel)

    def _build_panel(self, label_config: PanelConfig, body: Text | Markdown) -> Panel:
        panel = Panel(
            body,
            title=label_config.title,
            border_style=label_config.border_style,
            expand=True,
        )
        if label_config.background:
            panel.style = label_config.background
        return panel

    def _build_agent_panel(self, markdown_text: str) -> Panel:
        markdown = Markdown(markdown_text, style=self._ui.output_panel.text_style)
        return self._build_panel(self._ui.output_panel, markdown)

    def _register_panel(self, panel: Panel) -> None:
        self._history.append(panel)
        if len(self._history) > self._ui.history_limit:
            self._history = self._history[-self._ui.history_limit :]
        self._refresh_log()

    def _refresh_log(self) -> None:
        assert self._log is not None
        self._log.clear()
        for entry in self._history:
            self._log.write(entry)
        self._log.scroll_end(animate=False)


class CommandInput(Static):
    """Área de entrada multi-línea configurada para el usuario."""

    class Submitted(Message):
        """Evento emitido cuando se envía el formulario."""

        def __init__(self, sender: CommandInput, content: str) -> None:
            super().__init__(sender)
            self.content = content

    value = reactive("")

    def __init__(self, config: InputConfig) -> None:
        super().__init__(id="command-input")
        self._config = config
        self._editor: TextArea | None = None

    def compose(self) -> ComposeResult:
        placeholder = Static(self._config.placeholder, classes="input-placeholder")
        placeholder.styles.color = self._config.text_style
        yield placeholder
        self._editor = TextArea(text="", id="editor", soft_wrap=True)
        yield self._editor

    def on_mount(self) -> None:
        assert self._editor is not None
        self.styles.width = "100%"
        self.styles.padding = self._parse_padding(self._config.padding)
        self._editor.styles.width = "100%"
        self._editor.styles.background = self._config.background
        self._editor.styles.color = self._config.text_style
        self._editor.styles.min_height = self._config.min_lines
        self._editor.styles.max_height = self._config.max_lines
        self._editor.border_subtitle = self._config.submit_binding
        self._editor.cursor_blink = True
        self._editor.focus()

    def _parse_padding(self, raw_padding: str) -> tuple[int, ...]:
        values = tuple(int(value) for value in raw_padding.split())
        return values or (0,)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:  # type: ignore[override]
        self.value = event.text_area.text

    def on_key(self, event: events.Key) -> None:
        if event.key == self._config.submit_binding:
            event.stop()
            self._submit_value()

    def _submit_value(self) -> None:
        if not self._editor:
            return
        content = self._editor.text.strip()
        if not content:
            return
        self.post_message(self.Submitted(self, content))
        self._editor.load_text("")

    def focus_editor(self) -> None:
        if self._editor:
            self._editor.focus()


class SmartAISysAdminApp(App[None]):
    """Aplicación principal basada en Textual."""

    BINDINGS: list[tuple[str, str, str]] = []

    def __init__(self, config: AppConfig = CONFIG) -> None:
        super().__init__()
        self._config = config
        self._conversation: ConversationPanel | None = None
        self._input: CommandInput | None = None

    def compose(self) -> ComposeResult:
        yield Vertical(
            ConversationPanel(self._config),
            CommandInput(self._config.ui.input_widget),
            id="main-layout",
        )

    def on_mount(self) -> None:
        self.styles.background = self._config.ui.output_panel.background or "black"
        self._conversation = self.query_one(ConversationPanel)
        self._input = self.query_one(CommandInput)
        exit_shortcut = self._config.shortcuts.exit
        self.bind(exit_shortcut.binding, "quit", description=exit_shortcut.description)
        self._warn_if_term_incompatible()

    def on_command_input_submitted(self, message: CommandInput.Submitted) -> None:
        message.stop()
        assert self._conversation is not None
        assert self._input is not None
        self._conversation.add_user_message(message.content)
        self._conversation.add_agent_markdown(
            self._config.ui.output_panel.placeholder_response_markdown
        )
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


def run_app(config: AppConfig = CONFIG) -> None:
    """Ejecuta la aplicación TUI con la configuración suministrada."""
    SmartAISysAdminApp(config=config).run()
