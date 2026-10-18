# Shell Sentinel
![Interfaz retro de Shell Sentinel en ejecución](screenshots/shell-sentinel-tui-1280x640.png)

Disponible en: [English](README.md) · [Deutsch](README_de.md) · [Español](README_es.md)

Shell Sentinel es un administrador de sistemas asistido por IA en terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y traduce instrucciones en lenguaje natural en acciones seguras y auditables.

Repositorio público: <https://github.com/ibitato/ShellSentinel>

Sitio oficial: <https://www.shellsentinel.net>.

## Requisitos
- Python 3.12
- Entorno virtual local (recomendado `.venv`; ver también `.python-version`)

## Pasos iniciales
1. Crear el entorno virtual (Python 3.12):
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar dependencias de desarrollo y de ejecución:
   ```bash
   make install
   ```
3. Ejecutar las comprobaciones básicas:
   ```bash
   make format
   make lint
   make test
   ```
   `make test` incluye la suite end-to-end offline de la TUI. Las pruebas end-to-end contra proveedores reales se ejecutan con `make test-e2e-live` (`RUN_E2E=1` más las claves API; consulta `CONTRIBUTING.md`).

## Uso de la CLI
- Lanza la interfaz TUI con:
```bash
make run
```
- La consola se divide en dos zonas principales: historial de salida (superior) y área de entrada (inferior), rematada con un **footer** que muestra en todo momento el estado de la conexión SSH y el proveedor/modelo LLM activo.
- Envía las instrucciones usando el atajo configurado (por defecto `Ctrl+S`). Mientras el agente o `/connect` están trabajando, la interfaz sigue respondiendo (el footer muestra el indicador de "pensando"), pero los nuevos envíos se rechazan con un aviso hasta que termine el actual.
- Comandos disponibles (puedes usar los alias en inglés, español o alemán):
  - `/connect <host> <user> <password|key_path> [puerto]` (`/conectar`, `/verbinden`) abre una sesión SSH persistente (el puerto es opcional, por defecto 22). SFTP se abre en la primera transferencia de archivos.
  - `/disconnect` (`/desconectar`, `/trennen`) cierra la conexión activa si existe.
  - `/help` (`/ayuda`, `/hilfe`) muestra un resumen en Markdown de los comandos disponibles.
  - `/status` (`/estado`) muestra el estado actual del agente y la conexión.
  - `/exit` (`/salir`, `/beenden`, `/quit`) abre un diálogo de confirmación para cerrar la aplicación.
- El sistema mostrará las respuestas en formato Markdown y en un esquema de color retro naranja/verde.
- Se recomienda un terminal `xterm` o `xterm-256color` para aprovechar la paleta.

## Configuración
- Todos los parámetros visuales y de interacción (colores, atajos, mensajes, límites de historial) se gestionan desde `conf/app_config.json`.
- Puedes sobreescribir la ruta mediante las variables de entorno `SMART_AI_SYS_ADMIN_CONFIG_FILE` (ruta directa al fichero) o `SMART_AI_SYS_ADMIN_CONFIG_DIR` (directorio que contiene `app_config.json`).
- Evita modificar valores en código fuente; ajusta el fichero de configuración y reinicia la app para aplicar los cambios.
- Nuevos parámetros destacados en `conf/app_config.json`:
  - `ui.connection_panel`: estilos del panel inferior que muestra el estado de la conexión y el resumen del proveedor.
- `logging`: nivel (por defecto `DEBUG`), directorio (`logs/`), nombre de fichero y política de rotación (3 días) del sistema de logging basado en `TimedRotatingFileHandler`.
  - Los loggers de dependencias verbosas (`markdown_it`, `botocore.parsers`, `paramiko.transport`, etc.) se reducen automáticamente a `INFO` cuando se usa `DEBUG` para evitar ruido excesivo.
    - `log_to_console`: cuando es `true`, duplica los registros en stdout (por defecto `false` para no interferir con la TUI).

### Internacionalización
- La interfaz soporta inglés (por defecto), alemán y español. El idioma se detecta a partir de la variable `SMART_AI_SYS_ADMIN_LOCALE` o, en su defecto, del locale del sistema.
- Los textos traducibles viven en `conf/locales/<idioma>/strings.json`. Para añadir un nuevo idioma, crea el directorio correspondiente, copia uno de los ficheros existentes como plantilla y traduce las claves respetando los marcadores `{placeholder}`.
- Puedes forzar el idioma ejecutando, por ejemplo:
  ```bash
  export SMART_AI_SYS_ADMIN_LOCALE=de
  make run
  ```
