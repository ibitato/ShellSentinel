# Shell Sentinel
![Shell Sentinel TUI running in a retro-themed terminal](screenshots/shell-sentinel-tui-1280x640.png)

Available in: [English](README.md) · [Deutsch](README_de.md) · [Español](README_es.md)

## Overview
Shell Sentinel is a terminal-based, AI-assisted system administrator. It keeps a persistent SSH/SFTP session with a remote server and translates natural-language instructions into safe, auditable actions.

Public repository: <https://github.com/ibitato/ShellSentinel>

Official site: <https://www.shellsentinel.net>.

## Requirements
- Python 3.12
- Local virtual environment (recommended `.venv`; see also `.python-version`)

## Getting started
1. Create the virtual environment:
   ```bash
   python3.12 -m venv .venv
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
   make test
   ```

## CLI usage
- Launch the TUI with:
```bash
make run
```
- The console has two main sections: an output history (top) and an input area (bottom), with a footer that always displays the SSH connection status plus the active LLM provider/model.
- Submit instructions with the configured shortcut (default `Ctrl+S`).
- Supported commands (aliases available in English, Spanish and German):
- `/connect <host> <user> <password|key_path> [port]` (`/conectar`, `/verbinden`) opens a persistent SSH session (optional port, defaults to 22). SFTP opens on the first file transfer.
  - `/disconnect` (`/desconectar`, `/trennen`) closes the active connection if any.
  - `/help` (`/ayuda`, `/hilfe`) shows a Markdown summary of all commands.
  - `/status` (`/estado`) displays the current agent and connection status.
  - `/exit` (`/salir`, `/beenden`, `/quit`) opens the confirmation dialog before quitting.
- Responses are rendered in Markdown using the retro orange/green palette.
- For best results use an `xterm` or `xterm-256color` terminal.

## Configuration
- Visual and interaction settings (colours, shortcuts, messages, history limits) live in `conf/app_config.json`.
- Override the config location with `SMART_AI_SYS_ADMIN_CONFIG_FILE` (full path) or `SMART_AI_SYS_ADMIN_CONFIG_DIR` (directory containing `app_config.json`).
- Avoid hardcoding values in the source; update the configuration file and restart the app.
- Recent additions to `conf/app_config.json`:
  - `ui.connection_panel`: styles of the footer panel that shows SSH status and the active provider summary.
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
- Copy `conf/agent.conf.example` to `conf/agent.conf` and adjust the `provider` block to select Amazon Bedrock, OpenAI, LM Studio, Cerebras, Mistral AI or Ollama/local.
- When you pick LM Studio, start the local server with `lms server start` and review `providers.lmstudio` (`base_url`, `model_id`, `api_key_env`/`api_key`, `client_args`) so it matches your environment.
- For Cerebras, export `CEREBRAS_API_KEY` (or set `api_key_env`), then tune `providers.cerebras` (`model_id`, `params`, `client_args.timeout`, etc.); the custom provider wraps the official SDK with SSE streaming.
- For Mistral AI, export `MISTRAL_API_KEY` (or set `api_key_env`), select `provider: "mistral"` and review `providers.mistral`. Defaults: `model_id: mistral-medium-3.5`, `reasoning_effort: high` (required for reasoning models), `max_tokens: 16184`. Run `make test-mistral` to validate your API key.
- Each provider ships with its own `system_prompt` in `system_prompts/`. Custom prompts can be referenced by path.
- OpenAI supports `providers.openai.api: "chat_completions"` (default, `POST /v1/chat/completions`) and `api: "responses"` (`POST /v1/responses`). LM Studio remains in Chat Completions-compatible mode.
- The shared `max_tokens` setting is normalized to `max_completion_tokens` for Chat Completions and `max_output_tokens` for Responses. Likewise, `reasoning_effort` and `reasoning.effort` are converted to the form expected by the selected endpoint.
- For GPT-5.x models that use function tools and reasoning, select Responses. Chat Completions may return HTTP 400 for that combination or silently report zero reasoning tokens; `reasoning_effort: "none"` avoids the error only by disabling reasoning.
- Optional `stateful` mode can reuse `previous_response_id`, but a known limitation remains: reconstructed multi-turn `reasoningContent` does not yet preserve full reasoning continuity.
- Keep credentials in environment variables and export them before starting the TUI; never store secrets in JSON:
  ```bash
  export OPENAI_API_KEY="..."
  export FIRECRAWL_API_KEY="..."
  ```
