# AGENTS — Almost Human Sys Admin

## Objetivo del proyecto
Aplicación de terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y expone un agente de IA que traduce instrucciones en lenguaje natural a acciones administrativas sobre dicho servidor.

## Entorno técnico
- **Lenguaje:** Python 3.10+
- **Tipo de aplicación:** CLI interactiva
- **Framework TUI:** [Textual 0.67.1](https://textual.textualize.io)
- **Agentic stack:** [Strands Agents SDK](https://github.com/strands-agents/sdk-python) + [`strands-agents-tools`](https://github.com/strands-agents/tools)
- **Ejecución local:** `python -m smart_ai_sys_admin` o `make run`
- **Gestión de dependencias:** entorno virtual local `.venv`, listado en `requirements*.txt`
- **Estructura de código:** distribución basada en `src/`

## Herramientas de desarrollo
- **Formato:** `black`
- **Linting:** `ruff`
- **Pruebas:** `pytest` (reservado, aún sin casos)
- **Tareas automatizadas:** `Makefile` (`install`, `format`, `lint`, `test`, `run`, `clean`)
- **Herramientas MCP disponibles:** El entorno expone las herramientas de [Firecrawl](https://www.firecrawl.dev/) para buscar en la web, hacer *scraping* y extraer información estructurada. Úsalas para investigar errores de librerías de terceros o fundamentar decisiones con documentación externa.

## Configuración y constantes
- Toda variable o valor ajustable debe residir en el directorio `conf/` (por defecto `conf/app_config.json`). Está prohibido hardcodear parámetros en el código cuando puedan residir en la configuración.
- Los atajos de teclado, estilos de color, mensajes, tamaños y límites del historial se leen exclusivamente desde los ficheros de `conf/`. Si se añaden nuevos parámetros, documentarlos en el README.
- Es posible sobreescribir la ubicación del fichero principal mediante las variables de entorno `SMART_AI_SYS_ADMIN_CONFIG_FILE` o `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- La configuración del agente Strands vive en `conf/agent.conf`. Parte de `conf/agent.conf.example` y respeta `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` (o `SMART_AI_SYS_ADMIN_CONFIG_DIR`).
- Los *system prompts* de cada proveedor residen en `system_prompts/`. Mantenerlos en español y actualizar referencias si se renombran.
- El bloque `mcp` del agente solo debe habilitarse cuando los servidores declarados estén disponibles; la inicialización fallará en caso contrario.
- Dependencias nuevas deben agregarse al `requirements.txt` (ejecución) y, si aplica, cascada en `requirements-dev.txt`.

## Flujo de trabajo recomendado
1. Activar entorno virtual: `source .venv/bin/activate`
2. Instalar dependencias: `make install`
3. Antes de abrir PR:
   - `make format`
   - `make lint`
   - `make test` (cuando existan pruebas)
4. Ejecutar la TUI manualmente (`make run`) para validar cambios interactivos.

## Convenciones
- Colocar código fuente en `src/smart_ai_sys_admin/` y pruebas en `tests/`.
- Documentación y comentarios en español; identificadores y nombres de APIs en inglés.
- Mantener estilos retro (verde para entrada, naranja para salida) mediante la configuración.
- Preferir componentes de Textual para la TUI; si se incorporan nuevos widgets, documentar su uso en la configuración.
- Evitar dependencias globales; todo deberá instalarse en el entorno virtual.
- Mantener unidades de código pequeñas y cohesivas: separar responsabilidades en módulos/subpaquetes lógicos (por ejemplo `ui/`, `commands/`, `connection/`) y evitar archivos monolíticos.
- El paquete `smart_ai_sys_admin/agent/` encapsula la integración con Strands (config, factoría, runtime y herramientas). Extiende ahí cualquier lógica relacionada con LLMs o MCP.
- La tool personalizada `remote_ssh_command` reutiliza `SSHConnectionManager`. No crear accesos SSH paralelos.