- El fichero `conf/app_config.json` contiene referencias `{{clave.de.traduccion}}` que se resuelven en tiempo de carga usando el locale activo; no elimines las llaves dobles al personalizar valores.

### Manuales de usuario
- Documentación práctica paso a paso disponible en `docs/user_guide_es.md`, `docs/user_guide_en.md` y `docs/user_guide_de.md`. Mantén las tres versiones sincronizadas al introducir nuevas funcionalidades.

### Configuración del agente IA (Strands Agents)
- Copia `conf/agent.conf.example` a `conf/agent.conf` y ajusta el bloque `provider` para elegir entre Amazon Bedrock, OpenAI, LM Studio, Cerebras, Mistral AI, Google Gemini u Ollama/local.
- Si optas por LM Studio, arranca el servidor local con `lms server start` y revisa `providers.lmstudio` (`base_url`, `model_id`, `api_key_env`/`api_key`, `client_args`) para que coincidan con tu instalación.
- Para Cerebras, exporta `CEREBRAS_API_KEY` (o define `api_key_env`) y personaliza `providers.cerebras` (`model_id`, `params`, `client_args.timeout`, etc.); el proveedor usa el SDK oficial con streaming SSE.
- Para Mistral AI, exporta `MISTRAL_API_KEY` (o define `api_key_env`), selecciona `provider: "mistral"` y revisa `providers.mistral`. Valores por defecto: `model_id: mistral-medium-3.5`, `reasoning_effort: high` (obligatorio en modelos con reasoning), `max_tokens: 16184`. Ejecuta `make test-mistral` para validar la clave API.
- Para Google Gemini, exporta `GEMINI_API_KEY` (o `GOOGLE_API_KEY`, o apunta `api_key_env` a otra variable), selecciona `provider: "gemini"` y revisa `providers.gemini` (`model_id`, `params`, `client_args`). El proveedor usa el `GeminiModel` de Strands sobre el SDK oficial `google-genai`. El ejemplo usa `gemini-3.8-flash` con `temperature: 0.3` y `max_tokens: 16384` (enviado como `max_output_tokens`); el resto de `params` se pasa tal cual a `GenerateContentConfig` (por ejemplo `thinking_config`). `client_args` se reenvía al cliente de `google-genai`: define `vertexai: true` con `project`/`location` para usar credenciales de Vertex AI en lugar de una clave de API. No se admite `api_key` en el JSON.
- Cada proveedor cuenta con su propio `system_prompt`, ubicado en `system_prompts/`. Puedes personalizar esos ficheros o apuntar a otros paths.
- OpenAI admite `providers.openai.api: "chat_completions"` (predeterminado, `POST /v1/chat/completions`) y `api: "responses"` (`POST /v1/responses`). LM Studio permanece en el modo compatible con Chat Completions.
- El valor común `max_tokens` se normaliza como `max_completion_tokens` para Chat Completions y como `max_output_tokens` para Responses. Del mismo modo, `reasoning_effort` y `reasoning.effort` se convierten a la forma esperada por el endpoint elegido.
- En modelos GPT-5.x que usan function tools y razonamiento, selecciona Responses. Chat Completions puede devolver HTTP 400 para esa combinación o informar silenciosamente de cero tokens de razonamiento; `reasoning_effort: "none"` evita el error únicamente porque desactiva el razonamiento.
- El modo opcional `stateful` puede reutilizar `previous_response_id`, pero existe una limitación conocida: al reconstruir conversaciones multi-turno, `reasoningContent` todavía no conserva toda la continuidad del razonamiento.
- El prompt caching se configura por proveedor mediante un bloque opcional `cache` (`enabled`, `strategy`, `ttl`, `system_prompt_ttl`, `tools_ttl`, `cache_key`) que replica el `CacheConfig` de Strands. Valores por defecto: Bedrock `enabled: true` con `strategy: "auto"` (Strands inserta cache points solo en modelos Claude, así que el resto de modelos de Bedrock no se ven afectados; `ttl` admite `5m`/`1h`, `system_prompt_ttl`/`tools_ttl` admiten `true`/`false` o un TTL); OpenAI y Mistral `enabled: true`, que solo envía una clave de enrutamiento estable (`prompt_cache_key`) derivada de la ruta de configuración y de `model_id`, salvo que fijes `cache_key` (usa `false` para desactivarla; el `ttl` de OpenAI admite `in_memory`/`24h`). LM Studio permanece desactivado salvo que lo actives; Ollama, Cerebras y Gemini ignoran el bloque con un aviso en el log (Gemini cachea prefijos de forma implícita en el servidor y el `cached_content_token_count` que informe se muestra igualmente como tokens de entrada cacheados). `/status` indica si la caché está activa y cuántos tokens de entrada del último turno se leyeron de caché (también se registra a nivel INFO). Mistral informa de los aciertos de caché mediante `prompt_tokens_details.cached_tokens`, que Shell Sentinel traduce a `cacheReadInputTokens`.
- Mantén las credenciales en variables de entorno y expórtalas antes de iniciar la TUI; nunca guardes secretos en JSON:
  ```bash
  export OPENAI_API_KEY="..."
  export FIRECRAWL_API_KEY="..."
  ```
