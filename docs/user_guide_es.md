# Manual de usuario — Shell Sentinel (ES)

## Introducción
Shell Sentinel es una aplicación de terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y ofrece un asistente IA capaz de convertir instrucciones en lenguaje natural en acciones administrativas seguras.

## Requisitos
- Terminal compatible con color (se recomienda `xterm` o `xterm-256color`).
- Python 3.12.
- Acceso a un servidor con SSH/SFTP habilitado.

## Instalación
1. **Crear entorno virtual**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. **Instalar dependencias**:
   ```bash
   make install
   ```

## Configuración de idioma
El idioma se detecta automáticamente usando `SMART_AI_SYS_ADMIN_LOCALE` o, si no está definida, el locale del sistema. Idioma por defecto: inglés.

Ejemplos:
```bash
export SMART_AI_SYS_ADMIN_LOCALE=es   # Español
export SMART_AI_SYS_ADMIN_LOCALE=en   # Inglés
export SMART_AI_SYS_ADMIN_LOCALE=de   # Alemán
```

## Inicio de la aplicación
```bash
make run
```

Al arrancar verás una pantalla de bienvenida que se cierra sola en 5 segundos o al presionar cualquier tecla.

## Interfaz
- **Panel principal**: muestra la conversación en Markdown.
- **Área de entrada**: admite varias líneas; presiona `Ctrl+S` para enviar (por defecto).
- **Footer**: indica el estado de la conexión SSH y si el agente está procesando tu instrucción.

## Comandos básicos
Puedes usar los comandos en inglés, español o alemán.

- `/connect <host> <user> <password|key_path> [puerto]` — conecta la sesión SSH (puerto opcional, 22 por defecto). SFTP se abre automáticamente en la primera transferencia de archivos.
- `/disconnect` — cierra la conexión activa.
- `/help` — muestra el resumen de comandos disponibles.
- `/status` — muestra el estado actual del agente y la conexión.
- `/exit` — abre el diálogo de confirmación para salir.

Alias útiles: `/conectar`, `/desconectar`, `/ayuda`, `/salir`, `/verbinden`, `/trennen`, `/hilfe`, `/beenden`.

## Uso del asistente IA
Escribe instrucciones libres; si no coinciden con un comando slash, se enviarán al agente Strands. Ejemplos:
- "Listar los procesos que consumen más CPU".
- "Subir el archivo `/tmp/script.sh` a `/home/ubuntu/bin/script.sh`".

El agente reutiliza la sesión SSH activa para ejecutar comandos. Las transferencias de archivos abren SFTP bajo demanda en la misma conexión.

## Configuración adicional
- `conf/app_config.json` define estilos, textos y atajos mediante claves como `{{ui.output_panel.title}}`, resueltas según el locale.
- Las traducciones residen en `conf/locales/<idioma>/strings.json`. Al añadir nuevos textos, usa el helper `_('clave')` en el código y crea la entrada en cada idioma.
- `conf/agent.conf` controla el proveedor LLM, las herramientas y los timeouts. Copia `conf/agent.conf.example` antes de modificarlo.
- OpenAI admite `api: "chat_completions"` (predeterminado) y `api: "responses"`. Los valores comunes `max_tokens` y `reasoning_effort`/`reasoning.effort` se normalizan como `max_completion_tokens` o `max_output_tokens` y con la forma de razonamiento requerida por el endpoint. Usa Responses para function tools de GPT-5.x con razonamiento; Chat Completions puede rechazar esa combinación o devolver cero tokens de razonamiento. El modo opcional `stateful` puede reutilizar `previous_response_id`, pero `reasoningContent` todavía no mantiene toda la continuidad al reconstruir conversaciones multi-turno.
- Mantén `OPENAI_API_KEY` en el entorno. El ejemplo usa `gpt-5.6-sol`, Responses, razonamiento `medium` y `max_tokens: 32768` (efectivo como `max_output_tokens`); la configuración real usa `65536`. Bedrock mantiene `max_tokens: 8192`, `remote_command.timeout_seconds: 900` y `remote_command.max_output_chars: 120000`.
- Para `lmstudio`, ejecuta `lms server start` y ajusta `base_url`/`api_key`. Para `cerebras`, exporta `CEREBRAS_API_KEY` (o define `api_key_env`) y configura `client_args`/`params`; el SDK oficial procesa streams SSE. Para Mistral (`provider: "mistral"`), exporta `MISTRAL_API_KEY` y usa por defecto `reasoning_effort: high` y `max_tokens: 16184` con `mistral-medium-3.5`.

## Solución de problemas
- **No hay colores o la interfaz se ve mal**: revisa la variable `TERM` y la advertencia mostrada al inicio.
- **El agente no responde**: comprueba `conf/agent.conf`, variables de entorno de credenciales y los logs en `logs/app.log`.
- **Error “No hay una conexión SSH activa”**: ejecuta `/connect` antes de solicitar acciones al agente.
- **Fallo SFTP o transferencia tras un `/connect` correcto**: el shell remoto puede imprimir banners en sesiones no interactivas (por ejemplo `pyfiglet` en `~/.bashrc`). Envuelve la salida decorativa en una comprobación interactiva (`[[ $- == *i* ]]`) o pide al administrador usar `Subsystem sftp internal-sftp` en `sshd_config`.
- **Credenciales en logs**: las contraseñas de `/connect` se enmascaran como `***` en `logs/app.log` y en el eco del comando en la TUI.
