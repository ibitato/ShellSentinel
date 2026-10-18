# Changelog

All notable changes to Shell Sentinel are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Dependencies updated to Strands Agents 1.61.1, Strands Agents Tools 0.8.9 and Textual 8.2.8; lockfiles regenerated. The OpenAI and Mistral SDK majors remain pinned.
- MCP transports migrated to `mcp` 2.x (2.1.1, built on `httpx2`); the temporary `mcp<2` pin is gone. `streamable_http` transports now build an `httpx2` client carrying the configured `headers` and `timeout_seconds` (connect/write/pool; reads keep a 300 s SSE window) and fall back to 30 s when no timeout is set, instead of no connect timeout. `sse` transports now honor `timeout_seconds` as well.
- MCP servers start in parallel and `timeout_seconds` (default 30 s) now also bounds each server's startup, so a hung server no longer blocks the TUI from opening.
- `tools.default` in `conf/agent.conf` is now honored: only the listed Strands Agents Tools are registered (all of them when the key is omitted). Shell Sentinel tools are always registered.
- `remote_ssh_command` timeouts now cap total runtime instead of idle time between reads.

### Added

- Prompt caching per provider through an optional `cache` block in `conf/agent.conf` (`enabled`, `strategy`, `ttl`, `system_prompt_ttl`, `tools_ttl`, `cache_key`), passed to Strands as `CacheConfig`. Enabled by default for Bedrock (`strategy: "auto"`, cache points injected only for Claude model ids), OpenAI and Mistral (a stable `prompt_cache_key` derived from the configuration path and `model_id`, overridable with `cache_key` or disabled with `cache_key: false`); disabled by default for LM Studio; ignored with a logged warning for Ollama and Cerebras. `/status` shows whether caching is active and the cached vs total input tokens of the last turn, which is also logged at INFO.
- When an MCP server fails to start, the conversation panel shows a localized warning naming the cause (command not found, process exited, HTTP 401/403/404, unreachable host, timeout, missing environment variables) and what to fix, and `/status` lists every configured MCP server with its state and tool count. Previously the agent reported success and the log only said `unhandled errors in a TaskGroup`.

### Fixed

- The Mistral provider now reports prompt-cache hits: `ShellMistralModel` copies `prompt_tokens_details.cached_tokens` from the Mistral SDK usage (streaming and non-streaming) into `cacheReadInputTokens`, so `/status` and the INFO log show real cached-token counts instead of always zero.
- Security: PyJWT raised to `>=2.15.0` and lockfiles bumped to Pillow 12.3.0 and soupsieve 3.0.3 to address published advisories.
- The TUI no longer freezes while the agent or `/connect` is running; work runs in a background worker and new submissions are rejected until it finishes.
- SFTP uploads to relative remote paths now create missing directories under the SFTP home instead of `/`.
- Remote commands drain stdout and stderr concurrently, avoiding hangs on large stderr output.
- Quoted `/connect` passwords containing spaces are fully redacted in the conversation panel.
- Removed an un-awaited coroutine triggered on every keystroke in the input editor.
- `smart_ai_sys_admin.__version__` now matches the released version.

## [1.3.0] - 2026-07-27

### Added

- Selectable OpenAI Responses API support through `providers.openai.api`, while preserving Chat Completions as the compatibility default.
- Unit coverage for endpoint-specific parameter normalization and model selection, plus opt-in end-to-end tests for function tools and reasoning tokens.
- Configurable Responses `stateful` mode for server-side `previous_response_id` chaining.

### Changed

- OpenAI model construction now selects `OpenAIModel` or `OpenAIResponsesModel` according to the configured API.
- Shared OpenAI parameters are normalized automatically: `max_tokens` maps to `max_completion_tokens` or `max_output_tokens`, and `reasoning_effort` maps to the endpoint-specific reasoning shape.
- The OpenAI example now uses `gpt-5.6-sol`, Responses, medium reasoning and a 32,768-token output limit; the active local configuration uses 65,536.
- Dependencies updated to Strands Agents 1.50.1, Strands Agents Tools 0.8.5 and OpenAI 2.48.0.
- Product documentation and static-site manuals aligned in English, Spanish and German.

