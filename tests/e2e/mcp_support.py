"""Utilidades MCP para las pruebas e2e: transportes de prueba, servidor HTTP de estado fijo y
comprobaciones de procesos.

Los transportes se devuelven como diccionarios listos para el bloque ``mcp.transports`` de
``agent.conf`` (``write_agent_conf(..., mcp={"transports": [...]})``).
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

SCRIPTED_MCP_SERVER = Path(__file__).with_name("mcp_server.py")

FIRECRAWL_KEY_ENV = "FIRECRAWL_API_KEY"
FIRECRAWL_PACKAGE = "firecrawl-mcp"
# Variables de proxy que el subproceso de ``npx`` necesita heredar en redes corporativas.
PROXY_ENV_VARS = ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy")


# ---------------------------------------------------------------------- transportes
def scripted_mcp_transport(
    identifier: str = "e2e-stdio",
    *,
    mode: str = "normal",
    delay: float = 0.0,
    pid_file: Path | None = None,
    env: Mapping[str, str] | None = None,
    env_passthrough: Sequence[str] = (),
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """Transporte ``stdio`` que lanza ``tests/e2e/mcp_server.py`` con el intérprete actual."""

    args = ["-u", str(SCRIPTED_MCP_SERVER), "--mode", mode, "--name", identifier]
    if delay:
        args += ["--delay", str(delay)]
    if pid_file is not None:
        args += ["--pid-file", str(pid_file)]
    return {
        "id": identifier,
        "type": "stdio",
        "command": sys.executable,
        "args": args,
        "env": dict(env or {}),
        "env_passthrough": list(env_passthrough),
        "cwd": None,
        "timeout_seconds": timeout_seconds,
    }


def missing_command_transport(identifier: str = "missing-cmd") -> dict[str, Any]:
    return {
        "id": identifier,
        "type": "stdio",
        "command": "shell-sentinel-e2e-no-such-command",
        "args": [],
        "env": {},
        "env_passthrough": [],
        "cwd": None,
        "timeout_seconds": 10,
    }


def http_transport(
    identifier: str,
    url: str,
    *,
    transport_type: str = "streamable_http",
    timeout_seconds: int = 5,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "type": transport_type,
        "url": url,
        "headers": dict(headers or {}),
        "timeout_seconds": timeout_seconds,
    }


def firecrawl_transport(
    identifier: str = "firecrawl-stdio", *, timeout_seconds: int = 120
) -> dict[str, Any]:
    """Transporte real de Firecrawl: ``npx -y firecrawl-mcp`` con la clave y el proxy heredados.

    ``timeout_seconds`` es generoso porque la primera ejecución descarga el paquete.
    """

    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx no está en PATH; instala Node.js para las pruebas MCP live")
    return {
        "id": identifier,
        "type": "stdio",
        "command": npx,
        "args": ["-y", FIRECRAWL_PACKAGE],
        "env": {"NODE_USE_ENV_PROXY": "1"},
        "env_passthrough": [FIRECRAWL_KEY_ENV, *PROXY_ENV_VARS],
        "cwd": None,
        "timeout_seconds": timeout_seconds,
    }


def firecrawl_unavailable_reason(env: Mapping[str, str] | None = None) -> str | None:
    """``None`` si se puede ejecutar Firecrawl; si no, el motivo para saltar la prueba."""

    env = os.environ if env is None else env
    if not env.get(FIRECRAWL_KEY_ENV):
        return f"{FIRECRAWL_KEY_ENV} no está definida"
    if shutil.which("npx") is None:
        return "npx (Node.js) no está en PATH"
    return None


# ---------------------------------------------------------------------- servidor HTTP
class _FixedStatusHandler(BaseHTTPRequestHandler):
    status_code = 500
    server_version = "ShellSentinelE2E/1.0"

    def _reply(self) -> None:
        self.server.requests.append((self.command, self.path))  # type: ignore[attr-defined]
        body = b'{"error": "e2e fixed status"}'
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if self.status_code == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="e2e"')
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_DELETE = do_OPTIONS = _reply

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - firma de la stdlib
        return


class FixedStatusHTTPServer:
    """Servidor HTTP local que responde siempre con el mismo código (401, 404, 500...)."""

    def __init__(self, status_code: int) -> None:
        handler = type(
            f"Status{status_code}Handler", (_FixedStatusHandler,), {"status_code": status_code}
        )
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._server.requests = []  # type: ignore[attr-defined]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name=f"e2e-http-{status_code}", daemon=True
        )
        self.status_code = status_code

    def start(self) -> FixedStatusHTTPServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    @property
    def requests(self) -> list[tuple[str, str]]:
        return list(self._server.requests)  # type: ignore[attr-defined]

    def url(self, path: str = "/mcp") -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}{path}"


def closed_port_url(path: str = "/mcp") -> str:
    """URL local a un puerto que nadie escucha (conexión rechazada)."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}{path}"


# ---------------------------------------------------------------------- procesos
def read_pid(path: Path, timeout: float = 15.0) -> int:
    """Espera a que el servidor escriba su PID y lo devuelve."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return int(text)
        time.sleep(0.05)
    raise TimeoutError(f"el servidor MCP no escribió su PID en {path}")


def process_alive(pid: int) -> bool:
    if os.name == "nt":  # pragma: no cover - solo en estaciones Windows
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Un zombi sigue respondiendo a la señal 0: se intenta recoger su estado.
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
        return waited == 0
    except ChildProcessError:
        return True


def wait_for_process_exit(pid: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return True
        time.sleep(0.05)
    return not process_alive(pid)


__all__ = [
    "FIRECRAWL_KEY_ENV",
    "FIRECRAWL_PACKAGE",
    "PROXY_ENV_VARS",
    "SCRIPTED_MCP_SERVER",
    "FixedStatusHTTPServer",
    "closed_port_url",
    "firecrawl_transport",
    "firecrawl_unavailable_reason",
    "http_transport",
    "missing_command_transport",
    "process_alive",
    "read_pid",
    "scripted_mcp_transport",
    "wait_for_process_exit",
]
