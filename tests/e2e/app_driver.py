"""Conductor del TUI real bajo ``App.run_test()`` para las pruebas e2e."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from rich.markdown import Markdown
from rich.text import Text
from textual.pilot import Pilot
from textual.widgets import Static, TextArea

from smart_ai_sys_admin.ui.app import SmartAISysAdminApp
from smart_ai_sys_admin.ui.panels import ConversationPanel
from smart_ai_sys_admin.ui.welcome import WelcomeScreen

DEFAULT_IDLE_TIMEOUT = 15.0


def _plain(renderable: Any) -> str:
    if isinstance(renderable, Markdown):
        return renderable.markup
    if isinstance(renderable, Text):
        return renderable.plain
    plain = getattr(renderable, "plain", None)
    if isinstance(plain, str):
        return plain
    return str(renderable)


@dataclass
class TuiDriver:
    """Envía entradas por el camino real (editor + atajo) y lee lo que el TUI muestra."""

    app: SmartAISysAdminApp
    pilot: Pilot[Any]

    @property
    def runtime(self):  # type: ignore[no-untyped-def]
        return self.app._agent_runtime

    @property
    def connection(self):  # type: ignore[no-untyped-def]
        return self.app._connection_manager

    @property
    def editor(self) -> TextArea:
        return self.app.query_one("#editor", TextArea)

    async def dismiss_welcome(self) -> None:
        """Cierra la pantalla de bienvenida con una tecla, como haría el operador."""

        assert isinstance(self.app.screen, WelcomeScreen), type(self.app.screen)
        await self.pilot.press("escape")
        await self.pilot.pause()
        assert not isinstance(self.app.screen, WelcomeScreen)
        focused = self.app.focused
        assert focused is not None and focused.id == "editor", focused

    async def start_submit(self, text: str) -> None:
        """Carga ``text`` en el editor y pulsa el atajo de envío sin esperar al resultado."""

        editor = self.editor
        editor.focus()
        await self.pilot.pause()
        editor.load_text(text)
        await self.pilot.pause()
        await self.pilot.press(self.app._config.ui.input_widget.submit_binding)
        await self.pilot.pause()

    async def wait_idle(self, timeout: float = DEFAULT_IDLE_TIMEOUT) -> None:
        """Espera a que terminen los workers y se libere el guard ``_busy``."""

        async def _idle() -> None:
            await self.app.workers.wait_for_complete()
            while self.app._busy:
                await asyncio.sleep(0.01)
            await self.pilot.pause()

        await asyncio.wait_for(_idle(), timeout)

    async def submit(self, text: str, *, timeout: float = DEFAULT_IDLE_TIMEOUT) -> str:
        """Envía ``text`` y devuelve el último panel del agente tras completarse."""

        await self.start_submit(text)
        await self.wait_idle(timeout)
        return self.last_agent()

    # ------------------------------------------------------------------ lectura
    def conversation(self) -> list[tuple[str, str]]:
        """Pares ``(título, texto)`` de la conversación: fuente markdown, sin renderizar."""

        panel = self.app.query_one(ConversationPanel)
        return [(str(entry.title), _plain(entry.renderable)) for entry in panel._history]

    def agent_messages(self) -> list[str]:
        title = self.app._config.ui.output_panel.title
        return [text for panel_title, text in self.conversation() if panel_title == title]

    def user_messages(self) -> list[str]:
        title = self.app._config.ui.user_panel.title
        return [text for panel_title, text in self.conversation() if panel_title == title]

    def last_agent(self) -> str:
        messages = self.agent_messages()
        assert messages, "la conversación no tiene paneles del agente"
        return messages[-1]

    def footer(self) -> str:
        node = self.app.query_one("#connection-info-status", Static)
        return _plain(node.content)


__all__ = ["DEFAULT_IDLE_TIMEOUT", "TuiDriver"]
