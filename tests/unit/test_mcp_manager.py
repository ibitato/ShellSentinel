"""Pruebas del arranque paralelo y acotado de servidores MCP."""

from __future__ import annotations

import logging
import threading
import time
from unittest.mock import MagicMock

import pytest

from smart_ai_sys_admin.agent.config import MCPConfig, MCPTransportConfig
from smart_ai_sys_admin.agent.mcp_manager import MCPManager


class FakeClient:
    """Doble de MCPClient controlado por la prueba."""

    def __init__(
        self,
        *,
        tools: list[str] | None = None,
        start_delay: float = 0.0,
        start_error: BaseException | None = None,
        tools_error: BaseException | None = None,
        tools_delay: float = 0.0,
    ) -> None:
        self.tools = tools or []
        self.start_delay = start_delay
        self.start_error = start_error
        self.tools_error = tools_error
        self.tools_delay = tools_delay
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.stop_calls = 0
        self.list_calls = 0

    def start(self) -> FakeClient:
        if self.start_delay:
            time.sleep(self.start_delay)
        if self.start_error is not None:
            raise self.start_error
        self.started.set()
        return self

    def list_tools_sync(self) -> list[str]:
        self.list_calls += 1
        if self.tools_delay:
            time.sleep(self.tools_delay)
        if self.tools_error is not None:
            raise self.tools_error
        return list(self.tools)

    def stop(self, *_args) -> None:
        self.stop_calls += 1
        self.stopped.set()


def _transport(identifier: str, **kwargs) -> MCPTransportConfig:
    kwargs.setdefault("transport_type", "sse")
    kwargs.setdefault("url", f"http://{identifier}/sse")
    return MCPTransportConfig(identifier=identifier, **kwargs)


def _manager(
    transports: tuple[MCPTransportConfig, ...],
    clients: dict[str, FakeClient | BaseException],
    *,
    grace: float = 0.1,
) -> MCPManager:
    manager = MCPManager(
        MCPConfig(enabled=True, load_server_tools=True, transports=transports),
        logging.getLogger("test.mcp"),
        startup_grace_seconds=grace,
    )

    def create(cfg: MCPTransportConfig):
        outcome = clients[cfg.identifier]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    manager._create_client = create  # type: ignore[method-assign]
    return manager


def test_servers_start_in_parallel_and_tools_keep_config_order():
    a = FakeClient(tools=["a1", "a2"], start_delay=0.3)
    b = FakeClient(tools=["b1"], start_delay=0.3)
    manager = _manager((_transport("a"), _transport("b")), {"a": a, "b": b})
    started_at = time.monotonic()
    tools = manager.activate()
    assert time.monotonic() - started_at < 0.55
    assert tools == ["a1", "a2", "b1"]
    assert [(s.identifier, s.ready, s.tool_count) for s in manager.statuses] == [
        ("a", True, 2),
        ("b", True, 1),
    ]
    manager.close()
    assert a.stopped.is_set() and b.stopped.is_set()


def test_hung_server_is_abandoned_after_deadline_and_closed_when_it_finishes():
    # Si el listado también se colgase (tools_delay) no debe llegar a ejecutarse.
    slow = FakeClient(tools=["late"], start_delay=1.5, tools_delay=30)
    fast = FakeClient(tools=["ok"])
    manager = _manager(
        (_transport("slow", timeout_seconds=1), _transport("fast")),
        {"slow": slow, "fast": fast},
    )
    started_at = time.monotonic()
    tools = manager.activate()
    assert time.monotonic() - started_at < 1.4
    assert tools == ["ok"]
    slow_status, fast_status = manager.statuses
    assert slow_status.ready is False
    assert "1s" in slow_status.message
    assert "timeout_seconds" in slow_status.message
    assert fast_status.ready is True
    # El cliente abandonado se cierra en cuanto termina el saludo, sin listar herramientas.
    assert slow.stopped.wait(2.0)
    assert slow.list_calls == 0
    assert slow.stop_calls == 1
    manager.close()
    assert fast.stopped.is_set()
    assert slow.stop_calls == 1


def test_server_hung_on_tool_listing_is_stopped_at_once_and_only_once():
    stuck = FakeClient(tools=["late"], tools_delay=1.5)
    manager = _manager((_transport("stuck", timeout_seconds=1),), {"stuck": stuck})
    started_at = time.monotonic()
    assert manager.activate() == []
    assert time.monotonic() - started_at < 1.4
    (status,) = manager.statuses
    assert status.ready is False
    assert "timeout_seconds" in status.message
    # El saludo terminó, así que el proceso existe y debe cerrarse sin esperar al listado.
    assert stuck.stopped.wait(0.3)
    # Cuando el listado colgado termina, el hilo de arranque no vuelve a cerrarlo.
    time.sleep(1.5)
    assert stuck.stop_calls == 1
    manager.close()
    assert stuck.stop_calls == 1


def test_failed_start_is_reported_with_cause_and_not_closed():
    broken = FakeClient(start_error=FileNotFoundError("[Errno 2] No such file or directory: 'uvx'"))
    manager = _manager(
        (_transport("docs", transport_type="stdio", url=None, command="uvx"),),
        {"docs": broken},
    )
    assert manager.activate() == []
    (status,) = manager.statuses
    assert status.ready is False
    assert "uvx" in status.message
    assert "PATH" in status.message
    manager.close()
    assert not broken.stopped.is_set()


def test_tool_listing_error_keeps_client_for_cleanup():
    client = FakeClient(tools_error=RuntimeError("listing failed"))
    manager = _manager((_transport("x"),), {"x": client})
    assert manager.activate() == []
    (status,) = manager.statuses
    assert status.ready is False
    assert "listing failed" in status.message
    manager.close()
    assert client.stopped.is_set()


def test_invalid_transport_config_is_reported():
    manager = _manager(
        (_transport("bad"),),
        {"bad": ValueError("El transporte MCP 'sse' requiere el campo 'url'.")},
    )
    assert manager.activate() == []
    (status,) = manager.statuses
    assert status.ready is False
    assert "requiere" in status.message


def test_missing_env_is_reported_alongside_ready_status(monkeypatch):
    monkeypatch.delenv("MCP_TEST_SECRET", raising=False)
    cfg = _transport(
        "docs",
        transport_type="stdio",
        url=None,
        command="uvx",
        env_passthrough=("MCP_TEST_SECRET",),
    )
    manager = MCPManager(
        MCPConfig(enabled=True, load_server_tools=True, transports=(cfg,)),
        MagicMock(),
        startup_grace_seconds=0.1,
    )
    fake = FakeClient(tools=["t"])
    original = manager._create_client

    def create(transport_cfg: MCPTransportConfig):
        original(transport_cfg)
        return fake

    manager._create_client = create  # type: ignore[method-assign]
    assert manager.activate() == ["t"]
    (status,) = manager.statuses
    assert status.ready is True
    assert status.message is not None
    assert "MCP_TEST_SECRET" in status.message


@pytest.mark.parametrize("enabled", [False, True])
def test_disabled_or_empty_config_returns_nothing(enabled):
    manager = MCPManager(
        MCPConfig(enabled=enabled, load_server_tools=True, transports=()), MagicMock()
    )
    assert manager.activate() == []
    assert manager.statuses == ()
