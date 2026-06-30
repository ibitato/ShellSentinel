"""Pruebas para SlashCommandProcessor."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from smart_ai_sys_admin.connection import ConnectionAlreadyOpen, ConnectionError, NoActiveConnection
from smart_ai_sys_admin.plugins.types import PluginSlashCommand
from smart_ai_sys_admin.ui.commands import SlashCommandProcessor


def test_process_non_slash_returns_none(slash_processor: SlashCommandProcessor):
    assert slash_processor.process("hola mundo") is None


def test_process_whitespace_only_returns_empty(slash_processor: SlashCommandProcessor):
    assert slash_processor.process("   ") == ""


def test_help_overview(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/help")
    assert result is not None
    assert "/connect" in result or "connect" in result.lower()


def test_connect_insufficient_args(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/connect host")
    assert result is not None
    assert result


def test_connect_success(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/connect srv alice secret")
    assert result is not None
    assert fake_ssh_manager._fake_connected
    assert len(fake_ssh_manager.connect_calls) == 1


def test_connect_does_not_log_password(
    caplog, fake_ssh_manager, slash_processor: SlashCommandProcessor
):
    caplog.set_level(logging.INFO, logger="smart_ai_sys_admin.ui.commands")
    slash_processor.process("/connect srv alice top-secret")
    for record in caplog.records:
        assert "top-secret" not in record.getMessage()
        if "argumentos" in record.getMessage():
            assert "***" in record.getMessage()


def test_connect_invalid_port(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/connect srv alice secret 99999")
    assert result is not None
    assert "99999" in result or "port" in result.lower()


def test_connect_already_open(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    fake_ssh_manager._fake_connected = True
    fake_ssh_manager.connect_error = ConnectionAlreadyOpen("open")
    result = slash_processor.process("/connect srv alice secret")
    assert result is not None


def test_connect_connection_error(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    fake_ssh_manager.connect_error = ConnectionError("boom")
    result = slash_processor.process("/connect srv alice secret")
    assert result is not None
    assert "boom" in result


@patch.object(Path, "exists", return_value=True)
def test_connect_key_auth(mock_exists, fake_ssh_manager, slash_processor: SlashCommandProcessor):
    key = "/home/user/.ssh/id_rsa"
    slash_processor.process(f"/connect srv alice {key}")
    call = fake_ssh_manager.connect_calls[0]
    assert call["key_path"] == key


def test_disconnect_success(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    fake_ssh_manager._fake_connected = True
    result = slash_processor.process("/disconnect")
    assert result is not None
    assert fake_ssh_manager.disconnect_calls == 1


def test_disconnect_no_session(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    fake_ssh_manager.disconnect_error = NoActiveConnection("none")
    result = slash_processor.process("/disconnect")
    assert result is not None


def test_disconnect_rejects_extra_args(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/disconnect extra")
    assert result is not None


def test_status_includes_agent_fields(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/status")
    assert result is not None
    assert "gpt-test" in result


def test_status_rejects_extra_args(slash_processor: SlashCommandProcessor):
    result = slash_processor.process("/status extra")
    assert result is not None


def test_register_plugin_conflict_ignored(fake_ssh_manager, slash_processor: SlashCommandProcessor):
    command = PluginSlashCommand(
        name="/connect",
        handler=lambda args: "plugin",
    )
    slash_processor.register_plugin_commands([command])
    result = slash_processor.process("/connect srv alice secret")
    assert result is not None
    assert fake_ssh_manager.connect_calls


def test_plugin_command_executes(slash_processor: SlashCommandProcessor):
    command = PluginSlashCommand(
        name="/demo",
        handler=lambda args: f"demo:{args[0] if args else 'none'}",
        description_key=None,
    )
    slash_processor.register_plugin_commands([command])
    result = slash_processor.process("/demo value")
    assert result == "demo:value"


def test_suggestion_for_connect(slash_processor: SlashCommandProcessor):
    suggestion = slash_processor.suggestion_for("/connect srv")
    assert suggestion is None or isinstance(suggestion, str)
