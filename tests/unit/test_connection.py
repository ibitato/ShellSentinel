"""Pruebas para SSHConnectionManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from smart_ai_sys_admin.connection import (
    ConnectionAlreadyOpen,
    ConnectionDetails,
    ConnectionError,
    NoActiveConnection,
    SSHConnectionManager,
)


def _connected_manager(
    connection_logger,
    *,
    host: str = "srv",
    username: str = "alice",
    port: int = 22,
    auth_method: str = "password",
) -> SSHConnectionManager:
    manager = SSHConnectionManager(connection_logger)
    manager._ssh_client = MagicMock()
    manager._sftp_client = MagicMock()
    transport = MagicMock()
    transport.is_active.return_value = True
    manager._ssh_client.get_transport.return_value = transport
    manager._details = ConnectionDetails(
        host=host,
        port=port,
        username=username,
        auth_method=auth_method,
    )
    return manager


def test_connect_missing_secret(connection_logger):
    manager = SSHConnectionManager(connection_logger)
    with pytest.raises(ConnectionError):
        manager.connect("host", "user")


def test_connect_invalid_port(connection_logger):
    manager = SSHConnectionManager(connection_logger)
    with pytest.raises(ConnectionError):
        manager.connect("host", "user", password="x", port=0)


def test_connect_missing_key_file(connection_logger, tmp_path: Path):
    manager = SSHConnectionManager(connection_logger)
    missing = tmp_path / "id_rsa"
    with pytest.raises(ConnectionError, match=str(missing)):
        manager.connect("host", "user", key_path=str(missing))


@patch("smart_ai_sys_admin.connection.paramiko.SSHClient")
def test_connect_password_success(mock_ssh_client_cls, connection_logger):
    ssh_client = MagicMock()
    sftp_client = MagicMock()
    transport = MagicMock()
    transport.is_active.return_value = True
    ssh_client.get_transport.return_value = transport
    ssh_client.open_sftp.return_value = sftp_client
    channel = MagicMock()
    sftp_client.get_channel.return_value = channel
    mock_ssh_client_cls.return_value = ssh_client

    manager = SSHConnectionManager(connection_logger)
    details = manager.connect("host", "alice", password="secret", port=2222)

    assert details.auth_method == "password"
    assert manager.is_connected
    ssh_client.connect.assert_called_once()


def test_connect_already_open(connection_logger):
    manager = _connected_manager(connection_logger)
    with pytest.raises(ConnectionAlreadyOpen):
        manager.connect("host", "alice", password="x")


def test_disconnect_without_connection(connection_logger):
    manager = SSHConnectionManager(connection_logger)
    with pytest.raises(NoActiveConnection):
        manager.disconnect()


def test_disconnect_closes_clients(connection_logger):
    manager = _connected_manager(connection_logger)
    manager.disconnect()
    assert not manager.is_connected
    assert manager.details is None


def test_run_command_without_connection(connection_logger):
    manager = SSHConnectionManager(connection_logger)
    with pytest.raises(NoActiveConnection):
        manager.run_command("echo hi")


def test_run_command_returns_output(connection_logger):
    manager = _connected_manager(connection_logger)
    stdout = MagicMock()
    stderr = MagicMock()
    stdout.read.return_value = b"hello"
    stderr.read.return_value = b""
    stdout.channel.recv_exit_status.return_value = 0
    manager._ssh_client.exec_command.return_value = (MagicMock(), stdout, stderr)

    code, out, err = manager.run_command("echo hi", timeout=5)

    assert code == 0
    assert out == "hello"
    assert err == ""


def test_status_summary_disconnected(connection_logger):
    manager = SSHConnectionManager(connection_logger)
    summary = manager.status_summary()
    assert isinstance(summary, str)
    assert summary


def test_upload_rejects_missing_local(connection_logger):
    manager = _connected_manager(connection_logger)
    with pytest.raises(ConnectionError):
        manager.upload_file("/no/local", "/remote/file")


def test_download_rejects_existing_local(connection_logger, tmp_path: Path):
    manager = _connected_manager(connection_logger)
    local = tmp_path / "existing.txt"
    local.write_text("data", encoding="utf-8")
    with pytest.raises(ConnectionError):
        manager.download_file("/remote/file", str(local), overwrite=False)
