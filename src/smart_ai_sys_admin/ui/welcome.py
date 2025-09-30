# ruff: noqa: E501

"""Pantalla de bienvenida inicial con arte ASCII."""

from __future__ import annotations

from rich.text import Text
from textual import events
from textual.containers import Center, Container, Vertical
from textual.screen import Screen
from textual.widgets import Static

from ..localization import _

ASCII_ART = r"""
   ███     ██        ███     ███    ██████      ██████    ██████████          ██      ██  ██      ██  ███     ███     ███     ███     ██  
  ██ ██    ██        ████   ████   ██    ██    ██    ██      ██             ██      ██  ██      ██  ████   ████    ██ ██    ████    ██  
 ██   ██   ██        ██ ██ ██ ██  ██      ██   ██           ██             ██      ██  ██      ██  ██ ██ ██ ██   ██   ██   ██ ██   ██  
██     ██  ██        ██  ███  ██  ██      ██    ██████      ██             ██████████  ██      ██  ██  ███  ██  ██     ██  ██  ██  ██  
█████████  ██        ██   █   ██  ██      ██         ██     ██             ██      ██  ██      ██  ██   █   ██  █████████  ██   ██ ██  
██     ██  ██        ██       ██   ██    ██    ██    ██     ██             ██      ██   ██    ██   ██       ██  ██     ██  ██    ████  
██     ██  ████████  ██       ██    ██████      ██████      ██             ██      ██    ██████    ██       ██  ██     ██  ██     ███  
"""


class WelcomeScreen(Screen[None]):
    """Muestra un splash inicial centrado y con cierre automático."""

    AUTO_CLOSE_SECONDS = 5

    def __init__(
        self,
        *,
        primary_color: str = "#FF8C00",
        accent_color: str = "#FFB347",
        background: str = "black",
    ) -> None:
        super().__init__()
        self._primary_color = primary_color
        self._accent_color = accent_color
        self._background = background
        self._dismissed = False

    def compose(self):
        art_text = Text(ASCII_ART.rstrip(), justify="center", style=f"bold {self._primary_color}")
        title = Text(
            "Almost Human Sys Admin",
            justify="center",
            style=f"bold {self._accent_color}",
        )
        hint = Text(
            _(
                "ui.welcome.hint",
                seconds=self.AUTO_CLOSE_SECONDS,
            ),
            justify="center",
            style=f"italic dim {self._accent_color}",
        )

        yield Container(
            Center(
                Vertical(
                    Static(art_text, id="welcome-art"),
                    Static(title, id="welcome-title"),
                    Static(hint, id="welcome-hint"),
                    id="welcome-stack",
                ),
                id="welcome-center",
            ),
            id="welcome-root",
        )

    def on_mount(self) -> None:
        root = self.query_one("#welcome-root", Container)
        center = self.query_one("#welcome-center", Center)
        stack = self.query_one("#welcome-stack", Vertical)
        root.styles.height = "100%"
        root.styles.width = "100%"
        root.styles.background = self._background
        self.styles.background = self._background
        center.styles.width = "100%"
        center.styles.height = "100%"
        center.styles.background = "transparent"
        stack.styles.align_items = "center"
        stack.styles.justify_content = "center"
        stack.styles.gap = 1
        for widget in stack.children:
            if isinstance(widget, Static):
                widget.styles.padding = (0, 2)
                widget.styles.width = "100%"
                widget.styles.text_align = "center"
        self.set_timer(self.AUTO_CLOSE_SECONDS, self._dismiss)

    def on_key(self, event: events.Key) -> None:  # pragma: no cover - interacción de usuario
        event.stop()
        self._dismiss()

    def on_mouse_down(  # pragma: no cover - interacción de usuario
        self, event: events.MouseDown
    ) -> None:
        event.stop()
        self._dismiss()

    def _dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        self.dismiss(None)


__all__ = ["WelcomeScreen"]
