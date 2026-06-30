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
- **Footer**: shows the current SSH status and whether the agent is thinking.

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

The agent reuses the active SSH session to run remote commands. File transfers open SFTP on demand through the same connection.

## Configuration reference
- `conf/app_config.json` stores styling, prompts and shortcuts using placeholders such as `{{ui.output_panel.title}}`, automatically resolved for the active locale.
- Translations live in `conf/locales/<lang>/strings.json`. When adding new strings, call `_('key')` in the code and create entries for every supported language.
- `conf/agent.conf` defines the LLM provider, tool options and timeouts. Copy `conf/agent.conf.example` before customizing it and, when selecting `lmstudio`, start the local server with `lms server start` and adjust `base_url`/`api_key` to match your setup. For `cerebras`, export `CEREBRAS_API_KEY` (or set `api_key_env`) and tweak `client_args`/`params`; the integration wraps the official SDK with SSE streaming support. For `mistral`, export `MISTRAL_API_KEY`, set `provider: "mistral"` and use defaults `reasoning_effort: high` and `max_tokens: 16184` with model `mistral-medium-3.5`. Use `remote_command.max_output_chars` to control how much stdout/stderr the agent receives.

## Troubleshooting
- **Colors look wrong / warning about terminal**: check `TERM` and switch to `xterm-256color` if needed.
- **Agent not responding**: verify `conf/agent.conf`, provider credentials and logs under `logs/app.log`.
- **"No active SSH connection" errors**: run `/connect` before asking the agent to execute remote actions.
- **SFTP or file transfer fails after a successful `/connect`**: the remote shell may print banners or MOTD on non-interactive sessions (for example `pyfiglet` in `~/.bashrc`). Wrap decorative output in an interactive check (`[[ $- == *i* ]]`) or ask the server admin to use `Subsystem sftp internal-sftp` in `sshd_config`.
- **Credentials in logs**: passwords passed to `/connect` are masked as `***` in `logs/app.log` and in echoed command input.
