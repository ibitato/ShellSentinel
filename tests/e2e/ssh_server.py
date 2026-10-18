"""Servidor SSH/SFTP embebido con respuestas guionizadas para las pruebas e2e.

Arranca un ``paramiko.Transport`` en ``127.0.0.1`` con un puerto efímero, acepta
autenticación por contraseña, responde a peticiones ``exec`` con un guion de
comandos y expone un subsistema SFTP enjaulado en un directorio temporal. No
ejecuta nada en el host: es determinista y funciona igual en CI, en el contenedor
python:3.12 y en Windows.
"""

from __future__ import annotations

import os
import re
import shlex
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import paramiko
from paramiko import (
    AUTH_FAILED,
    AUTH_SUCCESSFUL,
    OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
    OPEN_SUCCEEDED,
    SFTP_OK,
    SFTPAttributes,
    SFTPHandle,
    SFTPServer,
    SFTPServerInterface,
)

E2E_USERNAME = "tester"
# No debe coincidir con una ruta existente: ``/connect`` trata una ruta como clave privada.
E2E_PASSWORD = "s3cr3t-e2e"

# Centinelas únicos presentes en las salidas enlatadas del perfil de hardware. Las
# pruebas live buscan estos textos en la respuesta del modelo.
SENTINEL_HOSTNAME = "sentinel-e2e-host"
SENTINEL_CPU_MODEL = "Sentinel Virtual CPU E2E-9000"
SENTINEL_KERNEL = "6.8.0-e2e-sentinel"
SENTINEL_ROOT_FS = "/dev/sentinel-root"


@dataclass(frozen=True)
class CommandResult:
    """Respuesta guionizada para un comando remoto."""

    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    delay: float = 0.0


Responder = CommandResult | Callable[[str], CommandResult]

# Margen para que el cliente reciba la confirmación del exec antes de que llegue la salida.
EXEC_REPLY_GRACE_SECONDS = 0.05

_COMPOUND_SPLIT = re.compile(r"\s*(?:;|&&|\|\|)\s*")


def split_compound(command: str) -> list[str]:
    """Divide un comando compuesto (``;``, ``&&``, ``||``) en segmentos no vacíos."""

    return [segment for segment in _COMPOUND_SPLIT.split(command.strip()) if segment]


def _echo_responder(command: str) -> CommandResult:
    try:
        words = shlex.split(command)[1:]
    except ValueError:
        words = command.split()[1:]
    words = [word for word in words if not word.startswith("-")]
    return CommandResult(0, " ".join(words) + "\n")


HARDWARE_PROFILE: list[tuple[str, Responder]] = [
    (r"^echo\b", _echo_responder),
    (
        r"^uname\b|/proc/version",
        CommandResult(
            0,
            f"Linux {SENTINEL_HOSTNAME} {SENTINEL_KERNEL} #1 SMP x86_64 GNU/Linux\n",
        ),
    ),
    (r"^hostname\b|^hostnamectl\b", CommandResult(0, f"{SENTINEL_HOSTNAME}\n")),
    (
        r"^lscpu\b|/proc/cpuinfo",
        CommandResult(
            0,
            "Architecture:        x86_64\n"
            "CPU(s):              4\n"
            f"Model name:          {SENTINEL_CPU_MODEL}\n"
            "Thread(s) per core:  2\n"
            "Core(s) per socket:  2\n",
        ),
    ),
    (r"^nproc\b", CommandResult(0, "4\n")),
    (
        r"^free\b|/proc/meminfo",
        CommandResult(
            0,
            "               total        used        free\n"
            "Mem:            7937        1203        6734\n"
            "Swap:           2047           0        2047\n",
        ),
    ),
    (
        r"^df\b",
        CommandResult(
            0,
            "Filesystem          Size  Used Avail Use% Mounted on\n"
            f"{SENTINEL_ROOT_FS}   40G   12G   28G  30% /\n",
        ),
    ),
    (
        r"^lsblk\b",
        CommandResult(
            0,
            "NAME      SIZE MODEL                 TYPE\n"
            "sda        40G Sentinel Virtual Disk disk\n",
        ),
    ),
    (
        r"os-release|^lsb_release\b",
        CommandResult(0, 'PRETTY_NAME="Sentinel Linux 1.0 (e2e)"\nID=sentinel\n'),
    ),
    (
        r"^dmidecode\b",
        CommandResult(0, f"Manufacturer: Sentinel Labs\nProduct Name: {SENTINEL_HOSTNAME}\n"),
    ),
    (
        r"^uptime\b",
        CommandResult(0, " 10:00:00 up 3 days,  2:11,  1 user,  load average: 0.10, 0.08, 0.05\n"),
    ),
]


