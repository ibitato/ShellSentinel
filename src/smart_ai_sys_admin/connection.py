"""Gestión de conexiones SSH y SFTP empleando Paramiko."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import paramiko


class ConnectionError(Exception):
    """Error genérico asociado a la conexión SSH."""


class ConnectionAlreadyOpen(ConnectionError):
    """Se intenta abrir una conexión cuando ya existe una activa."""


class NoActiveConnection(ConnectionError):
    """Se intenta operar sin que exista una conexión activa."""


@dataclass(frozen=True)
class ConnectionDetails:
    host: str
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
    ) -> ConnectionDetails:
        if self.is_connected:
            raise ConnectionAlreadyOpen("Ya existe una conexión activa. Usa /disconnect primero.")
        if not password and not key_path:
            raise ConnectionError("Debes proporcionar contraseña o ruta a la clave privada.")

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict[str, object] = {
            "hostname": host,
            "username": username,
            "timeout": 10,
            "look_for_keys": False,
            "allow_agent": False,
        }
        auth_method = "password"
        if key_path:
            resolved_key = Path(key_path).expanduser()
            if not resolved_key.is_file():
                raise ConnectionError(f"No se encontró la clave privada en '{resolved_key}'.")
            connect_kwargs["key_filename"] = str(resolved_key)
            auth_method = "key"
        else:
            connect_kwargs["password"] = password

        try:
            self._logger.debug(
                "Intentando conexión SSH con %s@%s usando %s",
                username,
                host,
                auth_method,
            )
            ssh_client.connect(**connect_kwargs)
            sftp_client = ssh_client.open_sftp()
        except Exception as exc:  # pragma: no cover - depende del entorno remoto.
            ssh_client.close()
            self._logger.exception("Fallo estableciendo conexión con %s@%s", username, host)
            raise ConnectionError(str(exc)) from exc

        self._ssh_client = ssh_client
        self._sftp_client = sftp_client
        self._details = ConnectionDetails(host=host, username=username, auth_method=auth_method)
        self._logger.info("Conexión abierta con %s@%s (%s)", username, host, auth_method)
        return self._details

    def disconnect(self) -> None:
        if not self.is_connected:
            raise NoActiveConnection("No hay conexión activa que cerrar.")
        assert self._ssh_client
        self._logger.debug(
            "Cerrando conexión SSH con %s@%s",
            self._details.username if self._details else "?",
            self._details.host if self._details else "?",
        )
        try:
            if self._sftp_client:
                self._sftp_client.close()
        finally:
            self._ssh_client.close()
        if self._details:
            self._logger.info(
                "Conexión cerrada con %s@%s",
                self._details.username,
                self._details.host,
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
            return "Sin conexión activa"
        return (
            f"Conectado a {self._details.username}@{self._details.host}"
            f" ({self._details.auth_method})"
        )
