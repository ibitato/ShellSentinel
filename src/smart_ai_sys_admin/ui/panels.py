"""Widgets principales de la interfaz TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.containers import Horizontal
from textual.widgets import RichLog, Static, TextArea

if TYPE_CHECKING:  # pragma: no cover - solo para anotaciones estáticas.
    from ..config import ShortcutConfig

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

    def on_resize(self, event: events.Resize) -> None:  # type: ignore[override]
        if self._log is not None:
            self._refresh_log()

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


class _HistoryAwareTextArea(TextArea):
    """TextArea que delega algunas teclas al contenedor para lógica personalizada."""

    def __init__(self, owner: CommandInput) -> None:
        super().__init__(text="", id="editor", soft_wrap=True)
        self._owner = owner

    def on_key(self, event: events.Key) -> None:  # type: ignore[override]
        if self._owner._handle_editor_key(event):
            return
        super().on_event(event)


class CommandInput(Static):
    """Área de entrada multi-línea configurada para el usuario."""

    class Submitted(Message):
        """Evento emitido cuando se envía el formulario."""

        def __init__(self, sender: CommandInput, content: str) -> None:
            super().__init__()
            self.set_sender(sender)
            self.content = content

    value = reactive("")

    def __init__(
        self,
        config: InputConfig,
        exit_shortcut: ShortcutConfig,
        history_limit: int,
    ) -> None:
        super().__init__(id="command-input")
        self._config = config
        self._exit_shortcut = exit_shortcut
        self._history_limit = max(history_limit, 1)
        self._editor: _HistoryAwareTextArea | None = None
        self._placeholder: Static | None = None
        self._base_placeholder = self._format_placeholder()
        self._history: list[str] = []
        self._history_index: int | None = None
        self._navigating_history = False

    def compose(self) -> ComposeResult:
        self._placeholder = Static(self._config.placeholder, classes="input-placeholder")
        self._placeholder.styles.color = self._config.text_style
        yield self._placeholder
        self._editor = _HistoryAwareTextArea(self)
        yield self._editor

    def on_mount(self) -> None:
        assert self._editor is not None
        self.styles.width = "100%"
        self.styles.height = "auto"
        self.styles.margin_top = 0
        self.styles.padding = self._parse_padding(self._config.padding)
        self._editor.styles.width = "100%"
        self._editor.styles.background = self._config.background
        self._editor.styles.color = self._config.text_style
        self._editor.styles.min_height = self._config.min_lines
        self._editor.styles.max_height = self._config.max_lines
        subtitle = self._build_border_subtitle()
        self._editor.border_subtitle = subtitle
        self._editor.cursor_blink = True
        self._editor.focus()
        self._update_placeholder_hint()

    def _parse_padding(self, raw_padding: str) -> tuple[int, ...]:
        values = tuple(int(value) for value in raw_padding.split())
        return values or (0,)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:  # type: ignore[override]
        self.value = event.text_area.text
        if not self._navigating_history:
            self._history_index = None
        self._update_placeholder_hint()

    def _handle_editor_key(self, event: events.Key) -> bool:
        if self._matches_submit_binding(event):
            event.stop()
            self._submit_value()
            return True
        key_label = event.key.lower()
        if key_label in {"shift+up", "shift+down"}:
            direction = -1 if key_label.endswith("up") else 1
            if self._navigate_history(direction):
                event.stop()
                return True
        return False

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
        if command in {"/connect", "/conectar"}:
            if len(tokens) <= 1:
                return "/conectar <host> <usuario> <password|ruta_clave>"
            if len(tokens) == 2:
                host = tokens[1]
                return f"Completa el usuario: `/conectar {host} <usuario> <password|ruta_clave>`"
            if len(tokens) == 3:
                host, usuario = tokens[1], tokens[2]
                return (
                    "Añade la contraseña o ruta de clave: "
                    f"`/conectar {host} {usuario} <password|ruta_clave>`"
                )
            return None
        if command in {"/disconnect", "/desconectar"}:
            if len(tokens) > 1:
                return "`/desconectar` no acepta argumentos adicionales"
            return "Cierra la sesión remota actual"
        if command == "/ayuda":
            if len(tokens) > 1:
                return "`/ayuda` no admite argumentos adicionales"
            return "Muestra la lista de comandos disponibles"
        if command == "/salir":
            if len(tokens) > 1:
                return "`/salir` no admite argumentos adicionales"
            return "Abre un diálogo de confirmación para cerrar la aplicación"
        return None

    def _submit_value(self) -> None:
        if not self._editor:
            return
        content = self._editor.text.strip()
        if not content:
            return
        self._store_history_entry(content)
        self.post_message(self.Submitted(self, content))
        self._editor.load_text("")

    def focus_editor(self) -> None:
        if self._editor:
            self._editor.focus()

    def _format_placeholder(self) -> str:
        template = self._config.placeholder
        try:
            return template.format(
                submit_binding=self._config.submit_binding,
                exit_binding=self._exit_shortcut.binding,
                exit_description=self._exit_shortcut.description,
            )
        except (KeyError, IndexError):
            return template

    def _build_border_subtitle(self) -> str:
        return self._config.submit_binding

    def _store_history_entry(self, entry: str) -> None:
        if not entry:
            return
        if self._history and self._history[-1] == entry:
            self._history_index = None
            return
        self._history.append(entry)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit :]
        self._history_index = None

    def _navigate_history(self, direction: int) -> bool:
        if not self._history:
            return False
        if direction < 0:
            if self._history_index is None:
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            else:
                return False
        else:
            if self._history_index is None:
                return False
            if self._history_index >= len(self._history) - 1:
                self._history_index = None
                self._apply_history_entry("")
                return True
            self._history_index += 1
        entry = "" if self._history_index is None else self._history[self._history_index]
        self._apply_history_entry(entry)
        return True

    def _apply_history_entry(self, entry: str) -> None:
        if not self._editor:
            return
        self._navigating_history = True
        self._editor.load_text(entry)
        self.value = entry
        self._navigating_history = False
        self._update_placeholder_hint()


class ConnectionInfo(Static):
    """Muestra el estado de la conexión activa y el progreso del agente."""

    def __init__(self, panel_config: PanelConfig) -> None:
        super().__init__(id="connection-info")
        self._panel_config = panel_config
        self._message = "Sin conexión activa"
        self._thinking = False
        self._status_node: Static | None = None
        self._indicator_node: Static | None = None

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static("", id="connection-info-status"),
            Static("", id="connection-info-indicator"),
            id="connection-info-row",
        )

    def on_mount(self) -> None:
        self.styles.width = "100%"
        self.styles.height = "auto"
        self.styles.min_height = 2
        self.styles.max_height = 2
        self.styles.dock = "bottom"
        self.styles.padding = (0, 1)
        self.styles.background = self._panel_config.background or "black"
        self.styles.border_top = ("heavy", self._panel_config.border_style)

        row = self.query_one("#connection-info-row", Horizontal)
        row.styles.width = "100%"
        row.styles.height = "100%"
        row.styles.align_vertical = "middle"
        row.styles.justify_content = "space-between"

        self._status_node = self.query_one("#connection-info-status", Static)
        self._indicator_node = self.query_one("#connection-info-indicator", Static)
        self._indicator_node.styles.color = self._panel_config.text_style

        self.refresh_status(self._message)

    def refresh_status(self, message: str) -> None:
        self._message = message
        self._render()

    def set_thinking(self, active: bool) -> None:
        self._thinking = active
        self._render()

    def _render(self) -> None:
        if not self._status_node or not self._indicator_node:
            return
        status_text = Text.assemble(
            (f"{self._panel_config.title}: ", self._panel_config.border_style),
            (self._message, self._panel_config.text_style),
        )
        self._status_node.update(status_text)
        if self._thinking:
            thinker = Text(
                "⏳ pensando…",
                style=f"{self._panel_config.text_style} italic",
            )
        else:
            thinker = Text("", style=self._panel_config.text_style)
        self._indicator_node.update(thinker)
