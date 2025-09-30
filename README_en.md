# Almost Human Sys Admin

Available in: [English](README_en.md) · [Deutsch](README_de.md) · [Español](README.md)

## Overview
Almost Human Sys Admin is a terminal-based, AI-assisted system administrator. It keeps a persistent SSH/SFTP session with a remote server and translates natural-language instructions into safe, auditable actions.

Compatibility note: the Python package and entry point remain `smart_ai_sys_admin` so existing integrations do not break.

## Requirements
- Python 3.10 or newer
- Local virtual environment (recommended `.venv`)

## Getting started
1. Create the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install runtime and development dependencies:
   ```bash
   make install
   ```
3. Run the basic checks:
   ```bash
   make format
   make lint
   ```

## CLI usage
- Launch the TUI with:
  ```bash
  make run
  # or
  python -m smart_ai_sys_admin
  ```
- The console has two main sections: an output history (top) and an input area (bottom), with a footer that always displays the SSH connection status.
- Submit instructions with the configured shortcut (default `Ctrl+S`).
- Supported commands (aliases available in English, Spanish and German):
  - `/connect <host> <user> <password|key_path>` (`/conectar`, `/verbinden`) opens a persistent SSH/SFTP session.
  - `/disconnect` (`/desconectar`, `/trennen`) closes the active connection if any.
  - `/help` (`/ayuda`, `/hilfe`) shows a Markdown summary of all commands.
  - `/exit` (`/salir`, `/beenden`, `/quit`) opens the confirmation dialog before quitting.
- Responses are rendered in Markdown using the retro orange/green palette.
- For best results use an `xterm` or `xterm-256color` terminal.

## Configuration
- Visual and interaction settings (colours, shortcuts, messages, history limits) live in `conf/app_config.json`.
- Override the config location with `SMART_AI_SYS_ADMIN_CONFIG_FILE` (full path) or `SMART_AI_SYS_ADMIN_CONFIG_DIR` (directory containing `app_config.json`).
- Avoid hardcoding values in the source; update the configuration file and restart the app.
- Recent additions to `conf/app_config.json`:
  - `ui.connection_panel`: styles of the footer panel that shows SSH status.
- `logging`: default level `DEBUG`, directory `logs/`, filename `app.log`, rotation policy (daily with 3 backups) using `TimedRotatingFileHandler`.
  - Chatty dependency loggers (`markdown_it`, `botocore.parsers`, `paramiko.transport`, etc.) are lowered to `INFO` when running in `DEBUG` to reduce noise.
  - `log_to_console`: when `true`, mirrors logs to stdout (disabled by default so the TUI is not disrupted).

### Internationalisation
- The interface supports English (default), German and Spanish. The language is detected via `SMART_AI_SYS_ADMIN_LOCALE` or, if unset, the system locale.
- Translatable strings are stored under `conf/locales/<lang>/strings.json`. To add a new language, clone an existing file, translate the keys while keeping `{placeholders}` intact, and register the locale.
- Force the language at runtime:
  ```bash
  export SMART_AI_SYS_ADMIN_LOCALE=de
  make run
  ```
- `conf/app_config.json` contains `{{translation.key}}` placeholders resolved at load time; keep the double braces when customising values.

### AI agent configuration (Strands Agents)
- Copy `conf/agent.conf.example` to `conf/agent.conf` and adjust the `provider` block to select Amazon Bedrock, OpenAI or Ollama/local.
- Each provider ships with its own `system_prompt` in `system_prompts/`. Custom prompts can be referenced by path.
- Copy the example file and set credentials via environment variables (e.g. `export OPENAI_API_KEY="..."`). The config file never stores secrets in plain text.
- OpenAI and Bedrock defaults allow long outputs; the example config sets `max_completion_tokens` (OpenAI) to **32 768** and `max_tokens` (Bedrock) to **8 192**. Adjust to match your account quotas.
- Credentials are read from your environment (`AWS_*`, `OPENAI_API_KEY`, etc.). You can also point to a different file via `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` or reuse `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- The `tools` section enables Strands Agents Tools and the custom `remote_ssh_command`, which reuses the TUI SSH session (the `timeout_seconds` parameter is optional).
- `remote_ssh_command` defaults to **900 seconds (15 minutes)** as defined in `conf/agent.conf`. If you expect longer operations, ask the agent to include the desired `timeout_seconds`.
- To work with Model Context Protocol (MCP) servers, declare each transport (`stdio`, `sse`, `streamable_http`) under `mcp`. The agent keeps those connections alive during the session and exposes their tools automatically.
  - Example: transport `firecrawl-stdio` runs `npx -y firecrawl-mcp`. Use `env_passthrough` so the agent inherits `FIRECRAWL_API_KEY` (or other secrets) and export them before launching the TUI.
- When the app starts you will see a retro welcome screen (orange theme) that closes after 5 seconds or any key press.
- `/connect` sessions keep SSH and SFTP alive. The agent exposes `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` to upload (`upload`/`put`) or download (`download`/`get`) files through the same connection. Rename the tool via `tools.sftp_transfer.name` if needed.
- You can manage GNU/Linux or Windows servers as long as they provide SSH/SFTP. Adjust commands to the target platform (PowerShell/cmd on Windows) and double-check paths when transferring files.

### User manuals
- Practical guides are available in `docs/user_guide_en.md`, `docs/user_guide_es.md` and `docs/user_guide_de.md`. Keep them aligned with the latest features.

## Project structure
- `requirements.txt`: runtime dependencies (Textual, Strands Agents, community tools).
- `requirements-dev.txt`: development dependencies (`-r requirements.txt`, linting, tests).
- `src/smart_ai_sys_admin/`: main application source code (TUI and utilities).
- `tests/`: placeholder for automated tests.
- `Makefile`: helper tasks for install, format, lint, test, run and clean.
- `AGENTS.md`: contribution guide for human collaborators and AI agents.

## Licence
- Free for education, students and teams up to 5 people.
- Larger deployments (more than 5 seats/users) require a commercial licence agreed with the maintainer.
- See `LICENSE` (Almost Human Sys Admin Community License 1.0) for full details, definitions and limitations.

For commercial licence inquiries or extended support, open a GitHub issue or contact the maintainer.
