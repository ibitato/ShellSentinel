# Changelog

All notable changes to Shell Sentinel are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2026-10-19

### Added

- End-to-end coverage for MCP in both e2e layers. Offline (`tests/e2e/offline/test_mcp_flow.py`, part of `make test`): the real TUI launches a scripted `stdio` server built on the `mcp` 2.x SDK (`tests/e2e/mcp_server.py`) plus local HTTP endpoints, and verifies tool registration and calls from the Strands agent, `env_passthrough` (including the warning for missing variables), declared and unexpected tool errors, `/status` output, the startup diagnostics for every failure kind (command not found, process exited, HTTP 401/404, unreachable host, hung handshake) and that server processes are stopped on shutdown. Live (`tests/e2e/live/test_live_mcp_firecrawl.py`, `make test-e2e-live`): the real Firecrawl MCP server (`npx -y firecrawl-mcp`, `FIRECRAWL_API_KEY`, Node.js) is started by the TUI, `firecrawl_scrape` runs through the agent with the scripted model, and each selected provider must pick a Firecrawl tool to read a page. `write_agent_conf` accepts an `mcp` block and `tests/e2e/mcp_support.py` builds the transports.

### Fixed

- An MCP server that accepts the connection but never answers the `initialize` handshake no longer leaves its process running after Shell Sentinel gives up on it. Strands' `MCPClient.stop()` only resolves a future that the client thread awaits once the handshake has completed, so for a hung handshake it blocked forever and the `stdio` subprocess (or HTTP session) outlived the TUI. Every transport now runs inside an anyio `CancelScope` that `MCPManager` cancels when the startup deadline expires: `stdio_client` kills the process tree, the client thread ends cleanly and the server is reported as `timeout` as before. Found by the new offline MCP e2e scenario.

## [1.4.0] - 2026-10-18

### Changed

- Dependencies updated to Strands Agents 1.61.1, Strands Agents Tools 0.8.9 and Textual 8.2.8; lockfiles regenerated. The OpenAI and Mistral SDK majors remain pinned.
- MCP transports migrated to `mcp` 2.x (2.1.1, built on `httpx2`); the temporary `mcp<2` pin is gone. `streamable_http` transports now build an `httpx2` client carrying the configured `headers` and `timeout_seconds` (connect/write/pool; reads keep a 300 s SSE window) and fall back to 30 s when no timeout is set, instead of no connect timeout. `sse` transports now honor `timeout_seconds` as well.
- MCP servers start in parallel and `timeout_seconds` (default 30 s) now also bounds each server's startup, so a hung server no longer blocks the TUI from opening.
- `tools.default` in `conf/agent.conf` is now honored: only the listed Strands Agents Tools are registered (all of them when the key is omitted). Shell Sentinel tools are always registered.
- `remote_ssh_command` timeouts now cap total runtime instead of idle time between reads.

### Added

- Google Gemini provider (`provider: "gemini"`) built on Strands' `GeminiModel` and the official `google-genai` SDK (new `gemini` extra of `strands-agents`; lockfiles regenerated). `providers.gemini` takes `model_id` (the example uses `gemini-3.8-flash`), `params` (passed to `GenerateContentConfig`; the shared `max_tokens` is normalized to `max_output_tokens`), `client_args` (forwarded to the `google-genai` client, so `vertexai: true` with `project`/`location` works without an API key) and `api_key_env` (default `GEMINI_API_KEY`, with `GOOGLE_API_KEY` as fallback; `api_key` in JSON is rejected). A missing key raises a clear configuration error at startup. The footer and `/status` show "Google Gemini"; thoughts stream as reasoning content when `show_thinking` is enabled. Strands' `GeminiModel` does not accept `CacheConfig`, so the `cache` block defaults to disabled and is ignored with a warning when enabled, while cached tokens reported by Gemini still appear in `/status`. The live e2e registry gains a `gemini` row.
- Configurable cap on agent turns per operator instruction: `agent.max_turns` in `conf/agent.conf` (default `25`; `null` or `0` disables it) is passed to the Strands agent as `limits={"turns": N}`. When the cap is reached the invocation ends with `stop_reason: limit_turns` instead of recursing until `RecursionError`, the conversation panel appends a localized warning suggesting a narrower instruction, and the stop is logged at WARNING. `/status` shows the active limit. Covered by unit tests and an offline e2e scenario that replays the 2026-10-18 incident (a model requesting a tool with empty input in a loop).
- End-to-end test suite for the TUI (`tests/e2e`): the real Textual app, `AgentRuntime` and `strands.Agent` run against an in-process paramiko SSH/SFTP server. The offline layer (`e2e_offline`, part of `make test`) uses a scripted Strands model and covers connect/disconnect, remote commands, output truncation, timeouts, SFTP transfers, the busy guard and a regression for tool-call arguments split across streaming deltas; the live layer (`make test-e2e-live`, `RUN_E2E=1` plus `OPENAI_API_KEY`/`MISTRAL_API_KEY`) runs operator scenarios against OpenAI and Mistral with a hook-based cap on model calls. The Mistral PoC tests are now marked `e2e` so `make test` never spends tokens.
- Prompt caching per provider through an optional `cache` block in `conf/agent.conf` (`enabled`, `strategy`, `ttl`, `system_prompt_ttl`, `tools_ttl`, `cache_key`), passed to Strands as `CacheConfig`. Enabled by default for Bedrock (`strategy: "auto"`, cache points injected only for Claude model ids), OpenAI and Mistral (a stable `prompt_cache_key` derived from the configuration path and `model_id`, overridable with `cache_key` or disabled with `cache_key: false`); disabled by default for LM Studio; ignored with a logged warning for Ollama and Cerebras. `/status` shows whether caching is active and the cached vs total input tokens of the last turn, which is also logged at INFO.
- When an MCP server fails to start, the conversation panel shows a localized warning naming the cause (command not found, process exited, HTTP 401/403/404, unreachable host, timeout, missing environment variables) and what to fix, and `/status` lists every configured MCP server with its state and tool count. Previously the agent reported success and the log only said `unhandled errors in a TaskGroup`.

### Fixed

- `ShellMistralModel` no longer splits a streamed tool call into broken `toolUse` blocks when its JSON arguments arrive over several deltas. Models served by Mistral such as `zai-glm-5-3` send the tool-call `id` and name only in the first fragment; the following fragments carry the SDK default id `"null"`, so grouping by id produced one block with unparseable JSON and one without id or name, `remote_ssh_command` ran with an empty input and the agent retried until Strands raised `RecursionError`. Fragments are now grouped by `index` (or real `id`) and appended to the last open call when neither is usable, parallel tool calls stay separate, dict arguments are serialized to JSON, and a warning naming the tool is logged if the reassembled call still has no id, no name or invalid JSON arguments.
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
