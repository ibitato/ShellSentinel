"""Pruebas para la gestión de permisos de tools."""

from __future__ import annotations

import os

import pytest
from smart_ai_sys_admin.agent.permissions import DEFAULT_PERMISSION_ENV_FLAGS, ToolPermissionManager


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch):
    """Garantiza que las variables de entorno usadas en las pruebas queden limpias."""

    originals = {key: os.environ.get(key) for key in DEFAULT_PERMISSION_ENV_FLAGS}
    for key in DEFAULT_PERMISSION_ENV_FLAGS:
        monkeypatch.delenv(key, raising=False)
    yield
    for key, value in originals.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_permission_manager_activate_sets_flags():
    manager = ToolPermissionManager()

    manager.activate()

    for key, value in DEFAULT_PERMISSION_ENV_FLAGS.items():
        assert os.environ.get(key) == value
    assert manager.active is True


def test_permission_manager_restore_returns_previous_values(monkeypatch: pytest.MonkeyPatch):
    manager = ToolPermissionManager()
    monkeypatch.setenv("BYPASS_TOOL_CONSENT", "custom")

    manager.activate()
    manager.restore()

    assert os.environ.get("BYPASS_TOOL_CONSENT") == "custom"
    for key in DEFAULT_PERMISSION_ENV_FLAGS:
        if key == "BYPASS_TOOL_CONSENT":
            continue
        assert os.environ.get(key) is None
    assert manager.active is False


def test_permission_manager_activate_is_idempotent():
    manager = ToolPermissionManager()
    manager.activate()
    manager.activate()
    assert manager.active is True


def test_permission_manager_restore_without_activate_is_noop():
    manager = ToolPermissionManager()
    manager.restore()
    assert manager.active is False


def test_permission_manager_custom_flags():
    manager = ToolPermissionManager({"CUSTOM_FLAG": "1"})
    manager.activate()
    assert os.environ.get("CUSTOM_FLAG") == "1"
    manager.restore()
    assert os.environ.get("CUSTOM_FLAG") is None
