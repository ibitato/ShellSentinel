"""Pruebas para el módulo de localización."""

from __future__ import annotations

import pytest
from smart_ai_sys_admin.localization import (
    _,
    detect_locale,
    get_localizer,
    localize_placeholders,
    register_plugin_translations,
    reset_localizer,
)


def test_detect_locale_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_LOCALE", "es_ES")
    assert detect_locale() == "es-ES"


def test_get_existing_translation():
    reset_localizer("en")
    value = _("ui.output_panel.title")
    assert isinstance(value, str)
    assert value


def test_missing_key_returns_key():
    reset_localizer("en")
    assert _("nonexistent.key.path") == "nonexistent.key.path"


def test_localize_placeholders_string():
    reset_localizer("en")
    result = localize_placeholders("{{ui.output_panel.title}}")
    assert result != "{{ui.output_panel.title}}"


def test_localize_placeholders_nested_dict():
    reset_localizer("en")
    payload = {"title": "{{ui.output_panel.title}}", "plain": "ok"}
    result = localize_placeholders(payload)
    assert result["plain"] == "ok"
    assert "{{" not in result["title"]


def test_register_plugin_translations_merges():
    reset_localizer("en")
    register_plugin_translations(
        "en",
        {"plugins": {"demo": {"description": "Demo plugin"}}},
    )
    localizer = get_localizer()
    assert localizer.get("plugins.demo.description") == "Demo plugin"


def test_reset_localizer_switches_locale(monkeypatch: pytest.MonkeyPatch):
    reset_localizer("de")
    localizer = get_localizer()
    assert localizer.active_locale == "de"


def test_format_kwargs():
    reset_localizer("en")
    text = _("connection.status.connected", username="alice", host="h", port=22, method="key")
    assert "alice" in text
    assert "h" in text
