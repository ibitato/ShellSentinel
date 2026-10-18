"""E2E live: ``/status`` muestra los aciertos de prompt cache del proveedor real."""

from __future__ import annotations

import pytest

from smart_ai_sys_admin.localization import _
from tests.e2e.live.conftest import LiveSession

# Las cachés de prefijo exigen un mínimo de tokens (Mistral no acertó con ~1.4k; sí con ~3.5k).
# Un contexto largo e idéntico en ambos turnos garantiza un prefijo compartido suficiente.
CONTEXT_PADDING = "\n".join(
    f"Regla operativa {index}: documenta cada comando ejecutado en el servidor remoto y "
    "confirma su código de salida antes de continuar con el siguiente paso."
    for index in range(1, 61)
)
REPEATED_PROMPT = (
    f"Contexto operativo del equipo:\n{CONTEXT_PADDING}\n\n"
    "Teniendo en cuenta estas reglas, ¿qué kernel corre este servidor? Responde en una línea."
)


async def test_status_reports_prompt_cache_hits(connected_live_app: LiveSession, record_property):
    session = connected_live_app

    first = await session.ask(REPEATED_PROMPT)
    session.assert_clean_reply(first)
    second = await session.ask(REPEATED_PROMPT)
    session.assert_clean_reply(second)

    status = await session.driver.submit("/status")
    assert f"- {_('ui.commands.status.cache')}: {_('common.yes')}" in status

    usage = session.driver.runtime.last_cache_usage
    assert usage is not None, status
    record_property("cache_usage", dict(usage))

    expectation = session.provider.cache_expectation
    if expectation == "none":
        return
    if usage["cached_tokens"] == 0 and expectation == "best_effort":
        if usage["input_tokens"] >= session.provider.cache_min_prefix_tokens:
            pytest.xfail(f"{session.provider.name}: sin acierto de caché (best effort): {usage}")
        pytest.skip(f"prefijo demasiado corto para la caché de {session.provider.name}: {usage}")
    assert usage["cached_tokens"] > 0, (usage, status)
    expected_line = _(
        "ui.commands.status.cache_usage",
        cached=f"{usage['cached_tokens']:,}",
        total=f"{usage['input_tokens']:,}",
        percent=usage["percent"],
        written=f"{usage['written_tokens']:,}",
    )
    assert expected_line in status, status
