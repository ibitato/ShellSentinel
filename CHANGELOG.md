# Changelog

Todos los cambios relevantes de Shell Sentinel se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [Semantic Versioning](https://semver.org/lang/es/).

## [1.1.0] - 2026-06-29

### Añadido

- Suite de pruebas automatizada (~104 casos) con `pytest`, `pytest-asyncio` y cobertura.
- Workflow de CI en GitHub Actions (lint + tests en Python 3.12) y análisis CodeQL.
- Gestión reproducible de dependencias con `pip-tools` (`make lock`, lockfiles versionados).
- Documentación de dependencias en `docs/dependencies.md` (ES/EN/DE).
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` y plantillas de issues/PR en `.github/`.
- Manuales web de contribución (`contributor-handbook-en/es/de.html`) y sincronización de guías de usuario.
- Resumen del agente (`agent_summary`) para el comando `/status`.

### Cambiado

- Python fijado en **3.12** (`.python-version`, `requires-python` en `pyproject.toml`).
- Migración a **Textual 8.2.7** con adaptación de widgets TUI (`ConnectionInfo._paint_status`, contenedores `Horizontal`/`Vertical`).
- Actualización de dependencias: Paramiko 5, Strands Agents ≥1.45, urllib3 2, stack de lint/test (Black 26, Ruff 0.15).
- README, `AGENTS.md`, manuales del repo y web estática alineados con el nuevo stack e instalación (`python3.12 -m venv`, `make test` obligatorio).
- Bootstrap del entorno virtual parametrizable (`PYTHON_BOOTSTRAP`) para compatibilidad con GitHub Actions.

### Corregido

- Soporte y salida del comando `/status` cuando el agente no está inicializado o falta configuración.

## [1.0.0] - 2025-10-08

### Añadido

- Primera release pública de Shell Sentinel: TUI conversacional con sesiones SSH/SFTP persistentes, soporte multilingüe (EN/ES/DE) y proveedores LLM configurables.
- Sitio estático en `website/` y documentación de usuario inicial.

[1.1.0]: https://github.com/ibitato/ShellSentinel/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/ibitato/ShellSentinel/releases/tag/1.0.0
