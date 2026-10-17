"""Pruebas para SSHConnectionManager."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
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
    transport = MagicMock()
    transport.is_active.return_value = True
    ssh_client.get_transport.return_value = transport
    mock_ssh_client_cls.return_value = ssh_client

    manager = SSHConnectionManager(connection_logger)
    details = manager.connect("host", "alice", password="secret", port=2222)

    assert details.auth_method == "password"
    assert manager.is_connected
    ssh_client.connect.assert_called_once()
    ssh_client.open_sftp.assert_not_called()
    assert manager._sftp_client is None


@patch("smart_ai_sys_admin.connection.paramiko.SSHClient")
def test_open_sftp_lazy_on_upload(mock_ssh_client_cls, connection_logger, tmp_path: Path):
    ssh_client = MagicMock()
    sftp_client = MagicMock()
    transport = MagicMock()
    transport.is_active.return_value = True
    ssh_client.get_transport.return_value = transport
    ssh_client.open_sftp.return_value = sftp_client
    sftp_client.get_channel.return_value = MagicMock()
    mock_ssh_client_cls.return_value = ssh_client

    manager = SSHConnectionManager(connection_logger)
    manager.connect("host", "alice", password="secret")
    local = tmp_path / "file.txt"
    local.write_text("data", encoding="utf-8")

    manager.upload_file(str(local), "/remote/file.txt", overwrite=True)

    ssh_client.open_sftp.assert_called_once()


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
    stdout.channel = _fake_channel(b"hello", b"")
    manager._ssh_client.exec_command.return_value = (MagicMock(), stdout, MagicMock())

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


def _fake_channel(out: bytes, err: bytes, *, exit_status: int = 0, finished: bool = True):
    """Simula un canal Paramiko que entrega stdout/stderr de una sola vez."""

    channel = MagicMock()
    state = {"out": out, "err": err}

    def _take(key: str) -> bytes:
        data, state[key] = state[key], b""
        return data

    channel.recv_ready.side_effect = lambda: bool(state["out"])
    channel.recv_stderr_ready.side_effect = lambda: bool(state["err"])
    channel.recv.side_effect = lambda _size: _take("out")
    channel.recv_stderr.side_effect = lambda _size: _take("err")
    channel.exit_status_ready.return_value = finished
    channel.recv_exit_status.return_value = exit_status
    return channel


def test_run_command_drains_stdout_and_stderr(connection_logger):
    manager = _connected_manager(connection_logger)
    stdout = MagicMock()
    stdout.channel = _fake_channel(b"out", b"err" * 1000, exit_status=3)
    manager._ssh_client.exec_command.return_value = (MagicMock(), stdout, MagicMock())

    code, out, err = manager.run_command("cmd", timeout=5)

    assert (code, out, err) == (3, "out", "err" * 1000)
    stdout.channel.close.assert_called_once()


def test_run_command_enforces_total_timeout(connection_logger):
    manager = _connected_manager(connection_logger)
    stdout = MagicMock()
    stdout.channel = _fake_channel(b"", b"", finished=False)
    manager._ssh_client.exec_command.return_value = (MagicMock(), stdout, MagicMock())

    with patch("smart_ai_sys_admin.connection.time.monotonic", side_effect=[0.0, 10.0]):
        with pytest.raises(ConnectionError, match="cmd"):
            manager.run_command("cmd", timeout=5)
    stdout.channel.close.assert_called_once()


def test_ensure_remote_directory_relative_path(connection_logger):
    manager = _connected_manager(connection_logger)
    sftp = manager._sftp_client
    sftp.stat.side_effect = FileNotFoundError

    manager._ensure_remote_directory(PurePosixPath("backups/daily"))

    created = [call.args[0] for call in sftp.mkdir.call_args_list]
    assert created == ["backups", "backups/daily"]


def test_ensure_remote_directory_absolute_path(connection_logger):
    manager = _connected_manager(connection_logger)
    sftp = manager._sftp_client
    sftp.stat.side_effect = FileNotFoundError

    manager._ensure_remote_directory(PurePosixPath("/srv/app"))

    created = [call.args[0] for call in sftp.mkdir.call_args_list]
    assert created == ["/srv", "/srv/app"]
