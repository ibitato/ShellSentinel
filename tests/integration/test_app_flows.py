"""Pruebas de flujo de la aplicación TUI."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from smart_ai_sys_admin.config import load_config
from smart_ai_sys_admin.plugins.types import PluginSlashCommand
from smart_ai_sys_admin.ui.app import SmartAISysAdminApp
from smart_ai_sys_admin.ui.panels import CommandInput


@pytest.fixture
def app_config(minimal_app_config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_CONFIG_FILE", str(minimal_app_config))
    return load_config()


def _build_app(app_config, fake_ssh_manager, fake_agent_runtime) -> SmartAISysAdminApp:
    app = SmartAISysAdminApp(config=app_config)
    app._connection_manager = fake_ssh_manager
    app._agent_runtime = fake_agent_runtime  # type: ignore[assignment]
    app._command_processor._connection_manager = fake_ssh_manager
    app._command_processor._agent_runtime = fake_agent_runtime  # type: ignore[assignment]
    app._welcome_shown = True
    app._initialize_agent_runtime = lambda: None  # type: ignore[method-assign]
    return app


async def _submit(app: SmartAISysAdminApp, content: str) -> None:
    input_widget = app.query_one(CommandInput)
    assert input_widget._editor is not None
    input_widget._editor.load_text(content)
    await app.on_command_input_submitted(CommandInput.Submitted(input_widget, content))


@pytest.mark.asyncio
async def test_app_mount_widgets(app_config, fake_ssh_manager, fake_agent_runtime):
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test() as pilot:
        assert pilot.app.query_one("#main-layout") is not None
        assert pilot.app.query_one("ConversationPanel") is not None
        assert pilot.app.query_one("CommandInput") is not None


@pytest.mark.asyncio
async def test_help_command_does_not_invoke_agent(app_config, fake_ssh_manager, fake_agent_runtime):
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test():
        await _submit(app, "/help")
        assert fake_agent_runtime.invoke_calls == []


@pytest.mark.asyncio
async def test_natural_language_invokes_agent(app_config, fake_ssh_manager, fake_agent_runtime):
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test():
        await _submit(app, "lista procesos")
        assert fake_agent_runtime.invoke_calls == ["lista procesos"]


@pytest.mark.asyncio
async def test_connect_command_updates_manager(app_config, fake_ssh_manager, fake_agent_runtime):
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test():
        await _submit(app, "/connect srv alice secret")
        assert fake_ssh_manager.connect_calls


@pytest.mark.asyncio
async def test_status_command_no_crash(app_config, fake_ssh_manager, fake_agent_runtime):
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test():
        await _submit(app, "/status")
        assert app.query_one("ConversationPanel") is not None


@pytest.mark.asyncio
async def test_agent_unavailable_message(app_config, fake_ssh_manager, fake_agent_runtime):
    fake_agent_runtime.ready = False
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    async with app.run_test():
        await _submit(app, "hola")
        assert fake_agent_runtime.invoke_calls == []


@pytest.mark.asyncio
async def test_plugin_command_executes(app_config, fake_ssh_manager, fake_agent_runtime):
    command = PluginSlashCommand(name="/demo", handler=lambda args: "plugin-ok")
    app = _build_app(app_config, fake_ssh_manager, fake_agent_runtime)
    app._command_processor.register_plugin_commands([command])
    async with app.run_test():
        await _submit(app, "/demo")
        assert fake_agent_runtime.invoke_calls == []


@pytest.mark.asyncio
@patch.object(SmartAISysAdminApp, "_show_welcome_screen")
@patch.object(SmartAISysAdminApp, "_initialize_agent_runtime")
@patch("smart_ai_sys_admin.ui.app.PluginManager.load")
async def test_thinking_indicator_during_invoke(
    mock_load,
    mock_init,
    mock_welcome,
    app_config,
    fake_ssh_manager,
):
    import time

    class SlowRuntime:
        ready = True

        def invoke(self, prompt: str) -> str:
            time.sleep(0.05)
            return "done"

        def provider_footer_summary(self) -> str:
            return ""

        def agent_summary(self) -> dict:
            return {"ready": True}

        def initialize(self) -> None:
            return None

        def shutdown(self) -> None:
            return None

    app = _build_app(app_config, fake_ssh_manager, SlowRuntime())  # type: ignore[arg-type]
    async with app.run_test():
        await _submit(app, "slow prompt")
