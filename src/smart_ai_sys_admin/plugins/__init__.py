"""Infraestructura de plugins para Almost Human Sys Admin."""

from .manager import PluginManager
from .registry import PluginRegistry
from .types import PluginSlashCommand

__all__ = [
    "PluginManager",
    "PluginRegistry",
    "PluginSlashCommand",
]
