# AGENTS — Shell Sentinel

## Documentation languages

Shell Sentinel splits documentation into two tiers. Follow this on every change:

| Tier | Scope | Languages | Examples |
|------|--------|-----------|----------|
| **Project & collaboration** | Repo governance, contributor/agent guidance, changelog, security, GitHub templates | **English only** | `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `docs/README.md`, `docs/website_seo.md` |
| **Product & operations** | End-user and operator flows, install/run guides, dependency how-tos, static website copy | **EN + ES + DE** (always in sync) | `README_es.md`, `README_de.md`, `docs/user_guide_*.md`, `docs/dependencies_*.md`, `docs/custom_model_providers_*.md`, `website/manuals/*`, `website/assets/js/translations.js`, `conf/locales/*` |

### Document map (edge cases)

| Document | Tier | Languages | Notes |
|----------|------|-----------|-------|
| `CONTRIBUTING.md`, `AGENTS.md`, `CHANGELOG.md` | Project | EN | Canonical collaboration policy |
| `contributor-handbook-*.html` | Product | EN/ES/DE | Public onboarding; English handbook + `CONTRIBUTING.md` remain canonical for policy |
| `project-overview-*.html` | Product | EN/ES/DE | Mission, stack and operator workflow |
| `custom-providers-*` / `custom_model_providers_*` | Product | EN/ES/DE | Technical operator guides |
| `system_prompts/` | Runtime | ES | Provider prompts (not end-user docs) |
| Code comments / docstrings | Source | ES | API identifiers stay in English |

- **Code:** identifiers and public APIs in English; comments and docstrings in Spanish (existing convention).
- **System prompts:** keep provider prompts in `system_prompts/` in Spanish unless a provider explicitly requires another language.
- **Plugins:** document inside the plugin directory; plugin UI strings must register translations for `en`, `es`, and `de`.

When a feature touches operators or end users, update **all three** product locales before merging. When it touches process, tooling, or repo policy, update **English** project docs only.

## Project goal

Terminal application that keeps a persistent SSH/SFTP session against a remote server and exposes an AI agent that turns natural-language instructions into administrative actions on that server.

## Technical environment

- **Language:** Python 3.12
- **Application type:** interactive CLI
- **TUI framework:** [Textual 8.2.7](https://textual.textualize.io)
- **Agentic stack:** [Strands Agents SDK](https://github.com/strands-agents/sdk-python) + [`strands-agents-tools`](https://github.com/strands-agents/tools)
- **Local run:** `python -m smart_ai_sys_admin` or `make run`
- **Dependencies:** `pyproject.toml` (source of truth), `requirements*.txt` lockfiles via `pip-tools` (`make lock`). Reproducible install with `make install` / `pip-sync`. See `docs/dependencies_en.md`, `docs/dependencies_es.md`, and `docs/dependencies_de.md`.
- **Code layout:** `src/`-based distribution

## Development tooling

- **Formatting:** `black`
- **Linting:** `ruff`
- **Tests:** `pytest` (suite in `tests/`, CI on Python 3.12)
- **Makefile targets:** `install`, `install-prod`, `lock`, `lock-upgrade`, `sync-deps`, `format`, `lint`, `test`, `test-mistral`, `run`, `clean`
- **MCP tools:** [Firecrawl](https://www.firecrawl.dev/) for web search, scraping and structured extraction when debugging third-party libraries or validating external docs

## Configuration and content

- All adjustable values live under `conf/` (default `conf/app_config.json`). Do not hardcode parameters when they belong in configuration.
- Shortcuts, colours, messages, sizes and history limits are read only from `conf/`. Document new options in the **English** `README.md` and sync **product** README translations (`README_es.md`, `README_de.md`) when behaviour visible to operators changes.
- Visible UI strings use `conf/locales/<lang>/strings.json`. Use `_('key')` from `smart_ai_sys_admin.localization` for new strings and add translations for `en`, `de`, and `es`. `{{dotted.key}}` references inside `conf/app_config.json` are resolved automatically — never replace them with literals.
- Active locale: `SMART_AI_SYS_ADMIN_LOCALE`, else system locale (fallback English). New locales require a `conf/locales/` directory plus product docs in all supported languages where applicable.
- Keep **product** docs aligned on functional or stack changes: `docs/user_guide_{en,es,de}.md`, `README_es.md`, `README_de.md`, and `website/` (`manuals/`, `translations.js`).
- Override config path with `SMART_AI_SYS_ADMIN_CONFIG_FILE` or `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- Strands agent config: `conf/agent.conf` from `conf/agent.conf.example`; respect `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE`. Example defaults: `max_completion_tokens` (OpenAI) 32 768, `max_tokens` (Bedrock) 8 192, `remote_command.timeout_seconds` 900, `remote_command.max_output_chars` 120 000.
- Plugins load from `plugins/` (`SMART_AI_SYS_ADMIN_PLUGINS_DIR`). Each plugin exposes `register(registry)`, registers translations and `PluginSlashCommand` handlers returning Markdown.
- New plugins: document install/usage **inside the plugin directory** only; do not add plugin-specific docs to general manuals.
- Source-available licence: no modifying or redistributing altered versions without permission.
- Long-running remote work: instruct the model to pass `timeout_seconds` to `remote_ssh_command` when expected runtime exceeds 15 minutes. Tune `remote_command.max_output_chars` for large log dumps.
- File transfer: `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` on the active connection. `/connect` opens SSH immediately; SFTP is opened on demand when a transfer runs.
- `/connect` passwords are redacted in logs and echoed TUI input via `smart_ai_sys_admin.security.redaction`.
- Use `local_datetime()` at the start of each turn when local time context helps (show to the operator only if they ask).
- Adapt commands and transfers to the remote OS (GNU/Linux, Unix, Windows PowerShell/cmd).
- Logging from `conf/app_config.json`, default `DEBUG`; use `smart_ai_sys_admin.*` loggers.
- Never store API keys in JSON; use `OPENAI_API_KEY`, `AWS_*`, etc. Document new providers in **product** guides (EN/ES/DE).
- Provider system prompts in `system_prompts/` (Spanish). Update references on rename.
- LM Studio: OpenAI-compatible mode; run `lms server start`, configure `providers.lmstudio` in `conf/agent.conf`.
- Example model `openai/gpt-oss-20b`: `max_context_length = 131072`; `max_completion_tokens` set accordingly in config.
- Cerebras: official SDK; configure `providers.cerebras`, set `CEREBRAS_API_KEY` or `api_key_env`.
- Mistral AI: official `mistralai` SDK via `ShellMistralModel`; configure `providers.mistral`, set `MISTRAL_API_KEY` or `api_key_env`, defaults `reasoning_effort=high` and `max_tokens=16184`.
- Enable `mcp` only when declared servers are available; startup fails otherwise.
- New dependencies: edit `pyproject.toml`, run `make lock` (or `make lock-upgrade` when resolving version conflicts), validate with `make test`. Do not hand-edit `requirements*.txt`.
- Custom model providers: read `docs/custom_model_providers_en.md` (and `docs/custom_model_providers_es.md`, `docs/custom_model_providers_de.md`) before changing `smart_ai_sys_admin.agent`.
- Static site `website/`: sync every product-facing change across EN/ES/DE.

## Recommended workflow

1. Activate virtualenv: `source .venv/bin/activate`
2. Install: `make install`
3. Before opening a PR: `make format`, `make lint`, `make test`
4. After `pyproject.toml` dependency changes: `make lock` (or `make lock-upgrade`) and commit updated `requirements*.txt`
5. Validate TUI: `make run`; validate website: `make website-serve`

## Conventions

- Source under `src/smart_ai_sys_admin/`, tests under `tests/`
- Comments and internal documentation in Spanish; identifiers and API names in English
- Retro palette (green input, orange output) via configuration
- Prefer Textual components; document new widgets in configuration
- No global dependencies; everything in the project virtualenv
- Small cohesive modules (`ui/`, `commands/`, `connection/`); avoid monoliths
- `smart_ai_sys_admin/agent/` encapsulates Strands (config, factory, runtime, tools)
- `remote_ssh_command` and `remote_sftp_transfer` reuse `SSHConnectionManager` — no parallel SSH/SFTP clients
