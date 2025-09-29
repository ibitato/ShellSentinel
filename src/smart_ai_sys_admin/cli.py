"""Punto de entrada de la interfaz de línea de comandos del asistente."""

from __future__ import annotations

from .tui import run_app


def main() -> int:
    """Ejecuta la interfaz de terminal del administrador inteligente."""
    run_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
