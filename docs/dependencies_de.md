# Abhängigkeitsverwaltung

Shell Sentinel nutzt **pip-tools** mit einer einzigen Quelle der Wahrheit und versionierten Lockfiles.

**Python-Version:** 3.12 (siehe `.python-version` und `requires-python` in `pyproject.toml`).

## Quelle der Wahrheit

| Datei | Rolle |
|-------|-------|
| `pyproject.toml` | Direkte Abhängigkeiten (Runtime und `dev`). Hier bearbeiten beim Hinzufügen oder Ändern von Bibliotheken. |
| `requirements.txt` | **Runtime**-Lock (generiert). Enthält gepinnte transitive Pakete. |
| `requirements-dev.txt` | **Entwicklungs**-Lock (generiert). Enthält Runtime + Lint/Test/Lock-Tools. |

`requirements*.txt` nicht von Hand bearbeiten (außer nach Merge-Konflikten); mit `make lock` oder `make lock-upgrade` neu generieren, wenn Pins aktualisiert werden sollen.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install          # Entwicklung (empfohlen)
# make install-prod   # nur Runtime
```

`make install` führt `pip-sync` gegen `requirements-dev.txt` aus und danach `pip install -e . --no-deps`.

## Abhängigkeiten hinzufügen oder aktualisieren

1. `[project.dependencies]` oder `[project.optional-dependencies.dev]` in `pyproject.toml` anpassen.
2. Locks mit Python 3.12 neu erzeugen:
   ```bash
   make lock          # inkrementelle Pin-Aktualisierung
   # make lock-upgrade   # alle Pins upgraden (Versionskonflikte)
   ```
3. Umgebung synchronisieren:
   ```bash
   make sync-deps
   ```
4. `make lint` und `make test` ausführen. `make test` führt die Unit-, Integrations- und Offline-End-to-End-Suiten ohne API-Key aus (die Mistral-PoC und die Live-E2E-Tests tragen den Marker `e2e` und sind standardmäßig ausgeschlossen); `make test-e2e-live` benötigt `RUN_E2E=1` plus `OPENAI_API_KEY`/`MISTRAL_API_KEY`/`GEMINI_API_KEY`.

## Kritische transitive Pakete

Diese Bibliotheken sind in `pyproject.toml` explizit deklariert (zusätzlich zu Strands/Paramiko). `strands-agents` wird mit den Extras `gemini`, `mistral`, `openai` und `ollama` installiert, die die Provider-SDKs (`google-genai`, `mistralai`, `openai`, `ollama`) mitbringen:

- `boto3` — Amazon Bedrock (über Strands)
- `openai` — OpenAI / LM Studio-kompatibler Provider (Major-Version gepinnt)
- `mistralai` — Mistral La Plateforme (Extra `strands-agents[mistral]`; Major-Version gepinnt)
- `cerebras_cloud_sdk` — Cerebras-Provider
- `mcp` 2.x und `httpx2` — MCP-Transporte (`stdio`, `sse`, `streamable_http`); der alte Pin `mcp<2` ist entfernt
- `PyJWT>=2.15.0` — Sicherheits-Untergrenze für die JWT-Abhängigkeit
- `cryptography` — Paramiko, JWT, MCP

Das Lockfile pinnt exakte Versionen für den gesamten Abhängigkeitsbaum.

## CI

GitHub Actions führt Lint und Tests auf **Python 3.12** bei jedem Pull Request aus (`.github/workflows/ci.yml`, `make install PYTHON_BOOTSTRAP=python`).

## Ohne Lockfiles (nicht empfohlen)

```bash
pip install -e ".[dev]"
```

Installiert `>=`-Bereiche ohne exakte Reproduzierbarkeit; nur für lokale Experimente verwenden.
