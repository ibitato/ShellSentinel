# Almost Human Sys Admin

Disponible en: [English](README_en.md) · [Deutsch](README_de.md) · [Español](README.md)

Administrador de sistemas asistido por IA en terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y traduce instrucciones en lenguaje natural en acciones seguras y auditables.

Nota de compatibilidad: por ahora el paquete y el comando siguen siendo `smart_ai_sys_admin` para no romper integraciones existentes.

## Requisitos
- Python 3.10 o superior
- Entorno virtual local (recomendado `.venv`)

## Pasos iniciales
1. Crear el entorno virtual:
   ```bash
   python3 -m venv .venv
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
   ```

## Uso de la CLI
- Lanza la interfaz TUI con:
  ```bash
  make run
  # o
  python -m smart_ai_sys_admin
  ```
- La consola se divide en dos zonas principales: historial de salida (superior) y área de entrada (inferior), rematada con un **footer** que muestra en todo momento el estado de la conexión SSH y el proveedor/modelo LLM activo.
- Envía las instrucciones usando el atajo configurado (por defecto `Ctrl+S`).
- Comandos disponibles (puedes usar los alias en inglés, español o alemán):
  - `/connect <host> <user> <password|key_path> [puerto]` (`/conectar`, `/verbinden`) abre una sesión SSH y SFTP persistente (el puerto es opcional, por defecto 22).
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
- Copia `conf/agent.conf.example` a `conf/agent.conf` y ajusta el bloque `provider` para elegir entre Amazon Bedrock, OpenAI, LM Studio, Cerebras u Ollama/local.
- Si optas por LM Studio, arranca el servidor local con `lms server start` y revisa `providers.lmstudio` (`base_url`, `model_id`, `api_key_env`/`api_key`, `client_args`) para que coincidan con tu instalación.
- Para Cerebras, exporta `CEREBRAS_API_KEY` (o define `api_key_env`) y personaliza `providers.cerebras` (`model_id`, `params`, `client_args.timeout`, etc.); el proveedor usa el SDK oficial con streaming SSE.
- Cada proveedor cuenta con su propio `system_prompt`, ubicado en `system_prompts/`. Puedes personalizar esos ficheros o apuntar a otros paths.
- Copia el fichero de ejemplo y ajusta las credenciales vía variables de entorno (por ejemplo `export OPENAI_API_KEY="..."`). El archivo no almacena claves en texto plano.
- Los modelos OpenAI y Bedrock admiten respuestas largas; por defecto `conf/agent.conf.example` fija `max_completion_tokens` (OpenAI) en **32 768** y `max_tokens` (Bedrock) en **8 192**. Ajusta estos límites según las cuotas de tu cuenta.
- Las credenciales se obtienen de tu entorno (`AWS_*`, `OPENAI_API_KEY`, etc.). También puedes redefinir la ubicación del fichero con `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` o reutilizar `SMART_AI_SYS_ADMIN_CONFIG_DIR`.
- La sección `tools` permite habilitar herramientas Strands Agents Tools y la tool personalizada `remote_ssh_command`, que reutiliza la sesión SSH abierta por la TUI (el parámetro `timeout_seconds` es opcional).
- `remote_ssh_command` emplea por defecto un timeout de **900 segundos (15 minutos)** definido en `conf/agent.conf`. Si el comando puede tardar más, indícalo en tu instrucción para que el agente añada `timeout_seconds` con el valor deseado.
- Si necesitas servidores externos Model Context Protocol (MCP), declara cada transporte (`stdio`, `sse`, `streamable_http`) en la sección `mcp`. El agente mantendrá las conexiones activas durante la sesión y añadirá sus herramientas automáticamente.
  - Ejemplo: el transporte `firecrawl-stdio` lanza `npx -y firecrawl-mcp`. Configura `env_passthrough` para que el agente herede `FIRECRAWL_API_KEY` (u otras variables sensibles) y, antes de iniciar la TUI, expórtalas en tu entorno (`export FIRECRAWL_API_KEY="..."`).
- Al iniciar la aplicación verás una pantalla de bienvenida retro en tonos naranja; se cierra sola tras 5 s o cuando presionas cualquier tecla.
- Las sesiones `/conectar` mantienen vivo el canal SSH y SFTP en paralelo. El agente dispone de `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` para subir (`upload`/`put`) o descargar (`download`/`get`) archivos reutilizando esa conexión. Puedes renombrar la herramienta desde `tools.sftp_transfer.name` si necesitas otro identificador.
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
    registry.register_translations(
        "en",
        {
            "plugins": {
                "credentials": {
                    "description": "Fetch credentials from the internal API",
                    "usage": "Usage: `{command} <server>`",
                    "help": "`{command}` queries the corporate API and prints credentials in the chat.",
                }
            }
        },
    )

    registry.register_command(
        PluginSlashCommand(
            name="/credentials",
            aliases=("/credenciales",),
            handler=_buscar_credenciales,
            description_key="plugins.credentials.description",
            usage_key="plugins.credentials.usage",
            help_key="plugins.credentials.help",
        )
    )
```

## Estructura del proyecto
- `requirements.txt`: dependencias de ejecución (Textual, Strands Agents y herramientas comunitarias).
- `requirements-dev.txt`: dependencias de desarrollo (`-r requirements.txt`, linting y tests).
- `src/smart_ai_sys_admin/`: código fuente principal de la aplicación (TUI y utilidades).
- `tests/`: espacio reservado para pruebas automatizadas.
- `Makefile`: tareas para automatizar instalación, formateo, lint y ejecución.
- `AGENTS.md`: guía para agentes IA colaborando en este repositorio.

## Licencia
- Uso gratuito para educación, estudiantes y equipos de hasta 5 personas.
- Para entornos con más de 5 puestos/usuarios, se requiere una licencia comercial acordada con el desarrollador.
- Consulta el archivo `LICENSE` (Almost Human Sys Admin Community License 1.0) para detalles completos, definiciones y limitaciones.

Para consultas sobre licencias comerciales o soporte extendido, abre un issue en GitHub o contacta al mantenedor.
