# Gestión de dependencias

Shell Sentinel usa **pip-tools** con un único origen de verdad y lockfiles versionados.

**Versión de Python:** 3.12 (ver `.python-version` y `requires-python` en `pyproject.toml`).

## Fuente de verdad

| Fichero | Rol |
|---------|-----|
| `pyproject.toml` | Dependencias directas (runtime y `dev`). Edítalo al añadir o cambiar librerías. |
| `requirements.txt` | Lock de **ejecución** (generado). Incluye transitivas pinadas. |
| `requirements-dev.txt` | Lock de **desarrollo** (generado). Incluye runtime + herramientas de lint/test/lock. |

No edites los `requirements*.txt` a mano salvo tras resolver conflictos de merge; regenera con `make lock`.

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
   make lock
   ```
3. Sincroniza el entorno:
   ```bash
   make sync-deps
   ```
4. Ejecuta `make lint` y `make test`.

## Transitivas críticas

Estas librerías están declaradas explícitamente en `pyproject.toml` para auditoría y estabilidad (además de llegar por Strands/Paramiko):

- `boto3` — Amazon Bedrock (vía Strands)
- `openai` — proveedor OpenAI / LM Studio compatible
- `cryptography` — Paramiko, JWT, MCP

El lockfile fija las versiones exactas de todo el árbol.

## CI

GitHub Actions ejecuta lint y tests en **Python 3.12** en cada pull request (`.github/workflows/ci.yml`, `make install PYTHON_BOOTSTRAP=python`).

## Alternativa sin lock (no recomendada)

```bash
pip install -e ".[dev]"
```

Instala rangos `>=` sin reproducibilidad exacta; úsalo solo para experimentos locales.
