# Manual de usuario — Shell Sentinel (ES)

## Introducción
Shell Sentinel es una aplicación de terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y ofrece un asistente IA capaz de convertir instrucciones en lenguaje natural en acciones administrativas seguras.

## Requisitos
- Terminal compatible con color (se recomienda `xterm` o `xterm-256color`).
- Python 3.10 o superior.
- Acceso a un servidor con SSH/SFTP habilitado.

## Instalación
1. **Crear entorno virtual**:
   ```bash
   python3 -m venv .venv
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

- `/connect <host> <user> <password|key_path> [puerto]` — conecta al servidor (puerto opcional, 22 por defecto).
- `/disconnect` — cierra la conexión activa.
- `/help` — muestra el resumen de comandos disponibles.
- `/status` — muestra el estado actual del agente y la conexión.
- `/exit` — abre el diálogo de confirmación para salir.

Alias útiles: `/conectar`, `/desconectar`, `/ayuda`, `/salir`, `/verbinden`, `/trennen`, `/hilfe`, `/beenden`.

## Uso del asistente IA
Escribe instrucciones libres; si no coinciden con un comando slash, se enviarán al agente Strands. Ejemplos:
- "Listar los procesos que consumen más CPU".
- "Subir el archivo `/tmp/script.sh` a `/home/ubuntu/bin/script.sh`".

El agente reutiliza la conexión SSH/SFTP abierta para ejecutar comandos y transferir archivos.

## Configuración adicional
- `conf/app_config.json` define estilos, textos y atajos mediante claves como `{{ui.output_panel.title}}`, resueltas según el locale.
- Las traducciones residen en `conf/locales/<idioma>/strings.json`. Al añadir nuevos textos, usa el helper `_('clave')` en el código y crea la entrada en cada idioma.
- `conf/agent.conf` controla el proveedor LLM, opciones de herramientas y timeouts. Copia `conf/agent.conf.example` antes de modificarlo y, si eliges `lmstudio`, recuerda iniciar el servidor local con `lms server start` y ajustar `base_url`/`api_key` según tu entorno. Para `cerebras`, exporta `CEREBRAS_API_KEY` (o define `api_key_env`) y personaliza `client_args`/`params`; la integración usa el SDK oficial con streaming SSE. Ajusta `remote_command.max_output_chars` para limitar la cantidad de salida que recibirá el agente.

## Solución de problemas
- **No hay colores o la interfaz se ve mal**: revisa la variable `TERM` y la advertencia mostrada al inicio.
- **El agente no responde**: comprueba `conf/agent.conf`, variables de entorno de credenciales y los logs en `logs/app.log`.
- **Error “No hay una conexión SSH activa”**: ejecuta `/connect` antes de solicitar acciones al agente.
