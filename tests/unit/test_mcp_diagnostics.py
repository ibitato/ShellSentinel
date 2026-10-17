"""Pruebas del diagnóstico de fallos de arranque MCP."""

from __future__ import annotations

import pytest
from httpx2 import ConnectError, HTTPStatusError, ReadTimeout, Request, Response
from mcp.shared.exceptions import MCPError
from strands.types.exceptions import MCPClientInitializationError

from smart_ai_sys_admin.agent.mcp_diagnostics import (
    MCPFailure,
    MCPFailureKind,
    classify_mcp_failure,
    describe_mcp_failure,
    iter_exception_chain,
)
from smart_ai_sys_admin.localization import reset_localizer


def _wrapped(inner: BaseException, *, grouped: bool = True) -> MCPClientInitializationError:
    """Reproduce la envoltura que strands + anyio aplican a un fallo de arranque."""

    cause: BaseException = inner
    if grouped:
        cause = ExceptionGroup("unhandled errors in a TaskGroup", [inner])
        cause = ExceptionGroup("unhandled errors in a TaskGroup", [cause])
    outer = MCPClientInitializationError(f"the client initialization failed: {cause}")
    outer.__cause__ = cause
    return outer


def _http_status_error(status: int, url: str = "http://h/sse") -> HTTPStatusError:
    request = Request("GET", url)
    response = Response(status, request=request)
    return HTTPStatusError(
        f"Client error '{status}' for url '{url}'", request=request, response=response
    )


def test_iter_exception_chain_walks_groups_cause_and_context():
    root = ValueError("root")
    contextual = KeyError("ctx")
    contextual.__context__ = root
    group = ExceptionGroup("g", [contextual, OSError("sibling")])
    outer = RuntimeError("outer")
    outer.__cause__ = group
    types = [type(e) for e in iter_exception_chain(outer)]
    assert types == [RuntimeError, ExceptionGroup, KeyError, ValueError, OSError]


@pytest.mark.parametrize(
    ("exc", "transport", "status", "kind", "code"),
    [
        (
            _wrapped(
                FileNotFoundError("[Errno 2] No such file or directory: 'uvx'"), grouped=False
            ),
            "stdio",
            None,
            MCPFailureKind.COMMAND_NOT_FOUND,
            None,
        ),
        (
            _wrapped(PermissionError("[Errno 13] Permission denied"), grouped=False),
            "stdio",
            None,
            MCPFailureKind.COMMAND_NOT_EXECUTABLE,
            None,
        ),
        (
            _wrapped(MCPError(code=-32000, message="Connection closed")),
            "stdio",
            None,
            MCPFailureKind.PROCESS_EXITED,
            None,
        ),
        (
            _wrapped(_http_status_error(401), grouped=False),
            "sse",
            None,
            MCPFailureKind.UNAUTHORIZED,
            401,
        ),
        (
            _wrapped(_http_status_error(503), grouped=False),
            "sse",
            None,
            MCPFailureKind.HTTP_ERROR,
            503,
        ),
        (
            _wrapped(MCPError(code=-32603, message="Server returned an error response")),
            "streamable_http",
            403,
            MCPFailureKind.UNAUTHORIZED,
            403,
        ),
        (
            _wrapped(MCPError(code=-32603, message="Server returned an error response")),
            "streamable_http",
            500,
            MCPFailureKind.HTTP_ERROR,
            500,
        ),
        (
            _wrapped(MCPError(code=-32603, message="Server returned an error response")),
            "streamable_http",
            None,
            MCPFailureKind.HTTP_ERROR,
            None,
        ),
        (
            _wrapped(MCPError(code=-32601, message="Not Found")),
            "streamable_http",
            404,
            MCPFailureKind.NOT_FOUND,
            404,
        ),
        (
            _wrapped(ConnectError("All connection attempts failed")),
            "streamable_http",
            None,
            MCPFailureKind.UNREACHABLE,
            None,
        ),
        (
            _wrapped(ReadTimeout("timed out")),
            "sse",
            None,
            MCPFailureKind.TIMEOUT,
            None,
        ),
        (
            _wrapped(TimeoutError(), grouped=False),
            "streamable_http",
            None,
            MCPFailureKind.TIMEOUT,
            None,
        ),
        (
            ValueError("El transporte MCP 'sse' requiere el campo 'url'."),
            "sse",
            None,
            MCPFailureKind.INVALID_CONFIG,
            None,
        ),
        (
            _wrapped(RuntimeError("something odd")),
            "streamable_http",
            None,
            MCPFailureKind.UNKNOWN,
            None,
        ),
    ],
)
def test_classify_mcp_failure(exc, transport, status, kind, code):
    failure = classify_mcp_failure(exc, transport, http_status=status)
    assert failure.kind == kind
    assert failure.status_code == code
    assert failure.detail


def test_classify_prefers_root_message_as_detail():
    failure = classify_mcp_failure(_wrapped(RuntimeError("the real reason")), "sse")
    assert failure.detail == "the real reason"


@pytest.mark.parametrize("locale", ["en", "es", "de"])
@pytest.mark.parametrize("kind", list(MCPFailureKind))
def test_describe_mcp_failure_is_translated(locale, kind):
    reset_localizer(locale)
    text = describe_mcp_failure(
        MCPFailure(kind, "detail text", 401),
        command="uvx",
        url="http://h/mcp",
        timeout_seconds=30,
        missing_env=("API_KEY",),
    )
    assert not text.startswith("agent.mcp")
    assert "{" not in text
    assert "API_KEY" in text


def test_describe_mcp_failure_mentions_context():
    reset_localizer("en")
    text = describe_mcp_failure(
        MCPFailure(MCPFailureKind.UNAUTHORIZED, "401", 401), url="http://h/mcp"
    )
    assert "http://h/mcp" in text
    assert "401" in text
    assert "headers" in text
