# AGENTS — Smart-AI-Sys-Admin

## Objetivo del proyecto
Aplicación de terminal que mantiene una sesión SSH/SFTP persistente contra un servidor remoto y expone un agente de IA que traduce instrucciones en lenguaje natural a acciones administrativas sobre dicho servidor.

## Entorno técnico
- **Lenguaje:** Python 3.10+
- **Tipo de aplicación:** CLI interactiva
- **Ejecución local:** `python -m smart_ai_sys_admin`
- **Gestión de dependencias:** entorno virtual local `.venv`
- **Estructura de código:** distribución basada en `src/`

## Herramientas de desarrollo
- **Formato:** `black`
- **Linting:** `ruff`
- **Pruebas:** `pytest` (reservado, aún sin casos)
- **Tareas automatizadas:** `Makefile`

## Flujo de trabajo recomendado
1. Activar entorno virtual: `source .venv/bin/activate`
2. Instalar dependencias de desarrollo: `pip install -r requirements-dev.txt`
3. Antes de abrir PR:
   - `make format`
   - `make lint`
   - `make test` (cuando existan pruebas)

## Convenciones
- Colocar código fuente en `src/smart_ai_sys_admin/`.
- Mantener comentarios y documentación en español; nombres de funciones y clases en inglés descriptivo.
- Añadir pruebas unitarias en `tests/`.
- Evitar dependencias globales; todo deberá instalarse en el entorno virtual.
