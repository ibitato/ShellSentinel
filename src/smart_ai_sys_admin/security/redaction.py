"""Redacción de datos sensibles antes de registrarlos o mostrarlos."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

REDACTED_SECRET = "***"


def redact_connect_args(args: Sequence[str]) -> list[str]:
    """Oculta contraseñas SSH en los argumentos de ``/connect``.

    Si el tercer argumento es una ruta a clave privada existente se conserva;
    en caso contrario se asume contraseña y se sustituye por ``***``.
    """

    if len(args) < 3:
        return list(args)
    redacted = list(args)
    secret = redacted[2]
    candidate = Path(secret).expanduser()
    if not candidate.exists():
        redacted[2] = REDACTED_SECRET
    return redacted
