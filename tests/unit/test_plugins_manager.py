"""Pruebas para el framework de plugins."""

from __future__ import annotations

import os
import textwrap

import pytest
from smart_ai_sys_admin.plugins.manager import PluginManager
from smart_ai_sys_admin.plugins.registry import PluginRegistry
from smart_ai_sys_admin.plugins.types import PluginSlashCommand


def test_registry_stores_commands_and_translations():
    registry = PluginRegistry()
    command = PluginSlashCommand(name="/demo", handler=lambda args: "ok")
    registry.register_command(command)
    registry.register_translations("en", {"plugins": {"demo": {"description": "Demo"}}})
    assert list(registry.commands)[0].name == "/demo"
    assert "en" in registry.translations


def test_plugin_command_iter_aliases():
    command = PluginSlashCommand(name="/demo", aliases=("/d",), handler=lambda args: "ok")
    aliases = list(command.iter_aliases())
    assert "/demo" in aliases
    assert "/d" in aliases


def test_plugin_manager_loads_register_function(tmp_path, monkeypatch: pytest.MonkeyPatch):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    plugin_file = plugin_dir / "sample.py"
    plugin_file.write_text(
        textwrap.dedent(
            """
            from smart_ai_sys_admin.plugins.types import PluginSlashCommand

            def register(registry):
                registry.register_command(
                    PluginSlashCommand(
                        name="/sample",
                        handler=lambda args: "sample-ok",
                    )
                )
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_PLUGINS_DIR", str(plugin_dir))
    manager = PluginManager()
    manager.load()
    commands = list(manager.commands)
    assert len(commands) == 1
    assert commands[0].name == "/sample"


def test_plugin_manager_skips_module_without_register(tmp_path):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "empty.py").write_text("VALUE = 1\n", encoding="utf-8")
    manager = PluginManager()
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SMART_AI_SYS_ADMIN_PLUGINS_DIR", str(plugin_dir))
        manager.load()
    assert list(manager.commands) == []


def test_plugin_manager_multiple_paths(tmp_path):
    first = tmp_path / "p1"
    second = tmp_path / "p2"
    first.mkdir()
    second.mkdir()
    (first / "a.py").write_text(
        "def register(r):\n"
        " from smart_ai_sys_admin.plugins.types import PluginSlashCommand\n"
        " r.register_command(PluginSlashCommand(name='/a', handler=lambda args: 'a'))\n",
        encoding="utf-8",
    )
    (second / "b.py").write_text(
        "def register(r):\n"
        " from smart_ai_sys_admin.plugins.types import PluginSlashCommand\n"
        " r.register_command(PluginSlashCommand(name='/b', handler=lambda args: 'b'))\n",
        encoding="utf-8",
    )
    manager = PluginManager()
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SMART_AI_SYS_ADMIN_PLUGINS_DIR", f"{first}{os.pathsep}{second}")
        manager.load()
    names = {cmd.name for cmd in manager.commands}
    assert names == {"/a", "/b"}
