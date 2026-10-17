"""Pruebas de construcción de transportes MCP (stdio, sse, streamable_http) con mcp 2.x."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import httpx2
import pytest

from smart_ai_sys_admin.agent.config import MCPConfig, MCPTransportConfig
from smart_ai_sys_admin.agent.mcp_manager import (
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    MCPManager,
    _HTTPStatusProbe,
)

MODULE = "smart_ai_sys_admin.agent.mcp_manager"


def _manager() -> MCPManager:
    return MCPManager(MCPConfig(enabled=True, load_server_tools=True, transports=()), MagicMock())


def _transport_callable(cfg: MCPTransportConfig, expected_startup_timeout: int):
    """Devuelve la factoría de transporte que MCPManager entrega a MCPClient."""
    with patch(f"{MODULE}.MCPClient") as client_cls:
        client = _manager()._create_client(cfg)
    assert client is client_cls.return_value
    assert client_cls.call_args.kwargs["startup_timeout"] == expected_startup_timeout
    return client_cls.call_args.args[0]


def test_stdio_transport_builds_server_parameters(monkeypatch):
    monkeypatch.setenv("MCP_TEST_TOKEN", "from-env")
    monkeypatch.delenv("MCP_TEST_MISSING", raising=False)
    cfg = MCPTransportConfig(
        identifier="docs",
        transport_type="stdio",
        command="uvx",
        args=("server@latest", "--flag"),
        env={"STATIC": "1"},
        env_passthrough=("MCP_TEST_TOKEN", "MCP_TEST_MISSING"),
        cwd="/tmp",
        timeout_seconds=12,
    )
    factory = _transport_callable(cfg, expected_startup_timeout=12)
    with patch(f"{MODULE}.stdio_client") as stdio_client:
        assert factory() is stdio_client.return_value
    params = stdio_client.call_args.args[0]
    assert params.command == "uvx"
    assert params.args == ["server@latest", "--flag"]
    assert params.env == {"MCP_TEST_TOKEN": "from-env", "STATIC": "1"}
    assert str(params.cwd) == "/tmp"


def test_sse_transport_passes_headers_and_timeout():
    cfg = MCPTransportConfig(
        identifier="sse",
        transport_type="sse",
        url="http://localhost:8000/sse",
        headers={"Authorization": "Bearer abc"},
        timeout_seconds=30,
    )
    factory = _transport_callable(cfg, expected_startup_timeout=30)
    with patch(f"{MODULE}.sse_client") as sse_client:
        assert factory() is sse_client.return_value
    assert sse_client.call_args.args == ("http://localhost:8000/sse",)
    kwargs = sse_client.call_args.kwargs
    assert kwargs["headers"] == {"Authorization": "Bearer abc"}
    assert kwargs["timeout"] == 30
    assert kwargs["sse_read_timeout"] == 300
    # La factoría httpx2 propia conserva cabeceras y timeout y registra estados HTTP de error.
    client = kwargs["httpx_client_factory"](headers={"A": "b"}, timeout=httpx2.Timeout(7.0))
    assert client.headers["A"] == "b"
    assert client.timeout.connect == 7
    assert isinstance(client.event_hooks["response"][0], _HTTPStatusProbe)


def test_sse_transport_without_timeout_uses_defaults():
    cfg = MCPTransportConfig(identifier="sse", transport_type="sse", url="http://h/sse")
    factory = _transport_callable(cfg, expected_startup_timeout=DEFAULT_STARTUP_TIMEOUT_SECONDS)
    with patch(f"{MODULE}.sse_client") as sse_client:
        factory()
    assert sse_client.call_args.kwargs["timeout"] == 30
    assert sse_client.call_args.kwargs["headers"] == {}


def _fake_streamable_http_client(captured: dict):
    @asynccontextmanager
    async def fake(url, *, http_client=None, terminate_on_close=True):
        captured["url"] = url
        captured["http_client"] = http_client
        yield ("read", "write")

    return fake


async def test_streamable_http_transport_configures_httpx2_client():
    cfg = MCPTransportConfig(
        identifier="http",
        transport_type="streamable_http",
        url="http://localhost:8000/mcp",
        headers={"X-Api-Key": "secret"},
        timeout_seconds=45,
    )
    factory = _transport_callable(cfg, expected_startup_timeout=45)
    captured: dict = {}
    with patch(f"{MODULE}.streamable_http_client", _fake_streamable_http_client(captured)):
        async with factory() as streams:
            assert streams == ("read", "write")
            http_client = captured["http_client"]
            assert not http_client.is_closed

    assert captured["url"] == "http://localhost:8000/mcp"
    assert isinstance(http_client, httpx2.AsyncClient)
    assert http_client.headers["X-Api-Key"] == "secret"
    assert http_client.follow_redirects is True
    assert http_client.timeout.connect == 45
    assert http_client.timeout.write == 45
    assert http_client.timeout.read == 300
    assert isinstance(http_client.event_hooks["response"][0], _HTTPStatusProbe)
    # El cliente httpx2 lo crea Shell Sentinel, así que debe cerrarse al salir del transporte.
    assert http_client.is_closed


async def test_streamable_http_transport_without_timeout_uses_defaults():
    cfg = MCPTransportConfig(
        identifier="http", transport_type="streamable_http", url="http://h/mcp"
    )
    factory = _transport_callable(cfg, expected_startup_timeout=DEFAULT_STARTUP_TIMEOUT_SECONDS)
    captured: dict = {}
    with patch(f"{MODULE}.streamable_http_client", _fake_streamable_http_client(captured)):
        async with factory():
            pass
    timeout = captured["http_client"].timeout
    assert timeout.connect == 30
    assert timeout.read == 300


async def test_http_status_probe_records_last_error_status():
    probe = _HTTPStatusProbe()
    request = httpx2.Request("POST", "http://h/mcp")
    await probe(httpx2.Response(200, request=request))
    assert probe.last_error_status is None
    await probe(httpx2.Response(401, request=request))
    await probe(httpx2.Response(200, request=request))
    assert probe.last_error_status == 401


@pytest.mark.parametrize("transport_type", ["sse", "streamable_http"])
def test_http_transports_require_url(transport_type):
    cfg = MCPTransportConfig(identifier="x", transport_type=transport_type, url=None)
    with pytest.raises(ValueError, match="url"):
        _manager()._create_client(cfg)


def test_unsupported_transport_type_raises():
    cfg = MCPTransportConfig(identifier="x", transport_type="websocket")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="websocket"):
        _manager()._create_client(cfg)
