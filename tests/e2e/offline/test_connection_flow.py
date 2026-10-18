"""E2E offline: ciclo de conexión SSH desde el TUI contra el servidor embebido."""

from __future__ import annotations

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.ssh_server import E2E_PASSWORD, E2E_USERNAME, ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline


async def test_connect_updates_footer_and_panel(tui, ssh: ScriptedSSHServer, connect_line: str):
    async with tui() as driver:
        reply = await driver.submit(connect_line)

        expected = _(
            "ui.commands.connect.success",
            username=E2E_USERNAME,
            host=ssh.host,
            port=ssh.port,
            auth_label=_("connection.auth.method.password"),
        )
        assert reply == expected
        echoed = driver.user_messages()[-1]
        assert "***" in echoed and E2E_PASSWORD not in echoed
        footer = driver.footer()
        assert f"Connected to {E2E_USERNAME}@{ssh.host}:{ssh.port} (password)" in footer
        assert "Provider: OpenAI" in footer and "gpt-test" in footer
        assert driver.connection.is_connected


async def test_connect_wrong_password_shows_failure(tui, ssh: ScriptedSSHServer):
    async with tui() as driver:
        reply = await driver.submit(f"/connect {ssh.host} {ssh.username} wrong-pass {ssh.port}")

        assert reply.startswith("❌")
        assert "Authentication failed" in reply
        assert _("connection.status.none") in driver.footer()
        assert not driver.connection.is_connected


async def test_status_disconnect_and_status_again(tui, ssh: ScriptedSSHServer, connect_line: str):
    async with tui() as driver:
        await driver.submit(connect_line)

        status = await driver.submit("/status")
        assert _("ui.commands.status.header") in status
        assert f"Connected to {ssh.username}@{ssh.host}:{ssh.port}" in status
        assert "OpenAI" in status and "gpt-test" in status
        assert f"- {_('ui.commands.status.agent_ready')}: {_('common.yes')}" in status
        assert f"- {_('ui.commands.status.cache')}: {_('common.yes')}" in status

        reply = await driver.submit("/disconnect")
        assert reply == _("ui.commands.disconnect.success")
        assert _("connection.status.none") in driver.footer()
        assert not driver.connection.is_connected

        reply = await driver.submit("/disconnect")
        assert reply.startswith(_("ui.commands.disconnect.no_active"))
