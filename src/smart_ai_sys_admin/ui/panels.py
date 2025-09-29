"""Widgets principales de la interfaz TUI."""

from __future__ import annotations

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import RichLog, Static, TextArea

from ..config import AppConfig, InputConfig, PanelConfig


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
        self._register_panel(self._build_agent_panel(self._ui.output_panel.initial_markdown))

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
            width = self._log.size.width or None
            self._log.write(entry, width=width, expand=True, shrink=False)
        self._log.scroll_end(animate=False)


class CommandInput(Static):
    """Área de entrada multi-línea configurada para el usuario."""

    class Submitted(Message):
        """Evento emitido cuando se envía el formulario."""

        def __init__(self, sender: CommandInput, content: str) -> None:
            super().__init__()
            self.set_sender(sender)
            self.content = content

    value = reactive("")

    def __init__(self, config: InputConfig) -> None:
        super().__init__(id="command-input")
        self._config = config
        self._editor: TextArea | None = None
        self._placeholder: Static | None = None
        self._base_placeholder = config.placeholder

    def compose(self) -> ComposeResult:
        self._placeholder = Static(self._config.placeholder, classes="input-placeholder")
        self._placeholder.styles.color = self._config.text_style
        yield self._placeholder
        self._editor = TextArea(text="", id="editor", soft_wrap=True)
        yield self._editor

    def on_mount(self) -> None:
        assert self._editor is not None
        self.styles.width = "100%"
        self.styles.height = "auto"
        self.styles.margin_top = "auto"
        self.styles.padding = self._parse_padding(self._config.padding)
        self._editor.styles.width = "100%"
        self._editor.styles.background = self._config.background
        self._editor.styles.color = self._config.text_style
        self._editor.styles.min_height = self._config.min_lines
        self._editor.styles.max_height = self._config.max_lines
        self._editor.border_subtitle = self._config.submit_binding
        self._editor.cursor_blink = True
        self._editor.focus()
        self._update_placeholder_hint()

    def _parse_padding(self, raw_padding: str) -> tuple[int, ...]:
        values = tuple(int(value) for value in raw_padding.split())
        return values or (0,)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:  # type: ignore[override]
        self.value = event.text_area.text
        self._update_placeholder_hint()

    def on_key(self, event: events.Key) -> None:
        if self._matches_submit_binding(event):
            event.stop()
            self._submit_value()

    def _matches_submit_binding(self, event: events.Key) -> bool:
        binding = self._config.submit_binding.strip().lower()
        if not binding:
            return False
        key = event.key.lower()
        if key == binding:
            return True
        for alias in getattr(event, "aliases", []):
            if alias.lower() == binding:
                return True
        name = getattr(event, "name", "").lower()
        if name and name == binding.replace("+", "_"):
            return True
        return False

    def _update_placeholder_hint(self) -> None:
        if not self._placeholder:
            return
        suggestion = self._suggestion_for(self.value)
        text = Text(self._base_placeholder, style=self._config.text_style)
        if suggestion:
            text.append("\n\n", style=self._config.text_style)
            text.append("Sugerencia: ", style=f"{self._config.text_style} dim")
            text.append(suggestion, style=self._config.text_style)
        self._placeholder.update(text)

    def _suggestion_for(self, raw_value: str) -> str | None:
        trimmed = raw_value.strip()
        if not trimmed:
            return None
        tokens = trimmed.split()
        command = tokens[0]
        if command == "/connect":
            if len(tokens) <= 1:
                return "/connect <host> <usuario> <password|ruta_clave>"
            if len(tokens) == 2:
                host = tokens[1]
                return f"Completa el usuario: `/connect {host} <usuario> <password|ruta_clave>`"
            if len(tokens) == 3:
                host, usuario = tokens[1], tokens[2]
                return (
                    "Añade la contraseña o ruta de clave: "
                    f"`/connect {host} {usuario} <password|ruta_clave>`"
                )
            return None
        if command == "/disconnect":
            if len(tokens) > 1:
                return "`/disconnect` no acepta argumentos adicionales"
            return "Cierra la sesión remota actual"
        return None

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


class ConnectionInfo(Static):
    """Muestra el estado de la conexión activa."""

    def __init__(self, panel_config: PanelConfig) -> None:
        super().__init__(id="connection-info")
        self._panel_config = panel_config

    def on_mount(self) -> None:
        self.styles.width = "100%"
        self.styles.height = "auto"
        self.styles.padding = (0, 1)
        self.refresh_status("Sin conexión activa")

    def refresh_status(self, message: str) -> None:
        body = Text(message, style=self._panel_config.text_style)
        panel = Panel(
            body,
            title=self._panel_config.title,
            border_style=self._panel_config.border_style,
            expand=True,
        )
        if self._panel_config.background:
            panel.style = self._panel_config.background
        self.update(panel)
