"""Registro auxiliar utilizado por los plugins al cargarse."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from .types import PluginSlashCommand


class PluginRegistry:
    """Almacena los artefactos registrados por un plugin."""

    def __init__(self) -> None:
        self._commands: list[PluginSlashCommand] = []
        self._translations: dict[str, list[Mapping[str, Any]]] = defaultdict(list)

    def register_command(self, command: PluginSlashCommand) -> None:
        self._commands.append(command)

    def register_translations(self, locale: str, translations: Mapping[str, Any]) -> None:
        self._translations[locale].append(translations)

    @property
    def commands(self) -> Iterable[PluginSlashCommand]:
        return tuple(self._commands)

    @property
    def translations(self) -> Mapping[str, Iterable[Mapping[str, Any]]]:
        return {locale: tuple(values) for locale, values in self._translations.items()}