class _Server(paramiko.ServerInterface):
    """Política del servidor: sesiones ``exec`` y autenticación por contraseña."""

    def __init__(self, owner: ScriptedSSHServer) -> None:
        super().__init__()
        self._owner = owner

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == "session":
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_auth_password(self, username: str, password: str) -> int:
        if (username, password) == (self._owner.username, self._owner.password):
            return AUTH_SUCCESSFUL
        return AUTH_FAILED

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes | str) -> bool:
        # paramiko 5 entrega el comando como bytes.
        text = command.decode("utf-8", "replace") if isinstance(command, bytes) else command
        self._owner.recorded_commands.append(text)
        threading.Thread(
            target=self._owner._run_exec, args=(channel, text), daemon=True, name="e2e-ssh-exec"
        ).start()
        return True


class _RootedHandle(SFTPHandle):
    """Handle de fichero SFTP respaldado por un fichero real bajo la raíz enjaulada."""

    def __init__(self, flags: int, path: Path, fileobj) -> None:  # type: ignore[no-untyped-def]
        super().__init__(flags)
        self._path = path
        self.readfile = fileobj
        self.writefile = fileobj

    def stat(self):  # type: ignore[no-untyped-def]
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)

    def chattr(self, attr):  # type: ignore[no-untyped-def]
        return SFTP_OK


class _RootedSFTPServer(SFTPServerInterface):
    """SFTP mínimo enjaulado en ``root``: suficiente para upload/download del proyecto."""

    def __init__(self, server: paramiko.ServerInterface, root: Path, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(server, *args, **kwargs)
        self._root = root

    def _real(self, path: str) -> Path:
        parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".", "..")]
        return self._root.joinpath(*parts)

    def canonicalize(self, path: str) -> str:
        parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".", "..")]
        return "/" + "/".join(parts)

    def stat(self, path: str):  # type: ignore[no-untyped-def]
        try:
            return SFTPAttributes.from_stat(os.stat(self._real(path)))
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)

    lstat = stat

    def list_folder(self, path: str):  # type: ignore[no-untyped-def]
        try:
            entries = []
            for child in self._real(path).iterdir():
                attr = SFTPAttributes.from_stat(os.stat(child))
                attr.filename = child.name
                entries.append(attr)
            return entries
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)

    def mkdir(self, path: str, attr):  # type: ignore[no-untyped-def]
        try:
            self._real(path).mkdir()
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)
        return SFTP_OK

    def rmdir(self, path: str):  # type: ignore[no-untyped-def]
        try:
            self._real(path).rmdir()
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)
        return SFTP_OK

    def remove(self, path: str):  # type: ignore[no-untyped-def]
        try:
            self._real(path).unlink()
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)
        return SFTP_OK

    def rename(self, oldpath: str, newpath: str):  # type: ignore[no-untyped-def]
        try:
            self._real(oldpath).rename(self._real(newpath))
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)
        return SFTP_OK

    def chattr(self, path: str, attr):  # type: ignore[no-untyped-def]
        return SFTP_OK

    def open(self, path: str, flags: int, attr):  # type: ignore[no-untyped-def]
        real = self._real(path)
        flags |= getattr(os, "O_BINARY", 0)
        try:
            fd = os.open(real, flags, 0o666)
        except OSError as exc:
            return SFTPServer.convert_errno(exc.errno)
        if flags & os.O_WRONLY:
            mode = "ab" if flags & os.O_APPEND else "wb"
        elif flags & os.O_RDWR:
            mode = "a+b" if flags & os.O_APPEND else "r+b"
        else:
            mode = "rb"
        fileobj = os.fdopen(fd, mode)
        return _RootedHandle(flags, real, fileobj)