### Fixed

- Avoided the HTTP 400 returned by GPT-5.x when function tools and active reasoning are combined through Chat Completions by routing supported configurations through Responses.
- MCP stdio transports can now receive explicitly allowlisted secrets such as `FIRECRAWL_API_KEY` through `env_passthrough`, without storing credentials in JSON.

### Known limitations

- Responses reasoning blocks do not yet retain full `reasoningContent` continuity when reconstructing multi-turn conversations; `stateful` is available for controlled evaluation.

## [1.2.0] - 2026-06-30

### Added

- First-class `mistral` LLM provider (Mistral La Plateforme) with mandatory `reasoning_effort=high` and default `max_tokens=16184`.
- `ShellMistralModel` wrapper extending Strands `MistralModel` for reasoning injection and thinking stream mapping.
- `system_prompts/mistral.md` and `providers.mistral` block in `conf/agent.conf.example`.
- Integration test suite: `make test-mistral` (requires `MISTRAL_API_KEY`).
- `smart_ai_sys_admin.security.redaction` module to mask `/connect` credentials in logs and echoed TUI input.
- `make lock-upgrade` Makefile target to regenerate lockfiles with dependency upgrades.

### Changed

- `/connect` opens the SSH session immediately; SFTP is opened on demand when the first file transfer runs.

### Fixed

- `/connect` no longer fails when the remote shell prints output during non-interactive sessions (e.g. banners in `.bashrc`) that previously broke the SFTP handshake.
- SSH passwords supplied via `/connect` are redacted from application logs.

## [1.1.1] - 2026-06-29

### Added

- Custom model provider guides in English and German (`docs/custom_model_providers_{en,de}.md`, `custom-providers-{en,de}.html`).
- Project overview manuals in Spanish and German (`project-overview-{es,de}.html`).
- English SEO conventions for the static site (`docs/website_seo.md`).

### Changed

- Language policy codified: English canonical for project/collaboration docs; EN/ES/DE for product and operator documentation.
- `README.md` is now the canonical English readme; `dependencies.md` renamed to `dependencies_es.md`.
- Documentation index cards unified to five manuals per locale (EN/ES/DE) on the static site.
- `CHANGELOG.md` and collaboration meta docs written in English.

## [1.1.0] - 2026-06-29

### Added

- Automated test suite (~104 cases) with `pytest`, `pytest-asyncio`, and coverage reporting.
- GitHub Actions CI workflow (lint + tests on Python 3.12) and CodeQL analysis.
- Reproducible dependency management with `pip-tools` (`make lock`, versioned lockfiles).
- Dependency documentation in `docs/dependencies_{en,es,de}.md`.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, and issue/PR templates under `.github/`.
- Web contributor handbooks (`contributor-handbook-en/es/de.html`) and synced user guides.
- Agent summary (`agent_summary`) for the `/status` command.

### Changed

- Python pinned to **3.12** (`.python-version`, `requires-python` in `pyproject.toml`).
- Migration to **Textual 8.2.7** with TUI widget updates (`ConnectionInfo._paint_status`, `Horizontal`/`Vertical` containers).
- Dependency updates: Paramiko 5, Strands Agents ≥1.45, urllib3 2, lint/test stack (Black 26, Ruff 0.15).
- README, `AGENTS.md`, repo manuals, and static website aligned with the new stack and install flow (`python3.12 -m venv`, mandatory `make test`).
- Parameterised virtualenv bootstrap (`PYTHON_BOOTSTRAP`) for GitHub Actions compatibility.

### Fixed

- `/status` command support and output when the agent is not initialised or configuration is missing.

## [1.0.0] - 2025-10-08

### Added

- Initial public release of Shell Sentinel: conversational TUI with persistent SSH/SFTP sessions, multilingual support (EN/ES/DE), and configurable LLM providers.
- Static site under `website/` and initial user documentation.

[1.3.0]: https://github.com/ibitato/ShellSentinel/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/ibitato/ShellSentinel/compare/1.1.1...1.2.0
[1.1.1]: https://github.com/ibitato/ShellSentinel/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/ibitato/ShellSentinel/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/ibitato/ShellSentinel/releases/tag/1.0.0
