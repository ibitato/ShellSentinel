"""Pruebas para las tools del agente."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from smart_ai_sys_admin.agent.tools import (
    DEFAULT_REMOTE_TIMEOUT,
    local_datetime,
    remote_sftp_transfer,
    remote_ssh_command,
    resolve_tools,
)
from smart_ai_sys_admin.connection import ConnectionError


@pytest.mark.asyncio
async def test_remote_ssh_command_without_manager():
    agent = SimpleNamespace()
    result = await remote_ssh_command("echo hi", agent=agent)
    assert isinstance(result, str)
    assert result


@pytest.mark.asyncio
async def test_remote_ssh_command_inactive(fake_ssh_manager):
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_ssh_command("echo hi", agent=agent)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_remote_ssh_command_success(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    fake_ssh_manager._run_result = (0, "hello\n", "")
    agent = SimpleNamespace(
        ssh_manager=fake_ssh_manager,
        remote_command_timeout=30,
        remote_command_max_output_chars=5000,
    )
    result = await remote_ssh_command("echo hi", agent=agent)
    assert "hello" in result
    assert fake_ssh_manager.commands_run == [("echo hi", 30)]


@pytest.mark.asyncio
async def test_remote_ssh_command_invalid_timeout(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_ssh_command("echo hi", agent=agent, timeout_seconds="bad")
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_remote_ssh_command_truncates_output(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    fake_ssh_manager._run_result = (0, "x" * 5000, "")
    agent = SimpleNamespace(
        ssh_manager=fake_ssh_manager,
        remote_command_timeout=DEFAULT_REMOTE_TIMEOUT,
        remote_command_max_output_chars=100,
    )
    result = await remote_ssh_command("big", agent=agent)
    assert "truncad" in result.lower() or "trunc" in result.lower() or len(result) < 5000


@pytest.mark.asyncio
async def test_remote_ssh_command_connection_error(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True

    def _fail(command: str, *, timeout: int | None = None):
        raise ConnectionError("boom")

    fake_ssh_manager.run_command = _fail  # type: ignore[method-assign]
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_ssh_command("fail", agent=agent)
    assert "boom" in result


@pytest.mark.asyncio
async def test_remote_sftp_transfer_invalid_action(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_sftp_transfer("copy", "/a", "/b", agent=agent)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_remote_sftp_transfer_upload(fake_ssh_manager, tmp_path: Path):
    fake_ssh_manager._fake_connected = True
    local = tmp_path / "file.txt"
    local.write_text("data", encoding="utf-8")
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_sftp_transfer("upload", str(local), "/remote/file.txt", agent=agent)
    assert "/remote/file.txt" in result


@pytest.mark.asyncio
async def test_remote_sftp_transfer_download(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    agent = SimpleNamespace(ssh_manager=fake_ssh_manager)
    result = await remote_sftp_transfer("get", "/local/out.txt", "/remote/file.txt", agent=agent)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_local_datetime_iso(mock_agent_namespace):
    result = await local_datetime(agent=mock_agent_namespace)
    parsed = datetime.fromisoformat(result)
    assert parsed.tzinfo is not None


def test_resolve_tools_extends_without_mutation():
    def custom_tool() -> str:
        return "x"

    first = resolve_tools()
    second = resolve_tools([custom_tool])
    assert len(second) == len(first) + 1
    assert len(first) == len(resolve_tools())
