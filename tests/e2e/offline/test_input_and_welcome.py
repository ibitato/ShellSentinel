"""E2E offline: pantalla de bienvenida y capa de entrada del TUI."""

from __future__ import annotations

import pytest
from textual.screen import Screen

from smart_ai_sys_admin.localization import _
from smart_ai_sys_admin.ui.panels import CommandInput
from smart_ai_sys_admin.ui.welcome import WelcomeScreen
from tests.e2e.fake_model import ScriptedModel

pytestmark = pytest.mark.e2e_offline


async def test_welcome_dismissed_by_key_and_editor_focused(tui):
    async with tui(dismiss_welcome=False) as driver:
        assert isinstance(driver.app.screen, WelcomeScreen)
        assert driver.agent_messages() == ["Welcome"]

        await driver.dismiss_welcome()

        assert isinstance(driver.app.screen, Screen)
        assert not isinstance(driver.app.screen, WelcomeScreen)
        assert driver.app.focused is not None and driver.app.focused.id == "editor"


async def test_typing_slash_help_with_pilot(tui, scripted_model: ScriptedModel):
    async with tui() as driver:
        driver.editor.focus()
        await driver.pilot.pause()
        await driver.pilot.press(*"/help")
        assert driver.editor.text == "/help"

        await driver.pilot.press(driver.app._config.ui.input_widget.submit_binding)
        await driver.wait_idle()

        assert driver.editor.text == ""
        assert driver.user_messages()[-1] == "/help"
        assert "/connect" in driver.last_agent()
        assert scripted_model.calls == []


async def test_blank_submission_is_rejected(tui):
    async with tui() as driver:
        before = len(driver.conversation())
        await driver.start_submit("   ")
        await driver.wait_idle()
        assert len(driver.conversation()) == before

        widget = driver.app.query_one(CommandInput)
        await driver.app.on_command_input_submitted(CommandInput.Submitted(widget, ""))
        await driver.wait_idle()
        assert driver.last_agent() == _("ui.app.input_required")
