# Changelog

All notable changes to Shell Sentinel are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-29

### Added

- Automated test suite (~104 cases) with `pytest`, `pytest-asyncio`, and coverage reporting.
- GitHub Actions CI workflow (lint + tests on Python 3.12) and CodeQL analysis.
- Reproducible dependency management with `pip-tools` (`make lock`, versioned lockfiles).
- Dependency documentation in `docs/dependencies.md` (ES/EN/DE).
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

[1.1.0]: https://github.com/ibitato/ShellSentinel/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/ibitato/ShellSentinel/releases/tag/1.0.0