- El ejemplo de OpenAI usa `gpt-5.6-sol`, `api: "responses"`, `reasoning_effort: "medium"` y `max_tokens: 32768` (enviado como `max_output_tokens`). La configuración real usa **65.536**; el ejemplo de Bedrock mantiene `max_tokens: 8192`. Ajusta estos valores a tus cuotas.
- Responses también admite `temperature: 0.3` opcional en `params`; no forma parte de la configuración predeterminada.
- Las credenciales se obtienen de tu entorno (`AWS_*`, `OPENAI_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`, etc.). También puedes redefinir la ubicación del fichero con `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` o reutilizar `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- La sección `tools` permite habilitar herramientas Strands Agents Tools y la tool personalizada `remote_ssh_command`, que reutiliza la sesión SSH abierta por la TUI (el parámetro `timeout_seconds` es opcional y limita el tiempo **total** de ejecución del comando, no la inactividad entre lecturas de salida).
- `tools.default` define qué herramientas de Strands Agents Tools se registran (`shell`, `file_read`, `file_write`, `sleep`). Quita `shell` y `file_write` para que el agente no actúe sobre tu equipo local; si omites la clave se habilitan todas. `remote_ssh_command`, `remote_sftp_transfer` y `local_datetime` están siempre disponibles.
- `remote_ssh_command` emplea por defecto un timeout de **900 segundos (15 minutos)** de ejecución total definido en `conf/agent.conf`; al superarlo se cierra el canal y el agente recibe un error de timeout. Si el comando puede tardar más, indícalo en tu instrucción para que el agente añada `timeout_seconds` con el valor deseado.
- Para evitar respuestas inmanejables, `remote_command.max_output_chars` limita el número de caracteres que se entregan al agente. Aumenta o reduce este valor según la política de tu entorno (por ejemplo, más alto para auditorías, más bajo para sesiones compartidas).
- `agent.max_turns` limita cuántos turnos (una llamada al modelo más las herramientas que solicite) puede dedicar el agente a una sola instrucción; el valor por defecto es **25**. Al alcanzarlo, Strands detiene la invocación de forma limpia, el panel de conversación añade un aviso sugiriendo una instrucción más acotada y se registra un WARNING. Usa `null` o `0` para desactivar el límite. `/status` muestra el valor activo. Es la red de seguridad frente a un modelo que pide herramientas en bucle, algo que antes terminaba en un `RecursionError`.
- Si necesitas servidores externos Model Context Protocol (MCP), declara cada transporte (`stdio`, `sse`, `streamable_http`) en la sección `mcp`. El agente mantendrá las conexiones activas durante la sesión y añadirá sus herramientas automáticamente.
  - Ejemplo: el transporte `firecrawl-stdio` lanza `npx -y firecrawl-mcp`. Configura `env_passthrough` para que el agente herede `FIRECRAWL_API_KEY` (u otras variables sensibles) y, antes de iniciar la TUI, expórtalas en tu entorno (`export FIRECRAWL_API_KEY="..."`).
  - Los servidores arrancan en paralelo; el que falla o no responde dentro de su `timeout_seconds` (30 s por defecto) se omite con un aviso en el panel de conversación que indica la causa y la solución, y `/status` lista cada servidor MCP con su estado y su número de herramientas. El agente arranca igualmente, sin las herramientas de ese servidor.
  - Los transportes usan el SDK `mcp` 2.x. En `sse` y `streamable_http`, `timeout_seconds` fija también el timeout HTTP de conexión/escritura (la lectura conserva una ventana SSE de 300 s) y `headers` se reenvía al cliente HTTP; sin valor, el transporte usa 30 s.
- Al iniciar la aplicación verás una pantalla de bienvenida retro en tonos naranja; se cierra sola tras 5 s o cuando presionas cualquier tecla.
- Las sesiones `/conectar` mantienen viva la sesión SSH; SFTP se abre bajo demanda cuando el agente transfiere archivos. El agente dispone de `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` para subir (`upload`/`put`) o descargar (`download`/`get`) archivos reutilizando esa conexión. Las rutas remotas relativas se resuelven bajo el directorio home SFTP del usuario conectado, y los directorios intermedios que falten se crean ahí. Las contraseñas de `/connect` (también las entrecomilladas con espacios) se enmascaran como `***` en logs y en la entrada mostrada. Puedes renombrar la herramienta desde `tools.sftp_transfer.name` si necesitas otro identificador.
- Puedes administrar servidores GNU/Linux o Windows siempre que expongan SSH/SFTP. Ajusta los comandos remotos a la plataforma (por ejemplo, usa PowerShell/cmd para Windows) y valida rutas antes de transferir o modificar contenidos.

### Sistema de plugins
- Los plugins se cargan automáticamente desde el directorio `plugins/` (puedes sobrescribirlo mediante `SMART_AI_SYS_ADMIN_PLUGINS_DIR`, que admite varios paths separados por `:`). Cada archivo `.py` debe definir una función `register(registry)`.
- Dentro de `register(...)` utiliza `PluginSlashCommand` para declarar comandos slash adicionales. El `handler` recibe los argumentos del usuario y debe devolver un texto (Markdown) que se mostrará en el chat. Cualquier logging que hagas desde el plugin se integra en el sistema habitual de la TUI.
- Los plugins pueden aportar sus propias traducciones llamando a `registry.register_translations(locale, payload)`. Las claves `description`, `usage` y `help` que referencies en `PluginSlashCommand` deben existir en esas traducciones para respetar la localización.
- Opcionalmente puedes aportar una función `suggestion(command, args)` para personalizar el autocompletado del input. Si no la defines, se mostrará la cadena asociada a `usage_key`.
- Los comandos registrados aparecen automáticamente en `/help`, heredan el historial del input y comparten las mismas reglas de output que los comandos nativos (`/connect`, `/disconnect`, etc.).

```python
# plugins/credenciales.py
from smart_ai_sys_admin.plugins import PluginRegistry, PluginSlashCommand


