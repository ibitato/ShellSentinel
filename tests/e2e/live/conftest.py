"""Fixtures de las pruebas e2e live: TUI real + proveedor real + servidor SSH embebido."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from strands import Agent

from tests.e2e.agent_conf import shipped_system_prompt, write_agent_conf
from tests.e2e.app_driver import TuiDriver
from tests.e2e.guards import GUARD_SENTINEL, E2EGuard
from tests.e2e.providers import (
    LiveProvider,
    live_params,
    max_model_calls,
    run_e2e_enabled,
    turn_timeout,
)
from tests.e2e.ssh_server import ScriptedSSHServer

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not run_e2e_enabled(), reason="RUN_E2E=1 es necesario para las pruebas live"
    ),
]

BAD_KEY_ENV = "SHELL_SENTINEL_E2E_BAD_KEY"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "live_provider" in metafunc.fixturenames:
        metafunc.parametrize("live_provider", live_params(os.environ))


@dataclass
class LiveSession:
    """TUI real conectado a un proveedor real, con el guarda de coste instalado."""

    driver: TuiDriver
    guard: E2EGuard
    provider: LiveProvider
    ssh: ScriptedSSHServer

    async def ask(self, prompt: str) -> str:
        """Envía un prompt al agente respetando el timeout por turno del proveedor."""

        self.guard.restart_clock()
        return await self.driver.submit(prompt, timeout=turn_timeout(self.provider))

    def assert_clean_reply(self, reply: str) -> None:
        report = self.guard.debug_report()
        assert self.guard.tripped is None, report
        assert reply.strip(), report
        assert not reply.startswith("❌"), f"{reply}\n{report}"
        assert GUARD_SENTINEL not in reply, report
        assert "<think>" not in reply.lower(), reply

    def assert_commands_well_formed(self) -> None:
        """Todo ``remote_ssh_command`` debe traer ``command`` no vacío (bug de deltas partidos)."""

        report = self.guard.debug_report()
        commands = self.guard.commands()
        assert commands, report
        for command in commands:
            assert isinstance(command, str) and command.strip(), report


@pytest.fixture
def live_conf(e2e_env: SimpleNamespace, live_provider: LiveProvider) -> SimpleNamespace:
    write_agent_conf(
        e2e_env.conf_dir,
        provider=live_provider.conf_key,
        model_id=live_provider.model_id,
        system_prompt=shipped_system_prompt(live_provider.conf_key),
        provider_block=live_provider.provider_block,
        api_key_env=live_provider.api_key_env,
        timeout_seconds=30,
        max_output_chars=5000,
        cache_key=live_provider.cache_key,
        cache_enabled=live_provider.cache_configurable,
    )
    return e2e_env


@pytest.fixture
def bad_key_conf(
    e2e_env: SimpleNamespace, live_provider: LiveProvider, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    """Misma configuración pero apuntando a una variable con una clave inválida."""

    monkeypatch.setenv(BAD_KEY_ENV, "invalid-e2e-key")
    write_agent_conf(
        e2e_env.conf_dir,
        provider=live_provider.conf_key,
        model_id=live_provider.model_id,
        system_prompt=shipped_system_prompt(live_provider.conf_key),
        provider_block=live_provider.provider_block,
        api_key_env=BAD_KEY_ENV,
        timeout_seconds=30,
        max_output_chars=5000,
        cache_key=live_provider.cache_key,
        cache_enabled=live_provider.cache_configurable,
    )
    return e2e_env


async def _start_session(tui, live_provider: LiveProvider, ssh: ScriptedSSHServer):  # type: ignore[no-untyped-def]
    guard = E2EGuard(
        max_model_calls=max_model_calls(live_provider),
        deadline_s=turn_timeout(live_provider),
    )
    async with tui(patch_model=False) as driver:
        runtime = driver.runtime
        assert runtime.ready, runtime.error_message
        agent = runtime._agent
        assert isinstance(agent, Agent)
        agent.hooks.add_hook(guard)
        yield LiveSession(driver, guard, live_provider, ssh)


@pytest.fixture
async def live_app(  # type: ignore[no-untyped-def]
    live_conf, tui, live_provider: LiveProvider, ssh: ScriptedSSHServer
) -> AsyncIterator[LiveSession]:
    async for session in _start_session(tui, live_provider, ssh):
        yield session


@pytest.fixture
async def bad_key_app(  # type: ignore[no-untyped-def]
    bad_key_conf, tui, live_provider: LiveProvider, ssh: ScriptedSSHServer
) -> AsyncIterator[LiveSession]:
    async for session in _start_session(tui, live_provider, ssh):
        yield session


@pytest.fixture
async def connected_live_app(live_app: LiveSession, connect_line: str) -> LiveSession:
    """Sesión live ya conectada al servidor SSH con el perfil de hardware cargado."""

    live_app.ssh.load_hardware_profile()
    reply = await live_app.driver.submit(connect_line)
    assert reply.startswith("✅"), reply
    assert (
        f"{live_app.ssh.username}@{live_app.ssh.host}:{live_app.ssh.port}"
        in live_app.driver.footer()
    )
    return live_app
