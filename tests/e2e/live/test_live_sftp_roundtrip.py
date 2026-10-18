"""E2E live (opcional): subida de un fichero por SFTP pedida en lenguaje natural.

Se activa con ``SHELL_SENTINEL_E2E_SFTP=1`` porque depende de que el modelo elija
``remote_sftp_transfer`` sin pedir confirmación.
"""

from __future__ import annotations

import os

import pytest

from tests.e2e.live.conftest import LiveSession

pytestmark = pytest.mark.skipif(
    os.environ.get("SHELL_SENTINEL_E2E_SFTP") != "1",
    reason="SHELL_SENTINEL_E2E_SFTP=1 activa el escenario SFTP live",
)


async def test_sftp_upload_via_natural_language(connected_live_app: LiveSession, e2e_env):
    session = connected_live_app
    assert session.ssh.sftp_root is not None
    source = e2e_env.tmp_path / "e2e_upload.txt"
    source.write_text("contenido e2e\n", encoding="utf-8")

    reply = await session.ask(
        f"sube el fichero local {source} al servidor en /upload/e2e_upload.txt; "
        "ya está autorizado, no pidas confirmación y confirma cuando termine"
    )

    session.assert_clean_reply(reply)
    uploads = [
        record
        for record in session.guard.tool_uses
        if record.name == "remote_sftp_transfer"
        and str(record.input.get("action", "")).lower() in {"upload", "put"}
    ]
    assert uploads, session.guard.debug_report()
    remote_copy = session.ssh.sftp_root / "upload" / "e2e_upload.txt"
    assert remote_copy.exists(), session.guard.debug_report()
    assert remote_copy.read_bytes() == source.read_bytes()
