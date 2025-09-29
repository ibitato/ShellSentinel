"""Componentes de diálogo para la TUI."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..config import ExitDialogConfig


class ExitConfirmationModal(ModalScreen[bool]):
    """Modal que confirma la intención de cerrar la aplicación."""

    DEFAULT_CSS = """
    ExitConfirmationModal {
        align: center middle;
    }

    ExitConfirmationModal #exit-dialog {
        width: 40%;
        max-width: 48;
        padding: 2 3;
        border: solid #FF8C00;
        background: #000000;
        color: #FFB347;
    }

    ExitConfirmationModal #exit-dialog > .dialog-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        color: #FFB347;
    }

    ExitConfirmationModal #exit-dialog > .dialog-message {
        padding-bottom: 1;
        color: #FFB347;
    }

    ExitConfirmationModal Button {
        background: #000000;
        color: #FFB347;
        border: tall #FF8C00;
    }

    ExitConfirmationModal Button:hover {
        background: #1A1A1A;
        color: #FFB347;
        border: tall #FFB347;
    }

    """

    def __init__(self, config: ExitDialogConfig) -> None:
        super().__init__()
        self._config = config
        self._confirm_button: Button | None = None
        self._cancel_button: Button | None = None

    def compose(self) -> ComposeResult:
        confirm_button = Button(
            self._config.confirm_label,
            id="confirm",
        )
        cancel_button = Button(
            self._config.cancel_label,
            id="cancel",
        )
        cancel_button.styles.margin_left = 2
        self._confirm_button = confirm_button
        self._cancel_button = cancel_button
        buttons = Horizontal(
            confirm_button,
            cancel_button,
            classes="dialog-buttons",
        )
        buttons.styles.align_horizontal = "center"
        yield Vertical(
            Static(self._config.title, classes="dialog-title"),
            Static(self._config.message, classes="dialog-message"),
            buttons,
            id="exit-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore[override]
        event.stop()
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event: events.Key) -> None:  # type: ignore[override]
        if event.key == "escape":
            event.stop()
            self.dismiss(False)
        elif event.key == "left" and self._cancel_button and self._cancel_button.has_focus:
            event.stop()
            if self._confirm_button:
                self._confirm_button.focus()
        elif event.key == "right" and self._confirm_button and self._confirm_button.has_focus:
            event.stop()
            if self._cancel_button:
                self._cancel_button.focus()
        elif event.key in {"enter", "return"}:
            event.stop()
            if self._confirm_button and self._confirm_button.has_focus:
                self.dismiss(True)
            else:
                self.dismiss(False)

    def on_mount(self) -> None:
        if self._confirm_button:
            self._confirm_button.focus()


__all__ = ["ExitConfirmationModal"]
