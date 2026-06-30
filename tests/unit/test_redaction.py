"""Pruebas de redacción de credenciales."""

from __future__ import annotations

from pathlib import Path

from smart_ai_sys_admin.security import redact_connect_args


def test_redact_connect_args_masks_password():
    assert redact_connect_args(["srv", "alice", "s3cr3t"]) == ["srv", "alice", "***"]


def test_redact_connect_args_preserves_short_lists():
    assert redact_connect_args(["srv", "alice"]) == ["srv", "alice"]


def test_redact_connect_args_keeps_existing_key_path(tmp_path: Path):
    key_file = tmp_path / "id_rsa"
    key_file.write_text("fake-key", encoding="utf-8")
    assert redact_connect_args(["srv", "alice", str(key_file)]) == [
        "srv",
        "alice",
        str(key_file),
    ]
