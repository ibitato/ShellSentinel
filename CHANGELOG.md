# Changelog

All notable changes to Shell Sentinel are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
