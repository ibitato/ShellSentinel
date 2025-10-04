"""Gestión de permisos para herramientas Strands.

Este módulo centraliza los ajustes de entorno necesarios para conceder permisos
completos a las herramientas registradas en el agente. El objetivo es evitar
confirmaciones interactivas que interrumpan el flujo del agente cuando se
utilizan herramientas que requieren consentimiento explícito.
"""

from __future__ import annotations

import logging
import os
from typing import Mapping

__all__ = ["DEFAULT_PERMISSION_ENV_FLAGS", "ToolPermissionManager"]

# Variables de entorno que habilitan el bypass de confirmaciones dentro de las
# tools empaquetadas en ``strands_tools``.
DEFAULT_PERMISSION_ENV_FLAGS: Mapping[str, str] = {
    "BYPASS_TOOL_CONSENT": "true",
    "STRANDS_NON_INTERACTIVE": "true",
}


class ToolPermissionManager:
    """Administra los permisos de herramientas mediante variables de entorno."""

    def __init__(
        self,
        env_flags: Mapping[str, str] | None = None,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._env_flags: dict[str, str] = dict(env_flags or DEFAULT_PERMISSION_ENV_FLAGS)
        self._logger = logger
        self._previous: dict[str, str | None] = {}
        self._active = False

    def set_logger(self, logger: logging.Logger | None) -> None:
        """Actualiza el logger utilizado para mensajes de depuración."""

        self._logger = logger

    def activate(self) -> None:
        """Aplica los permisos totales a las herramientas.

        Guarda el estado previo de las variables de entorno y establece los
        valores necesarios para omitir solicitudes de consentimiento.
        """

        if self._active:
            return

        self._previous = {key: os.environ.get(key) for key in self._env_flags}
        for key, value in self._env_flags.items():
            os.environ[key] = value
            if self._logger:
                self._logger.debug(
                    "Activando permisos totales para tools: %s=%s", key, value
                )
        self._active = True

    def restore(self) -> None:
        """Restaura los valores originales de las variables de entorno."""

        if not self._active:
            return

        for key, previous_value in self._previous.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
            if self._logger:
                self._logger.debug(
                    "Restaurando permisos de tools: %s vuelve a %r", key, previous_value
                )
        self._previous.clear()
        self._active = False

    @property
    def active(self) -> bool:
        """Indica si los permisos están actualmente activados."""

        return self._active

