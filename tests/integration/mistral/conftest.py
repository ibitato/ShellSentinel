"""Fixtures y constantes para la suite PoC Mistral cloud."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import pytest
from mistralai.client import Mistral

# Modelo objetivo del estudio: Mistral Medium 3.5 con reasoning high.
MISTRAL_POC_MODEL = "mistral-medium-3.5"
MISTRAL_REASONING_EFFORT = "high"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.mistral,
]

requires_mistral_api_key = pytest.mark.skipif(
    not os.environ.get("MISTRAL_API_KEY"),
    reason="MISTRAL_API_KEY no está definida en el entorno",
)


def remote_ssh_tool_spec() -> dict[str, Any]:
    """Esquema alineado con la tool `remote_ssh_command` de Shell Sentinel."""
    return {
        "type": "function",
        "function": {
            "name": "remote_ssh_command",
            "description": (
                "Execute a shell command on the connected remote server via SSH. "
                "Returns stdout, stderr and exit code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute on the remote host.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Optional timeout override in seconds.",
                    },
                },
                "required": ["command"],
            },
        },
    }


def strands_tool_spec_from_openai(tool: dict[str, Any]) -> dict[str, Any]:
    """Convierte un tool OpenAI/Mistral a ToolSpec de Strands."""
    fn = tool["function"]
    return {
        "name": fn["name"],
        "description": fn["description"],
        "inputSchema": {"json": fn["parameters"]},
    }


def synthetic_admin_tools(count: int = 20) -> list[dict[str, Any]]:
    """Genera tools sintéticas para simular carga de schemas (MCP + built-in)."""
    tools: list[dict[str, Any]] = []
    for index in range(count):
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": f"synthetic_admin_tool_{index:02d}",
                    "description": f"Synthetic sysadmin helper #{index} for schema load testing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Free-form query."},
                        },
                        "required": [],
                    },
                },
            }
        )
    tools.append(remote_ssh_tool_spec())
    return tools


def extract_visible_text(content: Any) -> str:
    """Extrae texto visible de respuestas Mistral (incluye chunks de reasoning)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for chunk in content:
        chunk_type = getattr(chunk, "type", None)
        if chunk_type == "text":
            parts.append(str(getattr(chunk, "text", "")))
        elif chunk_type == "thinking":
            thinking = getattr(chunk, "thinking", None) or []
            for inner in thinking:
                if getattr(inner, "type", None) == "text":
                    parts.append(str(getattr(inner, "text", "")))
    return "".join(parts)


def first_tool_call(message: Any) -> tuple[str, dict[str, Any]] | None:
    """Devuelve (nombre, argumentos) del primer tool_call o None."""
    import json

    tool_calls = getattr(message, "tool_calls", None) or []
    if not tool_calls:
        return None
    call = tool_calls[0]
    fn = call.function
    raw_args = fn.arguments or "{}"
    return fn.name, json.loads(raw_args)


@contextmanager
def mistral_client() -> Iterator[Mistral]:
    with Mistral(api_key=os.environ["MISTRAL_API_KEY"]) as client:
        yield client


@asynccontextmanager
async def collect_strands_stream(
    stream: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    async for event in stream:
        events.append(event)
    yield events


@pytest.fixture
def mistral_model_id() -> str:
    return MISTRAL_POC_MODEL