def _buscar_credenciales(args: list[str]) -> str:
    if not args:
        return "⚠️ Debes indicar el nombre del servidor."
    servidor = args[0]
    # Aquí podrías invocar a tu API corporativa
    return f"Credenciales de `{servidor}`: usuario demo / password 1234"


def register(registry: PluginRegistry) -> None:
    registry.register_translations(
        "es",
        {
            "plugins": {
                "credentials": {
                    "description": "Obtiene credenciales desde la API interna",
                    "usage": "Uso: `{command} <servidor>`",
                    "help": "`{command}` consulta la API corporativa y muestra las credenciales en el chat.",
                }
            }
        },
    )

    registry.register_command(
        PluginSlashCommand(
            name="/credenciales",
            aliases=("/credentials",),
            handler=_buscar_credenciales,
            description_key="plugins.credentials.description",
            usage_key="plugins.credentials.usage",
            help_key="plugins.credentials.help",
        )
    )
```

## Estructura del proyecto
- `pyproject.toml`: metadatos del paquete y **definición canónica** de dependencias (runtime y `dev`).
- `requirements.txt` / `requirements-dev.txt`: lockfiles generados (`make lock`); no editar a mano.
- `docs/dependencies_es.md` (y `docs/dependencies_en.md`, `docs/dependencies_de.md`): gestión de dependencias, lockfiles y CI.
- `CHANGELOG.md`: historial de versiones del proyecto.
- `src/smart_ai_sys_admin/`: código fuente principal de la aplicación (TUI y utilidades).
- `tests/`: suite de pruebas automatizadas (unitarias, de integración y end-to-end en `tests/e2e`).
- `Makefile`: tareas para instalación (`install`, `install-prod`), lock, lock-upgrade, sync-deps, formateo, lint, lint-fix, test, test-mistral, test-e2e, test-e2e-live, ejecución, website-serve y limpieza.
- `AGENTS.md`: guía para agentes IA colaborando en este repositorio.

## Licencia
- Shell Sentinel se distribuye como software de **código disponible (source-available)**: el repositorio en GitHub permite auditar el código pero no autoriza la modificación ni la redistribución de versiones alteradas.
- Uso gratuito únicamente para fines personales, educativos o de evaluación interna sin ánimo de lucro. Cualquier uso comercial requiere una licencia negociada con el mantenedor.
- Queda prohibida la modificación, adaptación o creación de trabajos derivados del Software sin autorización previa y por escrito.
- Consulta el archivo `LICENSE` (Shell Sentinel Source-Available License 1.0) para detalles completos, definiciones y limitaciones.

Para licencias comerciales, permisos especiales o soporte extendido, abre un issue en GitHub o contacta al mantenedor.
