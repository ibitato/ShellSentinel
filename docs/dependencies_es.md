# Gestión de dependencias

Shell Sentinel usa **pip-tools** con un único origen de verdad y lockfiles versionados.

**Versión de Python:** 3.12 (ver `.python-version` y `requires-python` en `pyproject.toml`).

## Fuente de verdad

| Fichero | Rol |
|---------|-----|
| `pyproject.toml` | Dependencias directas (runtime y `dev`). Edítalo al añadir o cambiar librerías. |
| `requirements.txt` | Lock de **ejecución** (generado). Incluye transitivas pinadas. |
| `requirements-dev.txt` | Lock de **desarrollo** (generado). Incluye runtime + herramientas de lint/test/lock. |

No edites los `requirements*.txt` a mano salvo tras resolver conflictos de merge; regenera con `make lock` o `make lock-upgrade` cuando necesites actualizar versiones fijadas.

## Instalación

```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install          # desarrollo (recomendado)
# make install-prod   # solo runtime
```

`make install` ejecuta `pip-sync` contra `requirements-dev.txt` y luego `pip install -e . --no-deps`.

## Añadir o actualizar dependencias

1. Modifica `[project.dependencies]` o `[project.optional-dependencies.dev]` en `pyproject.toml`.
2. Regenera locks con Python 3.12:
   ```bash
   make lock          # actualización incremental de pins
   # make lock-upgrade   # actualiza todos los pins (conflictos de versiones)
   ```
3. Sincroniza el entorno:
   ```bash
   make sync-deps
   ```
4. Ejecuta `make lint` y `make test`. `make test` ejecuta las suites unitaria, de integración y end-to-end offline sin ninguna clave API (la PoC de Mistral y las pruebas e2e live llevan el marcador `e2e` y quedan excluidas por defecto); `make test-e2e-live` necesita `RUN_E2E=1` más `OPENAI_API_KEY`/`MISTRAL_API_KEY`/`GEMINI_API_KEY`; los escenarios MCP requieren además `FIRECRAWL_API_KEY` y Node.js (`npx`).

## Transitivas críticas

Estas librerías están declaradas explícitamente en `pyproject.toml` para auditoría y estabilidad (además de llegar por Strands/Paramiko). `strands-agents` se instala con los extras `gemini`, `mistral`, `openai` y `ollama`, que arrastran los SDK de cada proveedor (`google-genai`, `mistralai`, `openai`, `ollama`):

- `boto3` — Amazon Bedrock (vía Strands)
- `openai` — proveedor OpenAI / LM Studio compatible (versión mayor fijada)
- `mistralai` — Mistral La Plateforme (extra `strands-agents[mistral]`; versión mayor fijada)
- `cerebras_cloud_sdk` — proveedor Cerebras
- `mcp` 2.x y `httpx2` — transportes MCP (`stdio`, `sse`, `streamable_http`); el antiguo pin `mcp<2` ya no existe
- `PyJWT>=2.15.0` — versión mínima de seguridad de la dependencia JWT
- `cryptography` — Paramiko, JWT, MCP

El lockfile fija las versiones exactas de todo el árbol.

## CI

GitHub Actions ejecuta lint y tests en **Python 3.12** en cada pull request (`.github/workflows/ci.yml`, `make install PYTHON_BOOTSTRAP=python`).

## Alternativa sin lock (no recomendada)

```bash
pip install -e ".[dev]"
```

Instala rangos `>=` sin reproducibilidad exacta; úsalo solo para experimentos locales.
