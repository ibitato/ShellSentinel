"""Tipos públicos para la definición de plugins."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

CommandHandler = Callable[[list[str]], str]
SuggestionHandler = Callable[[str, list[str]], str | None]


@dataclass(frozen=True)
class PluginSlashCommand:
    """Describe un comando slash proporcionado por un plugin."""

    name: str
    handler: CommandHandler
    aliases: tuple[str, ...] = ()
    description_key: str | None = None
    usage_key: str | None = None
    help_key: str | None = None
    suggestion: SuggestionHandler | None = None

    def iter_aliases(self) -> Iterable[str]:
        yield self.name
        yield from self.aliases