- The OpenAI example uses `gpt-5.6-sol`, `api: "responses"`, `reasoning_effort: "medium"` and `max_tokens: 32768` (sent as `max_output_tokens`). The real configuration uses **65,536**; the Bedrock example remains at `max_tokens: 8192`. Adjust these values to your quotas.
- Responses also accepts optional `temperature: 0.3` in `params`; it is not part of the default configuration.
- Credentials are read from your environment (`AWS_*`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, etc.). You can also point to a different file via `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` or reuse `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- The `tools` section enables Strands Agents Tools and the custom `remote_ssh_command`, which reuses the TUI SSH session (the `timeout_seconds` parameter is optional).
- `remote_ssh_command` defaults to **900 seconds (15 minutes)** as defined in `conf/agent.conf`. If you expect longer operations, ask the agent to include the desired `timeout_seconds`.
- To prevent overwhelming responses, set `remote_command.max_output_chars` to cap how many characters are forwarded to the agent. Increase it for audit-heavy workflows or reduce it for shared terminals.
- To work with Model Context Protocol (MCP) servers, declare each transport (`stdio`, `sse`, `streamable_http`) under `mcp`. The agent keeps those connections alive during the session and exposes their tools automatically.
  - Example: transport `firecrawl-stdio` runs `npx -y firecrawl-mcp`. Use `env_passthrough` so the agent inherits `FIRECRAWL_API_KEY` (or other secrets) and export them before launching the TUI.
- When the app starts you will see a retro welcome screen (orange theme) that closes after 5 seconds or any key press.
- `/connect` keeps the SSH session alive; SFTP opens on demand when the agent transfers files. The agent exposes `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` to upload (`upload`/`put`) or download (`download`/`get`) files through the same connection. Passwords supplied to `/connect` are redacted as `***` in logs and echoed input. Rename the tool via `tools.sftp_transfer.name` if needed.
- You can manage GNU/Linux or Windows servers as long as they provide SSH/SFTP. Adjust commands to the target platform (PowerShell/cmd on Windows) and double-check paths when transferring files.

### Plugin system
- Plugins are loaded automatically from the `plugins/` directory (override with `SMART_AI_SYS_ADMIN_PLUGINS_DIR`, supporting multiple paths separated by `:`). Each `.py` file must expose a `register(registry)` function.
- Inside `register(...)` you can add slash commands with `PluginSlashCommand`. The handler receives the list of user arguments and must return Markdown to display in the chat. Any logging you perform is integrated with the application logger.
- Plugins can ship localized strings by calling `registry.register_translations(locale, payload)`. The keys referenced in `description_key`, `usage_key` and `help_key` must exist in those translations so the command stays localized.
- Optionally, a `suggestion(command, args)` callback can be provided to customize the autocomplete text. When omitted, the string resolved by `usage_key` is shown.
- Registered commands appear automatically in `/help`, honor the input history and share the same output rules as the built-in commands.

```python
# plugins/credentials.py
from smart_ai_sys_admin.plugins import PluginRegistry, PluginSlashCommand


def _fetch_credentials(args: list[str]) -> str:
    if not args:
        return "⚠️ Please provide the server name."
    server = args[0]
    # Call your internal API here
    return f"Credentials for `{server}`: user demo / password 1234"


def register(registry: PluginRegistry) -> None:
    registry.register_translations(
        "en",
        {
            "plugins": {
                "credentials": {
                    "description": "Fetch credentials from the internal API",
                    "usage": "Usage: `{command} <server>`",
                    "help": "`{command}` queries the corporate API and prints the credentials in the chat.",
                }
            }
        },
    )

    registry.register_command(
        PluginSlashCommand(
            name="/credentials",
            aliases=("/creds",),
            handler=_fetch_credentials,
            description_key="plugins.credentials.description",
            usage_key="plugins.credentials.usage",
            help_key="plugins.credentials.help",
        )
    )
```

### User manuals
- Practical guides are available in `docs/user_guide_en.md`, `docs/user_guide_es.md` and `docs/user_guide_de.md`. Keep them aligned with the latest features.

## Project structure
- `pyproject.toml`: package metadata and **canonical** dependency definitions (runtime and `dev`).
- `requirements.txt` / `requirements-dev.txt`: generated lockfiles (`make lock`); do not edit by hand.
- `docs/dependencies_en.md`, `docs/dependencies_es.md`, and `docs/dependencies_de.md`: dependency management, lockfiles and CI.
- `CHANGELOG.md`: project version history.
- `src/smart_ai_sys_admin/`: main application source code (TUI and utilities).
- `tests/`: automated test suite (unit and integration).
- `Makefile`: helper tasks for install, lock, lock-upgrade, sync-deps, format, lint, test, test-mistral, run and clean.
- `AGENTS.md`: contribution guide for human collaborators and AI agents.

## Licence
- Shell Sentinel is released as **source-available software**: the GitHub repository allows code inspection but does not authorise modifying the codebase or redistributing altered versions.
- Free of charge strictly for personal, educational or internal evaluation purposes with no direct or indirect commercial gain. Any commercial use requires a separate agreement with the maintainer.
- Modification, adaptation or creation of derivative works is expressly forbidden without prior written consent.
- Refer to `LICENSE` (Shell Sentinel Source-Available License 1.0) for complete terms, definitions and limitations.

For commercial licences, special permissions or extended support, open a GitHub issue or contact the maintainer directly.
