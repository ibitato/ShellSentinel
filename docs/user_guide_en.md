# User Guide — Shell Sentinel (EN)

## Overview
Shell Sentinel is a terminal application that keeps a persistent SSH/SFTP session against a remote server and provides an AI assistant that turns natural-language instructions into safe administrative actions.

## Requirements
- Color-capable terminal (preferably `xterm` or `xterm-256color`).
- Python 3.12.
- Access to a server exposing SSH/SFTP.

## Installation
1. **Create a virtual environment**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   make install
   ```

## Language configuration
The application detects the language by reading `SMART_AI_SYS_ADMIN_LOCALE`; if it is unset, it falls back to the system locale (default: English).

Examples:
```bash
export SMART_AI_SYS_ADMIN_LOCALE=en   # English
export SMART_AI_SYS_ADMIN_LOCALE=es   # Spanish
export SMART_AI_SYS_ADMIN_LOCALE=de   # German
```

## Launching the app
```bash
make run
```

A welcome screen appears on startup and closes automatically after 5 seconds or when you press any key.

## Interface layout
- **Conversation panel**: renders Markdown responses from the assistant.
- **Input area**: multi-line editor; press `Ctrl+S` (default) to submit.
- **Footer**: shows the current SSH status, the active LLM provider and model (for example "Google Gemini · gemini-3.8-flash") and whether the agent is thinking.

## Core commands
Commands are available in English, Spanish and German.

- `/connect <host> <user> <password|key_path> [port]` — open the remote SSH session (optional port, defaults to 22). SFTP opens automatically on the first file transfer.
- `/disconnect` — close the active connection.
- `/help` — display a summary of commands.
- `/status` — display the current agent and connection status.
- `/exit` — open the confirmation dialog to quit.

Useful aliases: `/conectar`, `/desconectar`, `/ayuda`, `/salir`, `/verbinden`, `/trennen`, `/hilfe`, `/beenden`.

## Working with the AI assistant
Type any natural-language instruction. If it is not a slash command, the Strands agent will process it. Examples:
- "List the top CPU processes".
- "Upload `/tmp/script.sh` to `/home/ubuntu/bin/script.sh`".

The agent reuses the active SSH session to run remote commands. File transfers open SFTP on demand through the same connection; relative remote paths are resolved under the SFTP home directory of the connected user and missing parent directories are created there.

While the agent (or `/connect`) is working, the interface stays responsive and the footer shows the thinking indicator, but any new submission is rejected with a notice until the current one finishes. Remote commands are capped by `remote_command.timeout_seconds` (default 900 s of **total** runtime, not idle time); for longer tasks ask the agent to pass a larger `timeout_seconds`.

## Configuration reference
- `conf/app_config.json` stores styling, prompts and shortcuts using placeholders such as `{{ui.output_panel.title}}`, automatically resolved for the active locale.
- Translations live in `conf/locales/<lang>/strings.json`. When adding new strings, call `_('key')` in the code and create entries for every supported language.
- `conf/agent.conf` defines the LLM provider, tools and timeouts. Copy `conf/agent.conf.example` before customising it.
- OpenAI supports `api: "chat_completions"` (default) and `api: "responses"`. Shared `max_tokens` and `reasoning_effort`/`reasoning.effort` values are normalised to `max_completion_tokens` or `max_output_tokens` and the reasoning shape required by the endpoint. Use Responses for GPT-5.x function tools with reasoning; Chat Completions may reject that combination or return zero reasoning tokens. Optional `stateful` mode can reuse `previous_response_id`, but reconstructed multi-turn `reasoningContent` does not yet retain full reasoning continuity.
- Keep `OPENAI_API_KEY` in the environment. The example uses `gpt-5.6-sol`, Responses, `medium` reasoning and `max_tokens: 32768` (effective `max_output_tokens`); the real configuration uses `65536`. Bedrock remains at `max_tokens: 8192`, `remote_command.timeout_seconds` at `900` and `remote_command.max_output_chars` at `120000`.
- For `lmstudio`, run `lms server start` and adjust `base_url`/`api_key`. For `cerebras`, export `CEREBRAS_API_KEY` (or set `api_key_env`) and configure `client_args`/`params`; the official SDK streams SSE events. For Mistral (`provider: "mistral"`), export `MISTRAL_API_KEY` and use defaults `reasoning_effort: high` and `max_tokens: 16184` with `mistral-medium-3.5`. For Google Gemini (`provider: "gemini"`), export `GEMINI_API_KEY` (or `GOOGLE_API_KEY`, or set `api_key_env`) and review `providers.gemini`: the example uses `gemini-3.8-flash` with `temperature: 0.3` and `max_tokens: 16384` (sent as `max_output_tokens`); extra `params` go to `GenerateContentConfig` and `client_args` to the `google-genai` client (`vertexai: true` with `project`/`location` for Vertex AI).
- Prompt caching: each provider block accepts an optional `cache` object (`enabled`, `strategy`, `ttl`, `system_prompt_ttl`, `tools_ttl`, `cache_key`) mapped to Strands' `CacheConfig`. Bedrock defaults to `enabled: true` with `strategy: "auto"` (cache points are injected only for Claude model ids). OpenAI and Mistral default to `enabled: true` and only send a stable `prompt_cache_key` derived from the configuration path and `model_id`; pin `cache_key` or set it to `false` to opt out. LM Studio is disabled unless enabled explicitly; Ollama, Cerebras and Gemini ignore the block with a logged warning (Gemini caches prefixes implicitly and its reported cached tokens still appear in `/status`). `/status` reports whether caching is active and the cached vs total input tokens of the last turn.
- Turn limit: `agent.max_turns` (default `25`) caps the turns, each one a model call plus the tools it requests, that the agent may spend on one instruction. When it is reached the agent stops cleanly, the panel appends a warning suggesting a narrower instruction and a WARNING is logged; `null` or `0` disables the cap and `/status` shows the active value.
- Local tools: `tools.default` lists which Strands Agents Tools are registered (`shell`, `file_read`, `file_write`, `sleep` in the example); only those are enabled, and omitting the key enables all of them. `remote_ssh_command`, `remote_sftp_transfer` and `local_datetime` are always available.
- MCP servers: each transport under `mcp.transports` accepts `timeout_seconds` (default `30`), which bounds the server startup and, for `sse`/`streamable_http`, the HTTP connect timeout. Servers start in parallel; `/status` lists each one with its state and tool count.

## Troubleshooting
- **Colors look wrong / warning about terminal**: check `TERM` and switch to `xterm-256color` if needed.
- **Agent not responding**: verify `conf/agent.conf`, provider credentials and logs under `logs/app.log`.
- **"No active SSH connection" errors**: run `/connect` before asking the agent to execute remote actions.
- **SFTP or file transfer fails after a successful `/connect`**: the remote shell may print banners or MOTD on non-interactive sessions (for example `pyfiglet` in `~/.bashrc`). Wrap decorative output in an interactive check (`[[ $- == *i* ]]`) or ask the server admin to use `Subsystem sftp internal-sftp` in `sshd_config`.
- **Credentials in logs**: passwords passed to `/connect` are masked as `***` in `logs/app.log` and in echoed command input.
- **The agent stopped with a turn-limit warning**: the instruction needed more than `agent.max_turns` turns, or the model looped requesting tools (for example with empty arguments). Split the request into smaller instructions; if the task legitimately needs more steps, raise `agent.max_turns` in `conf/agent.conf`. `logs/app.log` records the stop at WARNING.
- **An MCP server did not start**: the conversation panel shows a warning at startup and `/status` lists every configured MCP server with its state. The message names the cause and what to do:
  - *command not found*: install the `command` (for example `uvx` or `npx`) or add it to `PATH`.
  - *exited before completing the MCP handshake*: run the command by hand to see its errors and review `args` and `env`.
  - *rejected the credentials (HTTP 401/403)*: check `headers` and the token.
  - *no MCP endpoint (HTTP 404)*: check the `url` path and the transport `type` (`sse` vs `streamable_http`).
  - *cannot connect*: make sure the server is running and the `url` is correct.
  - *no response within N s*: the server is slow or hung; check it and raise `timeout_seconds` if it needs longer to start.
  - *environment variables not set*: export the variables listed in `env_passthrough` before launching the TUI.
  The agent still starts; only that server's tools are missing. `logs/app.log` keeps the full trace.
