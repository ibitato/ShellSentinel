# Smart-AI-Sys-Admin

Sistema de administración remota mediante agente de IA que mantiene una sesión SSH/SFTP abierta contra un servidor remoto y ejecuta instrucciones en su nombre.

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
- La consola se divide en dos zonas: historial de salida (superior) y entrada multi-línea (inferior).
- Envía las instrucciones usando el atajo configurado (por defecto `Ctrl+S`).
- Comandos disponibles:
  - `/connect [host] [usuario] [password|ruta_clave]` abre una sesión SSH y SFTP persistente hasta que se invoque `/disconnect`.
  - `/disconnect` cierra la conexión activa (si existe).
- El sistema mostrará las respuestas en formato Markdown y en un esquema de color retro naranja/verde.
- Se recomienda un terminal `xterm` o `xterm-256color` para aprovechar la paleta.

## Configuración
- Todos los parámetros personalizables (colores, atajos, mensajes, límites de historial) se gestionan desde `conf/app_config.json`.
- Puedes sobreescribir la ruta mediante las variables de entorno `SMART_AI_SYS_ADMIN_CONFIG_FILE` (ruta directa al fichero) o `SMART_AI_SYS_ADMIN_CONFIG_DIR` (directorio que contiene `app_config.json`).
- Evita modificar valores en código fuente; ajusta el fichero de configuración y reinicia la app para aplicar los cambios.
- Nuevos parámetros destacados en `conf/app_config.json`:
  - `ui.connection_panel`: estilos del panel inferior que muestra el estado de la conexión.
  - `logging`: nivel, directorio (`logs/`), nombre de fichero y política de rotación (3 días) del sistema de logging basado en `TimedRotatingFileHandler`.
    - `log_to_console`: cuando es `true`, duplica los registros en stdout (por defecto `false` para no interferir con la TUI).

## Estructura del proyecto
- `requirements.txt`: dependencias de ejecución (Textual y Rich).
- `requirements-dev.txt`: dependencias de desarrollo (`-r requirements.txt`, linting y tests).
- `src/smart_ai_sys_admin/`: código fuente principal de la aplicación (TUI y utilidades).
- `tests/`: espacio reservado para pruebas automatizadas.
- `Makefile`: tareas para automatizar instalación, formateo, lint y ejecución.
- `AGENTS.md`: guía para agentes IA colaborando en este repositorio.
