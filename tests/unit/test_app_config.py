"""Pruebas para la carga de app_config.json."""

from __future__ import annotations

from pathlib import Path

import pytest
from smart_ai_sys_admin.config import load_config


def test_load_config_from_fixture(minimal_app_config, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_CONFIG_FILE", str(minimal_app_config))
    config = load_config()
    assert config.ui.history_limit == 50
    assert config.ui.output_panel.title == "Output"
    assert config.logging.log_to_console is False
    assert config.terminal.allowed_terms == ("xterm", "xterm-256color")


def test_load_config_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    missing = tmp_path / "missing.json"
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_CONFIG_FILE", str(missing))
    with pytest.raises(FileNotFoundError):
        load_config()


def test_load_config_from_config_dir(
    minimal_app_config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    target = conf_dir / "app_config.json"
    target.write_text(minimal_app_config.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.delenv("SMART_AI_SYS_ADMIN_CONFIG_FILE", raising=False)
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_CONFIG_DIR", str(conf_dir))
    config = load_config()
    assert config.ui.input_widget.submit_binding == "ctrl+s"
