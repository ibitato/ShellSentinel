"""Infraestructura de plugins para Shell Sentinel."""

from .manager import PluginManager
from .registry import PluginRegistry
from .types import PluginSlashCommand

__all__ = [
    "PluginManager",
    "PluginRegistry",
    "PluginSlashCommand",
]
