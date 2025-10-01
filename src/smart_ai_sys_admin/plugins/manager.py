"""Carga dinámica de plugins."""

from __future__ import annotations

import importlib.util
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

from ..localization import register_plugin_translations
from .registry import PluginRegistry
from .types import PluginSlashCommand

LOGGER = logging.getLogger("smart_ai_sys_admin.plugins")

PLUGINS_DIR_ENV = "SMART_AI_SYS_ADMIN_PLUGINS_DIR"


class PluginManager:
    """Descubre, importa y registra plugins externos."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or LOGGER
        self._commands: list[PluginSlashCommand] = []

    @property
    def commands(self) -> Iterable[PluginSlashCommand]:
        return tuple(self._commands)

    def load(self) -> None:
        for module_path in self._discover_plugin_modules():
            self._load_module(module_path)

    # ------------------------------------------------------------------
    # Descubrimiento e importación
    # ------------------------------------------------------------------

    def _discover_plugin_modules(self) -> list[Path]:
        search_paths = _plugin_directories()
        module_paths: list[Path] = []
        for directory in search_paths:
            if not directory.is_dir():
                continue
            for entry in sorted(directory.glob("*.py")):
                if entry.name.startswith("_"):
                    continue
                module_paths.append(entry)
        return module_paths

    def _load_module(self, module_path: Path) -> None:
        module_name = f"smart_ai_sys_admin.plugins.dynamic.{module_path.stem}"
        self._logger.debug("Cargando plugin desde %s", module_path)
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            self._logger.warning("No se pudo crear el spec para %s", module_path)
            return
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - dependiente de plugins externos
            self._logger.exception("Fallo importando plugin %s: %s", module_path, exc)
            return
        self._register_plugin(module)

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def _register_plugin(self, module: ModuleType) -> None:
        register = getattr(module, "register", None)
        if not callable(register):
            self._logger.debug(
                "El módulo %s no expone una función register(registry)", module.__name__
            )
            return
        registry = PluginRegistry()
        try:
            register(registry)
        except Exception as exc:  # pragma: no cover - depende del plugin
            self._logger.exception(
                "El plugin %s falló durante register(): %s", module.__name__, exc
            )
            return
        for command in registry.commands:
            self._commands.append(command)
        for locale, translations in registry.translations.items():
            for payload in translations:
                register_plugin_translations(locale, payload)
        self._logger.info(
            "Plugin '%s' registrado con %d comandos",
            module.__name__,
            len(tuple(registry.commands)),
        )


def _plugin_directories() -> list[Path]:
    env_value = os.environ.get(PLUGINS_DIR_ENV)
    if env_value:
        return [Path(part).expanduser() for part in env_value.split(os.pathsep) if part.strip()]
    root = Path(__file__).resolve().parents[3]
    return [root / "plugins"]
