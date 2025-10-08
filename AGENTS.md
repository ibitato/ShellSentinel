# AGENTS — Shell Sentinel

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
- Los atajos de teclado, estilos de color, mensajes, tamaños y límites del historial se leen exclusivamente desde los ficheros de `conf/`. Si se añaden nuevos parámetros (por ejemplo ajustes del footer de conexión), documentarlos en el README.
- Los textos visibles se suministran mediante plantillas en `conf/locales/<idioma>/strings.json`. Usa la función `_('clave')` del módulo `smart_ai_sys_admin.localization` para cualquier cadena nueva y crea la traducción en todos los idiomas soportados (`en`, `de`, `es`). Las referencias `{{ruta.de.clave}}` dentro de `conf/app_config.json` se resuelven automáticamente y nunca deben reemplazarse por cadenas literales.
- El idioma activo se detecta con la variable `SMART_AI_SYS_ADMIN_LOCALE` o, en su ausencia, con el locale del sistema (fallback a inglés). Si tu cambio requiere un idioma adicional, añade el directorio correspondiente en `conf/locales/`, documenta el soporte en los README y actualiza los manuales de usuario.
- Mantén sincronizados los manuales de usuario (`docs/user_guide_*.md`) y los README multilingües con cualquier cambio funcional: cada nueva característica, comando o flujo debe reflejarse inmediatamente en español, inglés y alemán.
- Es posible sobreescribir la ubicación del fichero principal mediante las variables de entorno `SMART_AI_SYS_ADMIN_CONFIG_FILE` o `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- La configuración del agente Strands vive en `conf/agent.conf`. Parte de `conf/agent.conf.example` y respeta `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` (o `SMART_AI_SYS_ADMIN_CONFIG_DIR`). El fichero de ejemplo fija `max_completion_tokens` (OpenAI) en 32 768, `max_tokens` (Bedrock) en 8 192, `remote_command.timeout_seconds` en 900 y `remote_command.max_output_chars` en 120 000; ajusta esos límites según las cuotas y políticas de tu entorno.
- El sistema de plugins carga cualquier módulo `.py` en `plugins/` (configurable con `SMART_AI_SYS_ADMIN_PLUGINS_DIR`). Cada plugin debe exponer `register(registry)`, registrar sus traducciones mediante `registry.register_translations(locale, payload)` y declarar comandos con `PluginSlashCommand`; los handlers devuelven Markdown y se integran en el logging estándar.
- Cuando desarrolles un plugin nuevo, documenta siempre su instalación y uso **dentro del propio directorio del plugin** (por ejemplo un `README` o `docs/` local) y evita añadirlo a la documentación general del proyecto.
- La licencia es de código disponible y restringe la modificación o redistribución de versiones alteradas sin permiso explícito; evita proponer acciones que vayan en contra de esa política.
- El agente debe considerar el tiempo de ejecución esperado: si el operario anticipa que un comando superará los 15 minutos por defecto, instruye al modelo para que incluya `timeout_seconds` en la tool `remote_ssh_command`. Ajusta también `remote_command.max_output_chars` cuando necesites recortes más agresivos o dumps completos (por ejemplo al revisar logs extensos).
- La transferencia de archivos usa la tool `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)`. Empléala para subir (`upload`/`put`) o bajar (`download`/`get`) archivos reutilizando la sesión SFTP vigente.
- Usa `local_datetime()` al inicio de cada turno para enriquecer las respuestas con la fecha y hora locales (no es necesario mostrarlas salvo que el operario lo requiera).
- Tanto los comandos como las transferencias deben adaptarse al sistema operativo remoto (GNU/Linux, Unix o Windows con PowerShell/cmd). Verifica la plataforma antes de proponer acciones específicas.
- El sistema de logging se inicializa desde `conf/app_config.json` con nivel por defecto `DEBUG`. Respeta este canal y usa los loggers `smart_ai_sys_admin.*` para observabilidad consistente.
- Nunca persistas claves API en el JSON. Usa las variables `OPENAI_API_KEY`, `AWS_*`, etc. y añade instrucciones de export en la documentación cuando se introduzca un nuevo proveedor.
- Los *system prompts* de cada proveedor residen en `system_prompts/`. Mantenerlos en español y actualizar referencias si se renombran.
- LM Studio funciona mediante el modo compatible con OpenAI. Antes de usarlo, ejecuta `lms server start` en la máquina local y ajusta `providers.lmstudio` (`base_url`, `model_id`, `api_key_env`/`api_key`) en `conf/agent.conf`.
- El modelo de ejemplo `openai/gpt-oss-20b` reporta `max_context_length = 131072` (consulta `GET /api/v0/models/<model>`), por lo que se fijó `max_completion_tokens` en ese valor para aprovechar todo el contexto disponible.
- Cerebras utiliza su SDK oficial. Configura `providers.cerebras` con `model_id`, `params` y `client_args` (sin credenciales en claro) y define `CEREBRAS_API_KEY` o `api_key_env`. El proveedor crea un cliente singleton reutilizable y convierte los eventos SSE en `StreamEvent` nativo.
- El bloque `mcp` del agente solo debe habilitarse cuando los servidores declarados estén disponibles; la inicialización fallará en caso contrario.
- Dependencias nuevas deben agregarse al `requirements.txt` (ejecución) y, si aplica, cascada en `requirements-dev.txt`.
- Para desarrollar proveedores de modelo personalizados revisa `docs/custom_model_providers_es.md` antes de tocar el paquete `smart_ai_sys_admin.agent` o la configuración del agente.
- Mantén la web estática en `website/` sincronizada con las novedades del producto: cada flujo, manual o cambio visual debe reflejarse en todas las traducciones y secciones de ayuda.

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
- Las tools personalizadas `remote_ssh_command` y `remote_sftp_transfer` reutilizan `SSHConnectionManager`. No crear accesos SSH o SFTP paralelos.
