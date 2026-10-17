"""Pruebas de construcción de transportes MCP (stdio, sse, streamable_http) con mcp 2.x."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import httpx2
import pytest

from smart_ai_sys_admin.agent.config import MCPConfig, MCPTransportConfig
from smart_ai_sys_admin.agent.runtime import MCPManager

RUNTIME = "smart_ai_sys_admin.agent.runtime"


def _manager() -> MCPManager:
    return MCPManager(MCPConfig(enabled=True, load_server_tools=True, transports=()), MagicMock())


def _transport_callable(cfg: MCPTransportConfig):
    """Devuelve la factoría de transporte que MCPManager entrega a MCPClient."""
    with patch(f"{RUNTIME}.MCPClient") as client_cls:
        client = _manager()._create_client(cfg)
    assert client is client_cls.return_value
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
    )
    factory = _transport_callable(cfg)
    with patch(f"{RUNTIME}.stdio_client") as stdio_client:
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
    factory = _transport_callable(cfg)
    with patch(f"{RUNTIME}.sse_client") as sse_client:
        assert factory() is sse_client.return_value
    sse_client.assert_called_once_with(
        "http://localhost:8000/sse", headers={"Authorization": "Bearer abc"}, timeout=30
    )


def test_sse_transport_without_timeout_keeps_sdk_default():
    cfg = MCPTransportConfig(identifier="sse", transport_type="sse", url="http://h/sse")
    factory = _transport_callable(cfg)
    with patch(f"{RUNTIME}.sse_client") as sse_client:
        factory()
    sse_client.assert_called_once_with("http://h/sse", headers={})


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
    factory = _transport_callable(cfg)
    captured: dict = {}
    with patch(f"{RUNTIME}.streamable_http_client", _fake_streamable_http_client(captured)):
        async with factory() as streams:
            assert streams == ("read", "write")
            http_client = captured["http_client"]
            assert not http_client.is_closed

    assert captured["url"] == "http://localhost:8000/mcp"
    assert isinstance(http_client, httpx2.AsyncClient)
    assert http_client.headers["X-Api-Key"] == "secret"
    assert http_client.timeout.connect == 45
    assert http_client.timeout.write == 45
    assert http_client.timeout.read == 300
    # El cliente httpx2 lo crea Shell Sentinel, así que debe cerrarse al salir del transporte.
    assert http_client.is_closed


async def test_streamable_http_transport_without_timeout_uses_mcp_defaults():
    cfg = MCPTransportConfig(
        identifier="http", transport_type="streamable_http", url="http://h/mcp"
    )
    factory = _transport_callable(cfg)
    captured: dict = {}
    with patch(f"{RUNTIME}.streamable_http_client", _fake_streamable_http_client(captured)):
        async with factory():
            pass
    timeout = captured["http_client"].timeout
    assert timeout.connect == 30
    assert timeout.read == 300


@pytest.mark.parametrize("transport_type", ["sse", "streamable_http"])
def test_http_transports_require_url(transport_type):
    cfg = MCPTransportConfig(identifier="x", transport_type=transport_type, url=None)
    with pytest.raises(ValueError, match="url"):
        _manager()._create_client(cfg)


def test_unsupported_transport_type_raises():
    cfg = MCPTransportConfig(identifier="x", transport_type="websocket")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="websocket"):
        _manager()._create_client(cfg)
