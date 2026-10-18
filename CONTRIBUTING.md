# Contributing to Shell Sentinel

Thanks for considering a contribution.

## Documentation languages

Shell Sentinel maintains two documentation tiers:

### Project & collaboration (English only)

Keep these in **English** when you change them:

- `README.md` (canonical GitHub readme)
- `CHANGELOG.md`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `AGENTS.md`, `.github/copilot-instructions.md`
- `.github/` issue and PR templates
- `docs/README.md` (documentation index)
- `docs/website_seo.md` (static site SEO conventions)

### Product & operations (English, Spanish, German)

Keep these **in sync across EN, ES, and DE** when behaviour or operator-facing flows change:

- `README_es.md`, `README_de.md`
- `docs/user_guide_en.md`, `docs/user_guide_es.md`, `docs/user_guide_de.md`
- `docs/dependencies_en.md`, `docs/dependencies_es.md`, `docs/dependencies_de.md`
- `docs/custom_model_providers_en.md`, `docs/custom_model_providers_es.md`, `docs/custom_model_providers_de.md`
- `website/manuals/` locale variants (`user-guide-*`, `plugin-development-*`, `custom-providers-*`, `project-overview-*`, `contributor-handbook-*`) and `website/assets/js/translations.js`
- `conf/locales/en`, `conf/locales/es`, `conf/locales/de`

### Product manuals on the website (trilingual)

These are **product** docs, not canonical collaboration policy (see `CONTRIBUTING.md` in English):

| Manual family | Purpose |
|---------------|---------|
| `contributor-handbook-*` | Public contributor onboarding |
| `project-overview-*` | Mission, stack and workflow |
| `custom-providers-*` | Custom LLM provider integration |

If a change is user-visible in the TUI or on the website, update all three product languages before merging. If it only affects contributors or CI, English project docs are enough.

## Ground rules

- Keep changes narrow and reviewable
- Update docs when behaviour changes (see language policy above)
- Do not commit secrets or credentials

## Before opening a pull request

- `make format`, `make lint`, and `make test` pass locally
- Lockfiles updated if `pyproject.toml` dependencies changed (`make lock` or `make lock-upgrade`)
- Optional integration check: `make test-mistral` when validating Mistral (requires `MISTRAL_API_KEY`; the PoC tests are marked `e2e`, so `make test` and CI never run them)
- Optional live end-to-end check: `make test-e2e-live` when touching the TUI, the agent runtime or a provider (see below; not run in CI)
- Docs match the new behaviour in the correct language tier

## Running end-to-end tests

`tests/e2e` drives the real Textual app, `AgentRuntime` and `strands.Agent` against an in-process paramiko SSH/SFTP server (`tests/e2e/ssh_server.py`). There are two layers:

- **Offline** (`tests/e2e/offline`, marker `e2e_offline`): a scripted Strands model (`tests/e2e/fake_model.py`) replaces the provider, so the suite is deterministic, needs no keys and runs inside `make test` and CI. `make test-e2e` runs only this layer.
- **Live** (`tests/e2e/live`, marker `e2e`): the real provider answers operator prompts such as "dame las características hardware de este servidor". It is excluded by default and only runs with `RUN_E2E=1` plus the provider keys in the environment (`OPENAI_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`); providers without a key are skipped. A Strands hook caps model calls per test (`SHELL_SENTINEL_E2E_MAX_MODEL_CALLS`, default 12) and each turn has a wall-clock timeout (`SHELL_SENTINEL_E2E_TURN_TIMEOUT`, default 180 s), so a looping agent fails fast instead of spending tokens. Select providers with `SHELL_SENTINEL_E2E_PROVIDERS=openai,mistral,mistral-zai,gemini` (the registry lives in `tests/e2e/providers.py`; default: all with a key); `SHELL_SENTINEL_E2E_SFTP=1` enables the optional SFTP scenario.

Keys are read from the environment only; never put them in configuration files or test fixtures. Typical invocations:

```bash
source ~/.config/llm-api-keys && make test-e2e-live
```

```bash
RUN_E2E=1 SHELL_SENTINEL_E2E_PROVIDERS=mistral pytest tests/e2e/live -m e2e --no-cov -x -ra
```

A full live run costs roughly 60–80k mostly-cached input tokens and a few thousand output tokens per provider. CI never runs the live layer and has no provider secrets.

## Pull request guidance

A good PR should explain:

- what changed
- why it changed
- how it was verified
- which documentation files were updated (and which locales)

## Issues before PRs

For larger changes, open an issue first so the direction can be aligned before implementation.

## Licensing note

By contributing, you agree that your contribution may be distributed under the repository licence.
