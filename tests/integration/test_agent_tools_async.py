"""Prueba de ejecución async de tools en un worker thread."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from smart_ai_sys_admin.agent.tools import remote_ssh_command


@pytest.mark.asyncio
async def test_remote_ssh_command_in_worker_thread(fake_ssh_manager):
    fake_ssh_manager._fake_connected = True
    fake_ssh_manager._run_result = (0, "thread-ok", "")

    agent = type("Agent", (), {})()
    agent.ssh_manager = fake_ssh_manager
    agent.remote_command_timeout = 30
    agent.remote_command_max_output_chars = 5000

    def _run_in_thread() -> str:
        async def _invoke() -> str:
            return await remote_ssh_command("echo hi", agent=agent)

        return asyncio.run(_invoke())

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = await asyncio.get_running_loop().run_in_executor(pool, _run_in_thread)

    assert "thread-ok" in result
