"""E2E offline: regresiones de streaming de tool calls hasta la ejecución real por SSH."""

from __future__ import annotations

import logging

import pytest

from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.fake_mistral_sdk import (
    FakeChat,
    install_fake_mistral,
    stream_chunk,
    tool_call_delta,
    usage_info,
)
from tests.e2e.fake_model import ScriptedModel, text_turn, tool_turn
from tests.e2e.ssh_server import CommandResult, ScriptedSSHServer

pytestmark = pytest.mark.e2e_offline


async def test_tool_input_split_across_deltas_executes_once(
    tui, ssh: ScriptedSSHServer, connect_line: str, scripted_model: ScriptedModel
):
    """Contrato Strands: fragmentos de ``toolUse.input`` se recomponen en una sola tool."""

    ssh.script["uname -a"] = CommandResult(0, "Linux fake\n")
    scripted_model.enqueue(
        tool_turn(
            "remote_ssh_command",
            {"command": "uname -a"},
            split=['{"comm', 'and": "una', 'me -a"}'],
        ),
        text_turn("one execution"),
    )

    async with tui() as driver:
        await driver.submit(connect_line)
        reply = await driver.submit("kernel")

        assert reply == "one execution"
        assert ssh.recorded_commands == ["uname -a"]
        assert len(scripted_model.calls) == 2


async def test_mistral_provider_reassembles_tool_call_fragments(
    tui, e2e_env, ssh: ScriptedSSHServer, connect_line: str, monkeypatch, caplog
):
    """Incidente 2026-10-18 (zai-glm-5-3): argumentos partidos en deltas con id ``null``.

    Con el proveedor real ``ShellMistralModel`` y el SDK falso, el agente debe ejecutar
    exactamente un ``uname -a`` y responder con texto, sin que Strands registre
    ``failed to parse tool input json``.
    """

    write_agent_conf(e2e_env.conf_dir, provider="mistral")
    ssh.script["uname -a"] = CommandResult(0, "Linux fake\n")
    chat = FakeChat(
        stream_scripts=[
            [
                stream_chunk(
                    tool_calls=[tool_call_delta("call_1", "remote_ssh_command", '{"comm')]
                ),
                stream_chunk(tool_calls=[tool_call_delta(None, None, 'and": "una')]),
                stream_chunk(
                    tool_calls=[tool_call_delta(None, None, 'me -a"}')],
                    finish_reason="tool_calls",
                    usage=usage_info(),
                ),
            ],
            [
                stream_chunk(content="Kernel: Linux fake"),
                stream_chunk(finish_reason="stop", usage=usage_info()),
            ],
        ]
    )
    install_fake_mistral(monkeypatch, chat)

    async with tui(patch_model=False) as driver:
        await driver.submit(connect_line)
        with caplog.at_level(logging.WARNING, logger="strands.event_loop.streaming"):
            reply = await driver.submit("dame el kernel")

        assert reply == "Kernel: Linux fake"
        assert ssh.recorded_commands == ["uname -a"]
        assert len(chat.requests) == 2
        assert "failed to parse tool input json" not in caplog.text
