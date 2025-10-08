# Guía — Proveedores de modelo personalizados en Strands Agents SDK (ES)

## Alcance
Este documento resume los pasos y criterios que debemos seguir al implementar proveedores de modelo personalizados para el SDK de Strands Agents dentro de Shell Sentinel. Complementa la documentación oficial y sirve como checklist interno.

## Requisitos previos
- Familiaridad con la jerarquía `strands.models.Model` (revisar ejemplos oficiales como `BedrockModel`).
- Comprender los tipos `Messages`, `StreamEvent` y `ToolSpec` definidos por Strands.
- Cliente Python (sincronía o asincronía) para el servicio LLM propietario que se desea exponer.
- Configuración declarativa en `conf/` (claves, IDs de modelo, parámetros) y credenciales vía variables de entorno.

## Flujo de implementación
1. **Definir configuración propia**: crear una `ModelConfig` tipada (por ejemplo `TypedDict`) con los parámetros admitidos (`model_id`, `params`, etc.) y exponer `get_config`/`update_config` para permitir ajustes en caliente.
2. **Inicializar el cliente**: en el constructor resolver credenciales desde entorno seguro, instanciar el cliente remoto y registrar logging (`smart_ai_sys_admin.agent`).
3. **Implementar `stream(...)`**:
   - Recibir `messages`, `tool_specs` y `system_prompt`, convertirlos al formato que espera el servicio externo.
   - Invocar el cliente y adaptar la respuesta al protocolo `StreamEvent` (emitir `messageStart`, `contentBlockDelta`, `messageStop`, `metadata`, etc.).
   - Gestionar errores propios (`ContextWindowOverflowException`, timeouts, autenticación) y producir trazas útiles.
   - Si el SDK no es asíncrono, usar `asyncio.to_thread` u otro wrapper para no bloquear el event loop.
4. **Soportar herramientas y salidas estructuradas**: reutilizar `stream` dentro de `structured_output(...)`, convirtiendo modelos Pydantic a `ToolSpec`, validando la respuesta y tratando la ausencia de tool calls como error.
5. **Registrar el proveedor**: exponer la clase dentro del paquete `smart_ai_sys_admin.agent` (factoría de modelos) y añadir la configuración correspondiente en `conf/agent.conf` o archivos derivados.

## Consideraciones adicionales
- Mantener logs al nivel `DEBUG` para facilitar troubleshooting en producción.
- Documentar cualquier nuevo parámetro en los manuales `docs/user_guide_*.md` cuando afecte al flujo del operario.
- No hardcodear tokens ni endpoints; emplear variables de entorno y entradas en `conf/`.
- Añadir pruebas de humo o scripts manuales para validar llamadas al proveedor antes de integrarlo en la TUI.

## Caso práctico: LM Studio
- LM Studio expone un servidor local compatible con la API de OpenAI (`/v1/*`). Define `base_url`, `api_key` (o `api_key_env`) y `model_id` en `providers.lmstudio` para reutilizar el `OpenAIModel` de Strands sin cambios adicionales.
- El servidor debe arrancarse con `lms server start` (puede ejecutarse en modo headless). Ajusta `timeout` y otros argumentos mediante `client_args` si necesitas mayores márgenes.
- La REST API nativa (`/api/v0/*`) ofrece métricas enriquecidas. Úsala como consulta auxiliar cuando debas mostrar estadísticas (TTFT, tokens/segundo) en los logs o telemetría.
- `GET /api/v0/models/<model_id>` devuelve `max_context_length`; úsalo para calcular límites sensatos de `max_completion_tokens` (ej. `openai/gpt-oss-20b` expone 131072 tokens de contexto).

## Caso práctico: Cerebras
- Integra el SDK oficial (`cerebras_cloud_sdk`) dentro de un `Model` personalizado para aprovechar streaming vía SSE y soporte de herramientas. En `providers.cerebras` define `model_id`, `params`, `client_args` y una referencia a la clave (`api_key_env` o `CEREBRAS_API_KEY`).
- El proveedor construye un cliente `AsyncCerebras` persistente; evita reinstanciarlo en cada llamada para mantener conexiones calientes.
- El método `stream()` convierte los `ChatChunkResponse` en `StreamEvent` nativo (texto, razonamiento y tool calls). Los metadatos (`usage`, `time_info.total_time`) se exponen como `metadata` para el panel de observabilidad.
- Para salidas estructuradas, genera un `ToolSpec` mediante `convert_pydantic_to_tool_spec`, fuerza `tool_choice` y parsea el `tool_call.function.arguments` devuelto.

## Referencias externas
- Documentación oficial: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/custom_model_provider/
- Código de ejemplo (`BedrockModel`): https://github.com/strands-agents/sdk-python/blob/main/src/strands/models/bedrock.py
