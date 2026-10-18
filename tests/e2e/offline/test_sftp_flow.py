"""E2E offline: transferencias SFTP a través de ``remote_sftp_transfer`` desde el TUI."""

from __future__ import annotations

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.ssh_server import ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline


def _tool_result_text(result: dict) -> str:
    return "\n".join(block.get("text", "") for block in result.get("content", []))


async def test_upload_then_download_via_tool(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    assert ssh.sftp_root is not None
    source = e2e_env.tmp_path / "report.txt"
    source.write_text("informe e2e\nlínea 2\n", encoding="utf-8")
    target = e2e_env.tmp_path / "back.txt"
    scripted_model.enqueue(
        tool_turn(
            "remote_sftp_transfer",
            {"action": "upload", "local_path": str(source), "remote_path": "/inbox/report.txt"},
        ),
        tool_turn(
            "remote_sftp_transfer",
            {"action": "download", "remote_path": "/inbox/report.txt", "local_path": str(target)},
            tool_use_id="tu-2",
        ),
        text_turn("transfer complete"),
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        reply = await driver.submit("sube el informe y vuelve a bajarlo")

        assert reply == "transfer complete"
        remote_copy = ssh.sftp_root / "inbox" / "report.txt"
        assert remote_copy.read_bytes() == source.read_bytes()
        assert target.read_bytes() == source.read_bytes()
        results = [_tool_result_text(result) for result in scripted_model.tool_results()]
        assert (
            _("agent.tools.transfer.upload_success", local=str(source), remote="/inbox/report.txt")
            in results
        )
        assert any(text.startswith("✅ Download completed.") for text in results)
        assert ssh.recorded_commands == []


async def test_upload_without_overwrite_fails(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    assert ssh.sftp_root is not None
    source = e2e_env.tmp_path / "dup.txt"
    source.write_text("v1", encoding="utf-8")
    (ssh.sftp_root / "dup.txt").write_text("existing", encoding="utf-8")
    scripted_model.enqueue(
        tool_turn(
            "remote_sftp_transfer",
            {"action": "upload", "local_path": str(source), "remote_path": "/dup.txt"},
        ),
        text_turn("refused"),
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        await driver.submit("sube dup.txt")

        text = _tool_result_text(scripted_model.tool_results()[0])
        assert _("connection.errors.remote_exists", path="/dup.txt") in text
        assert (ssh.sftp_root / "dup.txt").read_text(encoding="utf-8") == "existing"
