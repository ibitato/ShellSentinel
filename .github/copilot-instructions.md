# GitHub Copilot Instructions

## Resumen del dominio
- Almost Human Sys Admin es una TUI en Textual que mantiene una sesión SSH/SFTP persistente y la expone a un agente Strands para ejecutar instrucciones remotas.
- El entrypoint `src/smart_ai_sys_admin/cli.py` prepara el logging y delega en `SmartAISysAdminApp` (`ui/app.py`).
- El objetivo es traducir lenguaje natural en acciones de administración sobre un servidor ya conectado.

## Arquitectura y flujo
- `SmartAISysAdminApp` crea tres widgets clave: `ConversationPanel`, `CommandInput` y `ConnectionInfo`, organizados en `ui/app.py` y `ui/panels.py`.
- `CommandInput` emite eventos `Submitted`; si el texto comienza con slash se delega en `SlashCommandProcessor` (`ui/commands.py`), de lo contrario se invoca al agente Strands.
- `SlashCommandProcessor` resuelve `/conectar`, `/desconectar`, `/ayuda` y aliases; cualquier otra orden se entrega intacta al agente.
- La clase `SSHConnectionManager` (`connection.py`) encapsula Paramiko, mantiene estado de conexión y ejecuta comandos; no abras clientes Paramiko alternos.

## Configuración centralizada
- Toda la configuración visual, atajos y logging vive en `conf/app_config.json`, modelada con dataclasses en `config/__init__.py` y extensible vía `SMART_AI_SYS_ADMIN_CONFIG_FILE` o `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- Ajusta colores, bindings o límites modificando ese JSON; nunca hardcodees constantes en la UI.
- El logging escribe en `logs/app.log` con `TimedRotatingFileHandler`; `log_to_console` duplica a stdout sin romper la TUI.

## Agente Strands y herramientas
- `AgentRuntime` (`agent/runtime.py`) carga `conf/agent.conf`, construye el agente con `AgentFactory` y comparte `SSHConnectionManager` como `agent.ssh_manager`.
- El fichero `conf/agent.conf` define proveedor (`bedrock`, `openai`, `local`), prompts (`system_prompts/*`), herramientas activas y MCP; respeta los nombres si añades otros providers.
- La tool `remote_ssh_command` (`agent/tools.py`) reutiliza la sesión activa y respeta `timeout_seconds`; cambia el nombre desde config antes de instanciar el agente.
- Activa MCP solo cuando los servidores remotos existen; errores en esa sección detienen el agente.

## Patrones de UI y experiencia
- `CommandInput` usa `ctrl+s` (desde config) para enviar y ofrece sugerencias contextualizadas en `_suggestion_for`; si añades comandos, actualiza esos mensajes y el help.
- `ConversationPanel` guarda historial limitado (`history_limit` en config) y renderiza Markdown retro naranja/verde, así que usa Markdown en respuestas de agente y mensajes del sistema.
- El banner de compatibilidad de terminal se genera en `_warn_if_term_incompatible`; si cambias la lista de terminales válidos, modifícalo en config.

## Flujo de trabajo de desarrollo
- Usa `python3 -m venv .venv && make install` para montar el entorno; el proyecto instala en editable (`pip install -e .`).
- Formato y lint obligatorios antes de PR: `make format` (Black) y `make lint` (Ruff); `make test` ejecuta pytest (hay placeholders en `tests/`).
- Lanza la TUI con `make run` o `python -m smart_ai_sys_admin`; revisa `logs/app.log` cuando depures el agente.

## Extensiones habituales
- Nuevos slash commands viven en `SlashCommandProcessor`; recuerda sincronizar `COMMAND_OVERVIEW`, `CONNECT_HELP`, sugerencias del input y tests futuros.
- Herramientas adicionales para el agente deben registrarse en `agent/tools.resolve_tools` o habilitarse vía `tools.default` en `conf/agent.conf`.
- Si incorporas nuevos parámetros de configuración, documenta el campo en `README.md` y `AGENTS.md` y mantén el estilo de documentación en español.
