"""Punto de entrada de la interfaz de línea de comandos del asistente."""

from __future__ import annotations

import warnings

from .config import CONFIG
from .logging_setup import configure_logging
from .ui import run_app

try:  # pragma: no cover - depende de cryptography instalada.
    from cryptography.utils import CryptographyDeprecationWarning
except ModuleNotFoundError:  # pragma: no cover - fallback si falta cryptography.
    CryptographyDeprecationWarning = None


def main() -> int:
    """Ejecuta la interfaz de terminal del administrador inteligente."""
    configure_logging(CONFIG.logging)
    if CryptographyDeprecationWarning:
        warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
    warnings.filterwarnings("ignore", module="paramiko")
    # Strands 1.61 deja una corrutina sin esperar al cerrar un cliente MCP que no llegó a
    # arrancar; es inofensivo y el fallo real ya se informa en la TUI.
    warnings.filterwarnings(
        "ignore",
        message=r"coroutine 'MCPClient\.stop\.<locals>\._set_close_event' was never awaited",
        category=RuntimeWarning,
    )
    run_app(config=CONFIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
