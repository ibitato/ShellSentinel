"""Registro de proveedores reales para las pruebas e2e live.

Cada fila describe cómo configurar ``agent.conf`` para un proveedor/modelo y qué
comportamiento de caché cabe esperar. La selección se hace por variables de
entorno para que ``docker exec -e`` y ``make test-e2e-live`` las propaguen sin
opciones de pytest adicionales:

- ``RUN_E2E=1`` habilita las pruebas live (si no, se saltan todas).
- ``SHELL_SENTINEL_E2E_PROVIDERS=openai,mistral`` limita los proveedores (por defecto todos).
- ``SHELL_SENTINEL_E2E_MAX_MODEL_CALLS`` y ``SHELL_SENTINEL_E2E_TURN_TIMEOUT`` ajustan los guardas.

Las claves se leen únicamente de ``os.environ`` (``api_key_env``); nunca se escriben en disco.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import pytest

CacheExpectation = Literal["strict", "best_effort", "none"]

PROVIDERS_ENV = "SHELL_SENTINEL_E2E_PROVIDERS"
MAX_MODEL_CALLS_ENV = "SHELL_SENTINEL_E2E_MAX_MODEL_CALLS"
TURN_TIMEOUT_ENV = "SHELL_SENTINEL_E2E_TURN_TIMEOUT"
RUN_E2E_ENV = "RUN_E2E"


@dataclass(frozen=True)
class LiveProvider:
    """Proveedor/modelo real contra el que se ejecuta la suite live."""

    name: str
    conf_key: Literal["openai", "mistral", "gemini"]
    model_id: str
    api_key_env: str
    provider_block: Mapping[str, Any] = field(default_factory=dict)
    cache_expectation: CacheExpectation = "none"
    # False cuando el proveedor ignora el bloque ``cache`` (``/status`` muestra "no").
    cache_configurable: bool = True
    cache_min_prefix_tokens: int = 0
    max_model_calls: int = 12
    turn_timeout_s: float = 180.0

    @property
    def cache_key(self) -> str:
        """Clave de enrutamiento estable por proveedor: el prefijo se comparte entre pruebas."""

        return f"shell-sentinel-e2e-{self.name}"


REGISTRY: tuple[LiveProvider, ...] = (
    LiveProvider(
        name="openai",
        conf_key="openai",
        model_id="gpt-5.6-sol",
        api_key_env="OPENAI_API_KEY",
        provider_block={
            "api": "responses",
            "stateful": False,
            "params": {"reasoning_effort": "medium", "max_tokens": 4096},
        },
        # OpenAI solo cachea prefijos >= 1024 tokens; el prompt del proyecto ronda ese umbral.
        cache_expectation="best_effort",
        cache_min_prefix_tokens=1024,
    ),
    LiveProvider(
        name="mistral",
        conf_key="mistral",
        model_id="mistral-medium-3.5",
        api_key_env="MISTRAL_API_KEY",
        # temperature 0 es rechazada por el modelo ("top_p must be 1 when using greedy sampling").
        provider_block={
            "reasoning_effort": "high",
            "params": {"temperature": 0.3, "max_tokens": 4096},
        },
        cache_expectation="strict",
    ),
    LiveProvider(
        name="mistral-zai",
        conf_key="mistral",
        model_id="zai-glm-5-3",
        api_key_env="MISTRAL_API_KEY",
        provider_block={
            "reasoning_effort": "high",
            "params": {"temperature": 0.3, "max_tokens": 4096},
        },
        cache_expectation="strict",
    ),
    LiveProvider(
        name="gemini",
        conf_key="gemini",
        model_id="gemini-3.8-flash",
        api_key_env="GEMINI_API_KEY",
        provider_block={"params": {"temperature": 0.3, "max_tokens": 4096}},
        # El GeminiModel de Strands no acepta CacheConfig; Gemini cachea prefijos de forma
        # implícita y solo informa de ``cached_content_token_count`` cuando le conviene.
        cache_expectation="none",
        cache_configurable=False,
    ),
)

REGISTRY_BY_NAME: dict[str, LiveProvider] = {provider.name: provider for provider in REGISTRY}


def run_e2e_enabled(env: Mapping[str, str] | None = None) -> bool:
    env = os.environ if env is None else env
    return env.get(RUN_E2E_ENV) == "1"


def select_providers(env: Mapping[str, str] | None = None) -> list[LiveProvider]:
    """Proveedores pedidos por ``SHELL_SENTINEL_E2E_PROVIDERS`` (todos si no se define)."""

    env = os.environ if env is None else env
    raw = (env.get(PROVIDERS_ENV) or "").strip()
    if not raw:
        return list(REGISTRY)
    selected: list[LiveProvider] = []
    for token in raw.split(","):
        name = token.strip()
        if not name:
            continue
        if name not in REGISTRY_BY_NAME:
            known = ", ".join(sorted(REGISTRY_BY_NAME))
            raise pytest.UsageError(
                f"{PROVIDERS_ENV}: proveedor desconocido {name!r}; válidos: {known}"
            )
        if REGISTRY_BY_NAME[name] not in selected:
            selected.append(REGISTRY_BY_NAME[name])
    return selected


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise pytest.UsageError(f"{name} debe ser un entero, se recibió {raw!r}") from exc


def _float_env(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise pytest.UsageError(f"{name} debe ser numérico, se recibió {raw!r}") from exc


def max_model_calls(provider: LiveProvider, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    return _int_env(env, MAX_MODEL_CALLS_ENV, provider.max_model_calls)


def turn_timeout(provider: LiveProvider, env: Mapping[str, str] | None = None) -> float:
    env = os.environ if env is None else env
    return _float_env(env, TURN_TIMEOUT_ENV, provider.turn_timeout_s)


def live_params(env: Mapping[str, str] | None = None) -> list[Any]:
    """``pytest.param`` por proveedor seleccionado, saltando los que no tienen clave."""

    env = os.environ if env is None else env
    params = []
    for provider in select_providers(env):
        marks = []
        if not env.get(provider.api_key_env):
            marks.append(
                pytest.mark.skipif(True, reason=f"{provider.api_key_env} no está definida")
            )
        params.append(pytest.param(provider, id=provider.name, marks=marks))
    return params


__all__ = [
    "MAX_MODEL_CALLS_ENV",
    "PROVIDERS_ENV",
    "REGISTRY",
    "REGISTRY_BY_NAME",
    "RUN_E2E_ENV",
    "TURN_TIMEOUT_ENV",
    "LiveProvider",
    "live_params",
    "max_model_calls",
    "run_e2e_enabled",
    "select_providers",
    "turn_timeout",
]