class ScriptedSSHServer:
    """Servidor SSH en proceso con guion de comandos y SFTP enjaulado."""

    def __init__(
        self,
        *,
        username: str = E2E_USERNAME,
        password: str = E2E_PASSWORD,
        sftp_root: Path | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.sftp_root = sftp_root
        self.host = "127.0.0.1"
        self.port = 0
        self.recorded_commands: list[str] = []
        self.script: dict[str, Responder] = {}
        self.patterns: list[tuple[re.Pattern[str], Responder]] = []
        self.default: Responder = self._command_not_found
        self._host_key = paramiko.ECDSAKey.generate()
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._transports: list[paramiko.Transport] = []
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------ ciclo de vida
    def start(self) -> ScriptedSSHServer:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, 0))
        sock.listen(8)
        self.port = sock.getsockname()[1]
        self._sock = sock
        self._running = True
        self._thread = threading.Thread(
            target=self._accept_loop, daemon=True, name="e2e-ssh-accept"
        )
        self._thread.start()
        return self

    def stop(self) -> None:
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        with self._lock:
            transports = list(self._transports)
            self._transports.clear()
        for transport in transports:
            try:
                transport.close()
            except Exception:  # pragma: no cover - cierre defensivo
                pass
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def reset(self) -> None:
        """Limpia guion, patrones y comandos registrados entre pruebas."""

        self.recorded_commands.clear()
        self.script.clear()
        self.patterns.clear()
        self.default = self._command_not_found

    # ------------------------------------------------------------------ guion
    def add_pattern(self, regex: str, responder: Responder) -> None:
        self.patterns.append((re.compile(regex), responder))

    def load_hardware_profile(self) -> None:
        """Registra salidas enlatadas de inventario de hardware con centinelas únicos."""

        for regex, responder in HARDWARE_PROFILE:
            self.add_pattern(regex, responder)

    @staticmethod
    def _command_not_found(command: str) -> CommandResult:
        return CommandResult(127, "", f"sh: {command}: command not found\n")

    @staticmethod
    def _call(responder: Responder, command: str) -> CommandResult:
        return responder(command) if callable(responder) else responder

    def _match_segment(self, segment: str) -> CommandResult | None:
        exact = self.script.get(segment)
        if exact is not None:
            return self._call(exact, segment)
        for pattern, responder in self.patterns:
            if pattern.search(segment):
                return self._call(responder, segment)
        return None

    def resolve(self, command: str) -> CommandResult:
        """Resuelve un comando (simple o compuesto) contra el guion."""

        exact = self.script.get(command)
        if exact is not None:
            return self._call(exact, command)
        results = [self._match_segment(segment) for segment in split_compound(command)]
        matched = [result for result in results if result is not None]
        if not matched:
            return self._call(self.default, command)
        exit_code = next((result.exit_code for result in matched if result.exit_code), 0)
        return CommandResult(
            exit_code=exit_code,
            stdout="".join(result.stdout for result in matched),
            stderr="".join(result.stderr for result in matched),
            delay=sum(result.delay for result in matched),
        )

    # ------------------------------------------------------------------ red
    def _accept_loop(self) -> None:
        assert self._sock is not None
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            try:
                transport = paramiko.Transport(conn)
                transport.add_server_key(self._host_key)
                if self.sftp_root is not None:
                    transport.set_subsystem_handler(
                        "sftp", SFTPServer, _RootedSFTPServer, self.sftp_root
                    )
                transport.start_server(server=_Server(self))
            except Exception:  # pragma: no cover - cliente mal formado
                conn.close()
                continue
            with self._lock:
                self._transports.append(transport)

    def _run_exec(self, channel: paramiko.Channel, command: str) -> None:
        result = self.resolve(command)
        try:
            # paramiko envía MSG_CHANNEL_SUCCESS al volver de check_channel_exec_request; si el
            # canal se cierra antes, el cliente ve "Channel closed." en exec_command.
            time.sleep(EXEC_REPLY_GRACE_SECONDS)
            if result.delay:
                time.sleep(result.delay)
            if result.stdout:
                channel.sendall(result.stdout.encode("utf-8"))
            if result.stderr:
                channel.sendall_stderr(result.stderr.encode("utf-8"))
            channel.send_exit_status(result.exit_code)
        except Exception:  # pragma: no cover - el cliente pudo cerrar el canal (timeout)
            pass
        finally:
            try:
                channel.close()
            except Exception:  # pragma: no cover - cierre defensivo
                pass


__all__ = [
    "E2E_PASSWORD",
    "E2E_USERNAME",
    "HARDWARE_PROFILE",
    "SENTINEL_CPU_MODEL",
    "SENTINEL_HOSTNAME",
    "SENTINEL_KERNEL",
    "SENTINEL_ROOT_FS",
    "CommandResult",
    "ScriptedSSHServer",
    "split_compound",
]
