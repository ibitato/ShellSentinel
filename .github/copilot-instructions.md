# GitHub Copilot Instructions

## Documentation languages

| Tier | Languages | Update when |
|------|-----------|-------------|
| **Project & collaboration** | English only | CI, CONTRIBUTING, AGENTS, CHANGELOG, SECURITY, `docs/README.md`, new config keys for contributors |
| **Product & operations** | English, Spanish, German | User-visible behaviour, install steps, manuals, website copy, `conf/locales/*` |

Canonical English README: `README.md`. Translations: `README_es.md`, `README_de.md`.

## Domain summary

- Shell Sentinel is a Textual TUI that keeps a persistent SSH/SFTP session and exposes it to a Strands agent for remote administration.
- Entrypoint `src/smart_ai_sys_admin/cli.py` sets up logging and delegates to `SmartAISysAdminApp` (`ui/app.py`).
- Natural language is translated into actions on an already-connected server.

## Architecture and flow

- `SmartAISysAdminApp` composes `ConversationPanel`, `CommandInput`, and `ConnectionInfo` (`ui/app.py`, `ui/panels.py`).
- `CommandInput` emits `Submitted`; slash-prefixed input goes to `SlashCommandProcessor` (`ui/commands.py`), otherwise the Strands agent runs.
- `SlashCommandProcessor` handles `/connect`, `/disconnect`, `/help`, aliases; everything else goes to the agent unchanged.
- `SSHConnectionManager` (`connection.py`) wraps Paramiko and holds connection state; do not open alternate Paramiko clients.

## Centralised configuration

- Visual settings, bindings and logging live in `conf/app_config.json`, modelled in `config/__init__.py`, overridable via `SMART_AI_SYS_ADMIN_CONFIG_FILE` or `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- Change colours, bindings or limits in that JSON — never hardcode UI constants.
- Logging writes to `logs/app.log` with `TimedRotatingFileHandler`; `log_to_console` mirrors to stdout without breaking the TUI.

## Strands agent and tools

- `AgentRuntime` (`agent/runtime.py`) loads `conf/agent.conf`, builds the agent via `AgentFactory`, shares `SSHConnectionManager` as `agent.ssh_manager`.
- `conf/agent.conf` defines provider (`bedrock`, `openai`, `local`, …), prompts (`system_prompts/*`), tools and MCP.
- `remote_ssh_command` (`agent/tools.py`) reuses the active session and honours `timeout_seconds`.
- Enable MCP only when remote servers exist; errors in that block stop the agent.

## UI patterns

- `CommandInput` sends on `ctrl+s` (from config) and suggests completions in `_suggestion_for`; update help and suggestions when adding commands.
- `ConversationPanel` keeps bounded history (`history_limit`) and renders retro Markdown — return Markdown from agents and system messages.
- Terminal compatibility banner in `_warn_if_term_incompatible`; adjust allowed terminals in config.

## Development workflow

- `python3.12 -m venv .venv && make install` (`pip-sync` + editable install).
- Dependencies: edit `pyproject.toml`, `make lock`, commit `requirements*.txt`. See `docs/dependencies_en.md`.
- Before PR: `make format`, `make lint`, `make test` (104 cases, CI on Python 3.12).
- Run TUI: `make run` or `python -m smart_ai_sys_admin`; debug agent via `logs/app.log`.

## Common extensions

- New slash commands: `SlashCommandProcessor` — sync `COMMAND_OVERVIEW`, connect help, input suggestions and tests.
- New agent tools: register in `agent/tools.resolve_tools` or enable via `tools.default` in `conf/agent.conf`.
- New configuration fields: document in **English** `README.md` and `AGENTS.md`; sync **product** README translations and user guides (EN/ES/DE) when operators need the detail.
