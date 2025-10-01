"""Gestión de conexiones SSH y SFTP empleando Paramiko."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import paramiko

from .localization import _


class ConnectionError(Exception):
    """Error genérico asociado a la conexión SSH."""


class ConnectionAlreadyOpen(ConnectionError):
    """Se intenta abrir una conexión cuando ya existe una activa."""


class NoActiveConnection(ConnectionError):
    """Se intenta operar sin que exista una conexión activa."""


@dataclass(frozen=True)
class ConnectionDetails:
    host: str
    port: int
    username: str
    auth_method: str


class SSHConnectionManager:
    """Gestiona el ciclo de vida de la conexión SSH/SFTP."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._ssh_client: paramiko.SSHClient | None = None
        self._sftp_client: paramiko.SFTPClient | None = None
        self._details: ConnectionDetails | None = None

    def connect(
        self,
        host: str,
        username: str,
        *,
        password: str | None = None,
        key_path: str | None = None,
        port: int = 22,
    ) -> ConnectionDetails:
        if self.is_connected:
            raise ConnectionAlreadyOpen(_("connection.errors.already_open"))
        if not password and not key_path:
            raise ConnectionError(_("connection.errors.missing_secret"))
        if port <= 0 or port > 65535:
            raise ConnectionError(
                _("connection.errors.invalid_port", port=port)
            )

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict[str, object] = {
            "hostname": host,
            "username": username,
            "timeout": 10,
            "look_for_keys": False,
            "allow_agent": False,
            "port": port,
        }
        auth_method = "password"
        if key_path:
            resolved_key = Path(key_path).expanduser()
            if not resolved_key.is_file():
                raise ConnectionError(
                    _(
                        "connection.errors.missing_key",
                        path=str(resolved_key),
                    )
                )
            connect_kwargs["key_filename"] = str(resolved_key)
            auth_method = "key"
        else:
            connect_kwargs["password"] = password

        try:
            self._logger.debug(
                "Intentando conexión SSH con %s@%s:%s usando %s",
                username,
                host,
                port,
                auth_method,
            )
            ssh_client.connect(**connect_kwargs)
            sftp_client = ssh_client.open_sftp()
            transport = ssh_client.get_transport()
            if transport:
                transport.set_keepalive(30)
            try:
                channel = sftp_client.get_channel()
                channel.settimeout(30)
            except Exception:  # pragma: no cover - depende del backend
                pass
        except Exception as exc:  # pragma: no cover - depende del entorno remoto.
            ssh_client.close()
            self._logger.exception(
                "Fallo estableciendo conexión con %s@%s:%s", username, host, port
            )
            raise ConnectionError(str(exc)) from exc

        self._ssh_client = ssh_client
        self._sftp_client = sftp_client
        self._details = ConnectionDetails(
            host=host,
            port=port,
            username=username,
            auth_method=auth_method,
        )
        self._logger.info(
            "Conexión abierta con %s@%s:%s (%s)", username, host, port, auth_method
        )
        return self._details

    def disconnect(self) -> None:
        if not self.is_connected:
            raise NoActiveConnection(_("connection.errors.no_active_session"))
        assert self._ssh_client
        self._logger.debug(
            "Cerrando conexión SSH con %s@%s:%s",
            self._details.username if self._details else "?",
            self._details.host if self._details else "?",
            self._details.port if self._details else "?",
        )
        try:
            if self._sftp_client:
                self._sftp_client.close()
        finally:
            self._ssh_client.close()
        if self._details:
            self._logger.info(
                "Conexión cerrada con %s@%s:%s",
                self._details.username,
                self._details.host,
                self._details.port,
            )
        self._ssh_client = None
        self._sftp_client = None
        self._details = None

    @property
    def is_connected(self) -> bool:
        if not self._ssh_client:
            return False
        transport = self._ssh_client.get_transport()
        return bool(transport and transport.is_active())

    @property
    def details(self) -> ConnectionDetails | None:
        if not self.is_connected:
            return None
        return self._details

    def status_summary(self) -> str:
        if not self.is_connected or not self._details:
            return _("connection.status.none")
        method_key = f"connection.auth.method.{self._details.auth_method}"
        try:
            method_label = _(method_key)
        except KeyError:
            method_label = self._details.auth_method
        return _(
            "connection.status.connected",
            username=self._details.username,
            host=self._details.host,
            port=self._details.port,
            method=method_label,
        )

    def run_command(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Ejecuta un comando remoto y devuelve código de salida, stdout y stderr."""

        if not self.is_connected or not self._ssh_client:
            raise NoActiveConnection(_("connection.errors.no_active_ssh"))
        self._logger.debug("Ejecutando comando remoto: %s", command)
        try:
            stdin, stdout, stderr = self._ssh_client.exec_command(command, timeout=timeout)
        except Exception as exc:  # pragma: no cover - depende del host remoto
            raise ConnectionError(
                _(
                    "connection.errors.command_failed",
                    command=command,
                    error=str(exc),
                )
            ) from exc
        try:
            out_text = stdout.read().decode("utf-8", errors="replace")
            err_text = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()
        finally:
            stdin.close()
            stdout.close()
            stderr.close()
        self._logger.debug("Comando '%s' finalizado con código %s", command, exit_status)
        return exit_status, out_text, err_text

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        *,
        overwrite: bool = False,
    ) -> str:
        if not self.is_connected:
            raise NoActiveConnection(_("connection.errors.no_active_ssh"))
        if not self._sftp_client:
            raise NoActiveConnection(_("connection.errors.no_active_sftp"))

        local = Path(local_path).expanduser()
        if not local.exists():
            raise ConnectionError(
                _(
                    "connection.errors.local_missing",
                    path=str(local),
                )
            )
        if not local.is_file():
            raise ConnectionError(
                _(
                    "connection.errors.local_not_file",
                    path=str(local),
                )
            )

        remote = PurePosixPath(remote_path)
        sftp = self._sftp_client

        if not overwrite:
            try:
                sftp.stat(str(remote))
            except FileNotFoundError:
                pass
            else:
                raise ConnectionError(
                    _(
                        "connection.errors.remote_exists",
                        path=str(remote),
                    )
                )

        self._ensure_remote_directory(remote.parent)

        try:
            sftp.put(str(local), str(remote))
        except FileNotFoundError as exc:
            raise ConnectionError(
                _(
                    "connection.errors.upload_missing",
                    local=str(local),
                    remote=str(remote),
                    error=str(exc),
                )
            ) from exc
        except Exception as exc:  # pragma: no cover - errores específicos de SFTP
            raise ConnectionError(
                _(
                    "connection.errors.upload_generic",
                    remote=str(remote),
                    error=str(exc),
                )
            ) from exc

        self._logger.info("Archivo '%s' transferido a '%s'", local, remote)
        return str(remote)

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        *,
        overwrite: bool = False,
    ) -> Path:
        if not self.is_connected:
            raise NoActiveConnection(_("connection.errors.no_active_ssh"))
        if not self._sftp_client:
            raise NoActiveConnection(_("connection.errors.no_active_sftp"))

        remote = PurePosixPath(remote_path)
        local = Path(local_path).expanduser()
        if local.exists() and not overwrite:
            raise ConnectionError(
                _(
                    "connection.errors.local_exists",
                    path=str(local),
                )
            )
        local.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._sftp_client.get(str(remote), str(local))
        except FileNotFoundError as exc:
            raise ConnectionError(
                _(
                    "connection.errors.remote_missing",
                    path=str(remote),
                    error=str(exc),
                )
            ) from exc
        except Exception as exc:  # pragma: no cover - errores específicos de SFTP
            raise ConnectionError(
                _(
                    "connection.errors.download_generic",
                    path=str(remote),
                    error=str(exc),
                )
            ) from exc

        self._logger.info("Archivo '%s' descargado desde '%s'", local, remote)
        return local

    def _ensure_remote_directory(self, directory: PurePosixPath) -> None:
        if not directory or str(directory) in {"", ".", "/"}:
            return
        if not self._sftp_client:
            raise NoActiveConnection("La sesión SFTP no está disponible.")

        current = PurePosixPath("/")
        for part in directory.parts:
            if part == "/":
                current = PurePosixPath("/")
                continue
            current = current / part
            try:
                self._sftp_client.stat(str(current))
            except FileNotFoundError:
                try:
                    self._sftp_client.mkdir(str(current))
                    self._logger.debug("Directorio remoto creado: %s", current)
                except Exception as exc:  # pragma: no cover - depende del host remoto
                    raise ConnectionError(
                        _(
                            "connection.errors.mkdir_remote",
                            path=str(current),
                            error=str(exc),
                        )
                    ) from exc
