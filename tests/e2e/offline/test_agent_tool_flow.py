"""E2E offline: el agente Strands real ejecuta ``remote_ssh_command`` desde el TUI."""

from __future__ import annotations

import asyncio
import time

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.ssh_server import CommandResult, ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline

HARDWARE_PROMPT = "dame las características hardware de este servidor"
CUSTOM_TOOLS = {"local_datetime", "remote_ssh_command", "remote_sftp_transfer"}


def _tool_result_text(result: dict) -> str:
    return "\n".join(block.get("text", "") for block in result.get("content", []))


async def test_prompt_runs_remote_command_and_renders_answer(
    tui, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    ssh.script["uname -a"] = CommandResult(0, "Linux fake 6.1 x86_64\n")
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "uname -a"}),
        text_turn(
            "Kernel: **Linux fake 6.1**",
            usage={
                "inputTokens": 100,
                "outputTokens": 7,
                "totalTokens": 107,
                "cacheReadInputTokens": 80,
            },
        ),
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        reply = await driver.submit(HARDWARE_PROMPT)

        assert reply == "Kernel: **Linux fake 6.1**"
        assert ssh.recorded_commands == ["uname -a"]
        assert len(scripted_model.calls) == 2
        first_call = scripted_model.calls[0]
        assert CUSTOM_TOOLS <= set(first_call.tool_names)
        assert "shell" not in first_call.tool_names
        assert "You are a test system prompt" in (first_call.system_prompt or "")

        results = scripted_model.calls[1].tool_results()
        assert len(results) == 1
        assert results[0]["toolUseId"] == "tu-1"
        assert results[0]["status"] == "success"
        text = _tool_result_text(results[0])
        assert _("agent.tools.summary.exit_code", code=0) in text
        assert f"{_('agent.tools.summary.stdout')}\nLinux fake 6.1 x86_64" in text

        assert driver.user_messages()[-1] == HARDWARE_PROMPT
        assert _("connection.status.thinking") not in driver.footer()

        status = await driver.submit("/status")
        assert (
            _("ui.commands.status.cache_usage", cached=80, total=110, percent=73, written=0)
            in status
        )


async def test_nonzero_exit_and_stderr_reach_model(
    tui, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    ssh.script["false"] = CommandResult(1, "", "boom\n")
    scripted_model.enqueue(tool_turn("remote_ssh_command", {"command": "false"}), text_turn("done"))

    async with tui() as driver:
        await driver.submit(connect_line)
        await driver.submit("ejecuta false")

        text = _tool_result_text(scripted_model.tool_results()[0])
        assert _("agent.tools.summary.exit_code", code=1) in text
        assert f"{_('agent.tools.summary.stderr')}\nboom" in text


async def test_long_output_is_truncated_for_model(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    write_agent_conf(e2e_env.conf_dir, max_output_chars=500)
    ssh.script["cat big.log"] = CommandResult(0, "x" * 2000)
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "cat big.log"}), text_turn("ok")
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        await driver.submit("muestra el log")

        text = _tool_result_text(scripted_model.tool_results()[0])
        assert _("agent.tools.summary.stdout_truncated", limit=500) in text
        assert _("agent.tools.summary.stdout_preview") in text
        assert "x" * 2000 not in text


async def test_tool_timeout_is_reported_and_session_survives(
    tui, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    ssh.script["sleep 3"] = CommandResult(0, "late\n", delay=3.0)
    ssh.script["uname -a"] = CommandResult(0, "Linux fake\n")
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "sleep 3", "timeout_seconds": 1}),
        text_turn("timed out"),
        tool_turn("remote_ssh_command", {"command": "uname -a"}, tool_use_id="tu-2"),
        text_turn("recovered"),
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        started = time.monotonic()
        reply = await driver.submit("tarda mucho")
        assert time.monotonic() - started < 2.5
        assert reply == "timed out"

        text = _tool_result_text(scripted_model.tool_results()[0])
        assert text.startswith("❌")
        assert _("connection.errors.command_timeout", command="sleep 3", timeout=1) in text
        assert driver.connection.is_connected

        reply = await driver.submit("y ahora el kernel")
        assert reply == "recovered"
        assert ssh.recorded_commands == ["sleep 3", "uname -a"]


async def test_prompt_without_connection_tells_model_ssh_inactive(
    tui, ssh: ScriptedSSHServer, scripted_model: ScriptedModel
):
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "uname -a"}), text_turn("no ssh")
    )

    async with tui() as driver:
        reply = await driver.submit("dame el kernel")

        assert reply == "no ssh"
        text = _tool_result_text(scripted_model.tool_results()[0])
        assert text == _("agent.tools.ssh_inactive")
        assert ssh.recorded_commands == []


async def test_model_failure_renders_error_and_app_stays_responsive(
    tui, scripted_model: ScriptedModel
):
    scripted_model.raise_on_exhausted = RuntimeError("provider exploded")

    async with tui() as driver:
        reply = await driver.submit("hola")

        assert reply.startswith("❌ El agente falló al procesar la instrucción")
        assert "provider exploded" in reply
        assert driver.app._busy is False

        reply = await driver.submit("/help")
        assert "/connect" in reply


async def test_busy_guard_and_thinking_indicator(
    tui, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    ssh.script["sleep 1"] = CommandResult(0, "slow\n", delay=1.0)
    scripted_model.enqueue(
        tool_turn("remote_ssh_command", {"command": "sleep 1"}), text_turn("slow done")
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        await driver.start_submit("tarda un poco")
        await asyncio.sleep(0.3)

        assert driver.app._busy is True
        assert driver.footer().endswith(_("connection.status.thinking"))

        await driver.start_submit("segunda petición")
        await asyncio.sleep(0.1)
        assert driver.last_agent() == _("ui.app.busy")

        await driver.wait_idle()
        assert driver.last_agent() == "slow done"
        assert len(scripted_model.calls) == 2
        assert _("connection.status.thinking") not in driver.footer()
