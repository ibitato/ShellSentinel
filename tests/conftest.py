"""Fixtures compartidas para la suite de pruebas."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from smart_ai_sys_admin.agent.runtime import AgentRuntime
from smart_ai_sys_admin.config import OutputPanelConfig
from smart_ai_sys_admin.connection import ConnectionDetails, SSHConnectionManager
from smart_ai_sys_admin.localization import reset_localizer
from smart_ai_sys_admin.ui.commands import SlashCommandProcessor

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_localizer():
    reset_localizer("en")
    yield
    reset_localizer("en")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def minimal_agent_conf(tmp_path: Path, fixtures_dir: Path) -> Path:
    """Copia agent.conf y system prompt a un directorio temporal."""

    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    prompts_dir = conf_dir / "system_prompts"
    prompts_dir.mkdir()
    shutil.copy(fixtures_dir / "system_prompts" / "test.md", prompts_dir / "test.md")
    config_path = conf_dir / "agent.conf"
    shutil.copy(fixtures_dir / "agent.conf.minimal.json", config_path)
    return config_path


@pytest.fixture
def minimal_app_config(tmp_path: Path, fixtures_dir: Path) -> Path:
    config_path = tmp_path / "app_config.json"
    shutil.copy(fixtures_dir / "app_config.minimal.json", config_path)
    return config_path


@pytest.fixture
def connection_logger() -> logging.Logger:
    return logging.getLogger("test.connection")


class FakeSSHConnectionManager(SSHConnectionManager):
    """Doble de prueba compatible con isinstance(SSHConnectionManager)."""

    def __init__(self) -> None:
        super().__init__(logging.getLogger("test.connection"))
        self._fake_connected = False
        self.connect_calls: list[dict] = []
        self.disconnect_calls = 0
        self.commands_run: list[tuple[str, int | None]] = []
        self._run_result: tuple[int, str, str] = (0, "ok", "")
        self.connect_error: Exception | None = None
        self.disconnect_error: Exception | None = None
        self._fake_details: ConnectionDetails | None = None

    @property
    def is_connected(self) -> bool:
        return self._fake_connected

    def connect(
        self,
        host: str,
        username: str,
        *,
        password: str | None = None,
        key_path: str | None = None,
        port: int = 22,
    ) -> ConnectionDetails:
        if self.connect_error:
            raise self.connect_error
        self.connect_calls.append(
            {
                "host": host,
                "username": username,
                "password": password,
                "key_path": key_path,
                "port": port,
            }
        )
        auth_method = "key" if key_path else "password"
        self._fake_connected = True
        self._fake_details = ConnectionDetails(
            host=host,
            port=port,
            username=username,
            auth_method=auth_method,
        )
        return self._fake_details

    def disconnect(self) -> None:
        if self.disconnect_error:
            raise self.disconnect_error
        self.disconnect_calls += 1
        self._fake_connected = False
        self._fake_details = None

    def status_summary(self) -> str:
        if not self._fake_connected or not self._fake_details:
            return "disconnected"
        return f"{self._fake_details.username}@{self._fake_details.host}:{self._fake_details.port}"

    def run_command(self, command: str, *, timeout: int | None = None) -> tuple[int, str, str]:
        self.commands_run.append((command, timeout))
        return self._run_result

    def upload_file(self, local_path: str, remote_path: str, *, overwrite: bool = False) -> str:
        return remote_path

    def download_file(self, remote_path: str, local_path: str, *, overwrite: bool = False) -> Path:
        return Path(local_path)


@pytest.fixture
def fake_ssh_manager() -> FakeSSHConnectionManager:
    return FakeSSHConnectionManager()


class FakeAgentRuntime:
    """Doble de prueba para AgentRuntime."""

    def __init__(self) -> None:
        self.ready = True
        self.error_message: str | None = None
        self.status_message: str | None = None
        self.invoke_calls: list[str] = []
        self.initialize_calls = 0
        self.shutdown_calls = 0
        self._invoke_result = "agent response"
        self._summary = {
            "ready": True,
            "streaming": True,
            "provider": "OpenAI",
            "model": "gpt-test",
            "config_path": "/tmp/agent.conf",
            "status": "ok",
            "error": None,
        }

    def initialize(self) -> None:
        self.initialize_calls += 1

    def invoke(self, prompt: str) -> str:
        self.invoke_calls.append(prompt)
        return self._invoke_result

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        self.ready = False

    def provider_footer_summary(self) -> str:
        return "OpenAI · gpt-test"

    def agent_summary(self) -> dict:
        return dict(self._summary)


@pytest.fixture
def fake_agent_runtime() -> FakeAgentRuntime:
    return FakeAgentRuntime()


@pytest.fixture
def output_panel_config() -> OutputPanelConfig:
    return OutputPanelConfig(
        title="Output",
        border_style="#FF8C00",
        text_style="#FFB347",
        background="#000000",
        initial_markdown="",
        placeholder_response_markdown="placeholder",
    )


@pytest.fixture
def slash_processor(
    fake_ssh_manager: FakeSSHConnectionManager,
    fake_agent_runtime: FakeAgentRuntime,
    output_panel_config: OutputPanelConfig,
) -> SlashCommandProcessor:
    return SlashCommandProcessor(
        fake_ssh_manager,
        fake_agent_runtime,  # type: ignore[arg-type]
        output_panel_config,
        logging.getLogger("test.commands"),
    )


@pytest.fixture
def real_ssh_manager(connection_logger: logging.Logger) -> SSHConnectionManager:
    return SSHConnectionManager(connection_logger)


@pytest.fixture
def agent_runtime(real_ssh_manager: SSHConnectionManager) -> AgentRuntime:
    return AgentRuntime(real_ssh_manager, logging.getLogger("test.agent.runtime"))


@pytest.fixture
def mock_agent_namespace(fake_ssh_manager: FakeSSHConnectionManager) -> SimpleNamespace:
    return SimpleNamespace(
        ssh_manager=fake_ssh_manager,
        remote_command_timeout=120,
        remote_command_max_output_chars=1000,
    )
