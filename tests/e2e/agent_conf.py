"""Generación de ``agent.conf`` temporales para las pruebas e2e.

Parte de ``tests/fixtures/agent.conf.minimal.json`` y deja solo el bloque del
proveedor seleccionado con las tools propias de Shell Sentinel, consentimiento
automático y MCP desactivado. Nunca escribe valores de claves: solo nombres de
variables de entorno (``api_key_env``).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
FIXTURE_CONF = FIXTURES_DIR / "agent.conf.minimal.json"
FIXTURE_PROMPT = FIXTURES_DIR / "system_prompts" / "test.md"
SHIPPED_PROMPTS_DIR = REPO_ROOT / "system_prompts"

DEFAULT_REMOTE_TOOL_NAME = "remote_ssh_command"


def _deep_merge(base: dict[str, Any], extra: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in extra.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def write_agent_conf(
    dest_dir: Path,
    *,
    provider: str = "openai",
    model_id: str | None = None,
    system_prompt: str | Path | None = None,
    provider_block: Mapping[str, Any] | None = None,
    api_key_env: str | None = None,
    default_tools: Sequence[str] = (),
    remote_tool_name: str = DEFAULT_REMOTE_TOOL_NAME,
    timeout_seconds: int = 60,
    max_output_chars: int = 500,
    window_size: int = 40,
    streaming: bool = True,
    max_turns: int | None = 25,
    cache_key: str | None = None,
    cache_enabled: bool = True,
    show_thinking: bool = False,
) -> Path:
    """Escribe ``dest_dir/agent.conf`` y devuelve su ruta.

    Sin ``system_prompt`` se copia el prompt de pruebas junto a la configuración
    (``system_prompts/test.md``, ruta relativa al directorio del conf). Para las
    pruebas live se pasa la ruta absoluta del prompt real de ``system_prompts/``.
    ``cache_enabled=False`` escribe ``cache: {"enabled": false}`` (sin ``cache_key``) para
    proveedores que ignoran el bloque, como Gemini.
    """

    dest_dir.mkdir(parents=True, exist_ok=True)
    payload = json.loads(FIXTURE_CONF.read_text(encoding="utf-8"))

    if provider not in payload["providers"]:
        raise ValueError(f"El fixture no tiene bloque para el proveedor {provider!r}")
    block: dict[str, Any] = dict(payload["providers"][provider])

    if system_prompt is None:
        prompts_dir = dest_dir / "system_prompts"
        prompts_dir.mkdir(exist_ok=True)
        shutil.copy(FIXTURE_PROMPT, prompts_dir / "test.md")
        block["system_prompt"] = "system_prompts/test.md"
    else:
        block["system_prompt"] = str(system_prompt)

    if model_id is not None:
        block["model_id"] = model_id
    block["show_thinking"] = show_thinking

    if api_key_env is not None:
        if provider == "openai":
            client_args = dict(block.get("client_args") or {})
            client_args["api_key_env"] = api_key_env
            block["client_args"] = client_args
        else:
            block["api_key_env"] = api_key_env

    cache_block: dict[str, Any] = {"enabled": cache_enabled}
    if cache_enabled and cache_key is not None:
        cache_block["cache_key"] = cache_key
    block["cache"] = _deep_merge(dict(block.get("cache") or {}), cache_block)

    if provider_block:
        overrides = dict(provider_block)
        # Los params del fixture (temperature, max_tokens de prueba) no se mezclan con los
        # reales: algunos modelos rechazan parámetros que no soportan (p. ej. temperature).
        if "params" in overrides:
            block["params"] = dict(overrides.pop("params"))
        block = _deep_merge(block, overrides)

    payload["provider"] = provider
    payload["providers"] = {provider: block}
    payload["agent"] = _deep_merge(
        dict(payload.get("agent") or {}),
        {
            "streaming": streaming,
            "max_turns": max_turns,
            "conversation": {
                "strategy": "sliding_window",
                "window_size": window_size,
                "truncate_tool_results": True,
            },
        },
    )
    payload["tools"] = {
        "default": list(default_tools),
        "remote_command": {
            "name": remote_tool_name,
            "timeout_seconds": timeout_seconds,
            "max_output_chars": max_output_chars,
        },
        "load_directory": False,
        "consent": {"bypass": True},
    }
    payload["mcp"] = {"enabled": False, "load_server_tools": True, "transports": []}

    conf_path = dest_dir / "agent.conf"
    conf_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return conf_path


def shipped_system_prompt(provider: str) -> Path:
    """Ruta absoluta del system prompt real que distribuye el proyecto para ``provider``."""

    path = SHIPPED_PROMPTS_DIR / f"{provider}.md"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


__all__ = ["DEFAULT_REMOTE_TOOL_NAME", "REPO_ROOT", "shipped_system_prompt", "write_agent_conf"]
