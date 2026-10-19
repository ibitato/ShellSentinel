"""Servidor MCP con guion para las pruebas e2e (se lanza como subproceso ``stdio``).

Expone un puñado de tools deterministas sobre el SDK ``mcp`` 2.x (``MCPServer``) y, según
``--mode``, reproduce los fallos de arranque que Shell Sentinel debe diagnosticar:

- ``normal``: sirve las tools ``echo``, ``add``, ``env_value``, ``fail`` y ``crash``.
- ``exit``: termina con código 3 antes del saludo MCP (``process_exited``).
- ``hang``: no responde nunca al saludo (``timeout``).
- ``slow``: espera ``--delay`` segundos antes de servir (arranque lento pero válido).

``--pid-file`` escribe el PID del proceso para que la prueba compruebe que Shell Sentinel lo
cierra al apagar el runtime. No depende de ``smart_ai_sys_admin``: solo necesita ``mcp``.
"""

from __future__ import annotations

import argparse
import os
import sys
import time


def _write_pid(path: str | None) -> None:
    if path:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))


def build_server(name: str):  # type: ignore[no-untyped-def]
    """Construye el ``MCPServer`` con las tools de prueba (import diferido: ``exit``/``hang``
    no deben depender de que el SDK cargue)."""

    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError

    # CRITICAL: el SDK registra cada crash de tool con un traceback que ensuciaría pytest.
    server = MCPServer(name, log_level="CRITICAL")

    @server.tool(description="Devuelve el texto recibido con el prefijo 'echo: '.")
    def echo(text: str) -> str:
        return f"echo: {text}"

    @server.tool(description="Suma dos enteros.")
    def add(a: int, b: int) -> int:
        return a + b

    @server.tool(description="Valor de una variable de entorno del proceso del servidor.")
    def env_value(name: str) -> str:
        return os.environ.get(name, "<unset>")

    @server.tool(description="Falla de forma declarada: el mensaje llega al cliente.")
    def fail(message: str) -> str:
        raise ToolError(message)

    @server.tool(description="Revienta con una excepción no prevista: el detalle no sale.")
    def crash(secret: str) -> str:
        raise RuntimeError(f"crash with {secret}")

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("normal", "exit", "hang", "slow"), default="normal")
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--name", default="e2e-scripted-mcp")
    parser.add_argument("--pid-file", default=None)
    args = parser.parse_args(argv)

    _write_pid(args.pid_file)

    if args.mode == "exit":
        print("e2e mcp server: exiting on purpose", file=sys.stderr, flush=True)
        return 3
    if args.mode == "hang":
        # Sin leer stdin ni escribir nada: el cliente nunca recibe la respuesta al saludo.
        time.sleep(3600)
        return 0
    if args.mode == "slow" and args.delay > 0:
        time.sleep(args.delay)

    build_server(args.name).run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
