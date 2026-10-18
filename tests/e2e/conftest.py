"""Fixtures compartidas por las pruebas e2e (offline y live) del TUI."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import AbstractAsyncContextManager, ExitStack, asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from smart_ai_sys_admin.agent.factory import AgentFactory
from smart_ai_sys_admin.agent.tools import remote_ssh_command
from smart_ai_sys_admin.config import load_config
from smart_ai_sys_admin.connection import NoActiveConnection
from smart_ai_sys_admin.ui.app import SmartAISysAdminApp
from tests.e2e.agent_conf import write_agent_conf
from tests.e2e.app_driver import TuiDriver
from tests.e2e.fake_model import ScriptedModel
from tests.e2e.ssh_server import ScriptedSSHServer

PERMISSION_ENV_VARS = ("BYPASS_TOOL_CONSENT", "STRANDS_NON_INTERACTIVE")

TuiFactory = Callable[..., AbstractAsyncContextManager[TuiDriver]]


# ---------------------------------------------------------------------- servidor SSH
@pytest.fixture(scope="session")
def ssh_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ScriptedSSHServer]:
    """Un único servidor SSH/SFTP embebido para toda la sesión de pruebas."""

    server = ScriptedSSHServer(sftp_root=tmp_path_factory.mktemp("sftp-root")).start()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def ssh(ssh_server: ScriptedSSHServer) -> Iterator[ScriptedSSHServer]:
    """Vista por prueba: guion y comandos registrados limpios."""

    ssh_server.reset()
    try:
        yield ssh_server
    finally:
        ssh_server.reset()


@pytest.fixture
def connect_line(ssh: ScriptedSSHServer) -> str:
    return f"/connect {ssh.host} {ssh.username} {ssh.password} {ssh.port}"


# ---------------------------------------------------------------------- entorno
@pytest.fixture
def e2e_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, minimal_app_config: Path
) -> SimpleNamespace:
    """Variables de entorno y configuración aisladas para arrancar el TUI real.

    Escribe un ``agent.conf`` por defecto (OpenAI ficticio) en ``conf_dir``; una prueba
    puede regenerarlo con ``write_agent_conf(e2e_env.conf_dir, ...)`` antes de lanzar el TUI.
    """

    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_LOCALE", "en")
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_CONFIG_FILE", str(minimal_app_config))
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_PLUGINS_DIR", str(plugins_dir))
    # Claves ficticias para que la fábrica no falle offline; las reales (live) se respetan.
    for key_env in ("OPENAI_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.setenv(key_env, os.environ.get(key_env) or "e2e-dummy-key")
    for name in PERMISSION_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    conf_dir = tmp_path / "conf"
    agent_conf = write_agent_conf(conf_dir)
    monkeypatch.setenv("SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE", str(agent_conf))

    return SimpleNamespace(
        conf_dir=conf_dir,
        agent_conf=agent_conf,
        tmp_path=tmp_path,
        app_config=load_config(),
    )


@pytest.fixture
def scripted_model() -> ScriptedModel:
    return ScriptedModel()


def _snapshot_remote_tool() -> tuple[Any, Any]:
    spec = getattr(remote_ssh_command, "tool_spec", None)
    name = spec.get("name") if isinstance(spec, dict) else None
    return name, getattr(remote_ssh_command, "_tool_name", None)


def _restore_remote_tool(snapshot: tuple[Any, Any]) -> None:
    name, private_name = snapshot
    spec = getattr(remote_ssh_command, "tool_spec", None)
    if isinstance(spec, dict) and name is not None:
        spec["name"] = name
    if private_name is not None and hasattr(remote_ssh_command, "_tool_name"):
        remote_ssh_command._tool_name = private_name  # type: ignore[attr-defined]


@pytest.fixture
def tui(e2e_env: SimpleNamespace, scripted_model: ScriptedModel) -> TuiFactory:
    """Fábrica de contextos que arranca el TUI real con el ``AgentRuntime`` real.

    ``patch_model=True`` sustituye ``AgentFactory._build_model`` por ``model`` (el
    ``ScriptedModel`` de la prueba). Con ``patch_model=False`` se construye el modelo
    real del proveedor configurado (p. ej. ``ShellMistralModel`` con el SDK falso).
    """

    @asynccontextmanager
    async def _launch(
        *,
        model: Any = None,
        patch_model: bool = True,
        dismiss_welcome: bool = True,
        size: tuple[int, int] = (120, 40),
    ) -> AsyncIterator[TuiDriver]:
        snapshot = _snapshot_remote_tool()
        permission_env_before = {name: os.environ.get(name) for name in PERMISSION_ENV_VARS}
        with ExitStack() as stack:
            if patch_model:
                stack.enter_context(
                    patch.object(
                        AgentFactory,
                        "_build_model",
                        return_value=model if model is not None else scripted_model,
                    )
                )
            app = SmartAISysAdminApp(config=e2e_env.app_config)
            try:
                async with app.run_test(size=size) as pilot:
                    driver = TuiDriver(app, pilot)
                    if dismiss_welcome:
                        await driver.dismiss_welcome()
                    yield driver
            finally:
                try:
                    app._connection_manager.disconnect()
                except NoActiveConnection:
                    pass
                except Exception:  # pragma: no cover - cierre defensivo
                    pass
                # run_test no pasa por action_quit: restauramos el entorno de permisos.
                app._agent_runtime.shutdown()
                _restore_remote_tool(snapshot)
                permission_env_after = {name: os.environ.get(name) for name in PERMISSION_ENV_VARS}
                assert permission_env_after == permission_env_before, (
                    "el TUI filtró variables de consentimiento de tools: "
                    f"{permission_env_before} -> {permission_env_after}"
                )

    return _launch


# ---------------------------------------------------------------------- live
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Toda prueba que use ``live_provider`` lleva ``e2e`` aunque se olvide el marcador."""

    for item in items:
        fixturenames = getattr(item, "fixturenames", ())
        if "live_provider" in fixturenames and not item.get_closest_marker("e2e"):
            item.add_marker(pytest.mark.e2e)
