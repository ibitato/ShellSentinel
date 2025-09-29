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
2. Instalar dependencias de desarrollo:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Ejecutar el formato y lint para verificar que todo está en orden:
   ```bash
   make format
   make lint
   ```

## Uso
> La lógica de la CLI está en construcción. Utiliza `python -m smart_ai_sys_admin` para ejecutar la versión actual.

## Estructura del proyecto
- `src/smart_ai_sys_admin/`: código fuente principal de la aplicación.
- `tests/`: espacio reservado para pruebas automatizadas.
- `Makefile`: tareas para automatizar instalación, formateo y lint.
- `AGENTS.md`: guía para agentes IA colaborando en este repositorio.
