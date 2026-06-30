# Dependency management

Shell Sentinel uses **pip-tools** with a single source of truth and versioned lockfiles.

**Python version:** 3.12 (see `.python-version` and `requires-python` in `pyproject.toml`).

## Source of truth

| File | Role |
|------|------|
| `pyproject.toml` | Direct dependencies (runtime and `dev`). Edit when adding or changing libraries. |
| `requirements.txt` | **Runtime** lock (generated). Includes pinned transitive packages. |
| `requirements-dev.txt` | **Development** lock (generated). Includes runtime + lint/test/lock tools. |

Do not edit `requirements*.txt` by hand except after merge conflicts; regenerate with `make lock`.

## Installation

```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install          # development (recommended)
# make install-prod   # runtime only
```

`make install` runs `pip-sync` against `requirements-dev.txt`, then `pip install -e . --no-deps`.

## Add or update dependencies

1. Edit `[project.dependencies]` or `[project.optional-dependencies.dev]` in `pyproject.toml`.
2. Regenerate locks with Python 3.12:
   ```bash
   make lock
   ```
3. Sync the environment:
   ```bash
   make sync-deps
   ```
4. Run `make lint` and `make test`.

## Critical transitive packages

These libraries are declared explicitly in `pyproject.toml` for auditability and stability (in addition to Strands/Paramiko):

- `boto3` — Amazon Bedrock (via Strands)
- `openai` — OpenAI / LM Studio-compatible provider
- `mistralai` — Mistral La Plateforme (`strands-agents[mistral]` extra)
- `cryptography` — Paramiko, JWT, MCP

The lockfile pins exact versions for the full dependency tree.

## CI

GitHub Actions runs lint and tests on **Python 3.12** on every pull request via `.github/workflows/ci.yml` (`make install PYTHON_BOOTSTRAP=python`).

## Without lockfiles (not recommended)

```bash
pip install -e ".[dev]"
```

Installs `>=` ranges without exact reproducibility; use only for local experiments.
