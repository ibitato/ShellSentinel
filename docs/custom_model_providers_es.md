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

## Caso práctico: OpenAI Responses API

Shell Sentinel permite seleccionar el endpoint con `providers.openai.api`: `chat_completions` es el valor predeterminado y usa `/v1/chat/completions`; `responses` usa `/v1/responses`. La entrada común se normaliza por endpoint: `max_tokens` pasa a `max_completion_tokens` para Chat Completions o a `max_output_tokens` para Responses, y `reasoning_effort`/`reasoning.effort` se convierten a la forma correspondiente.

El caso que motivó la migración fue un HTTP 400 de `gpt-5.6-sol`: Chat Completions no admite function tools junto con un `reasoning_effort` activo. Shell Sentinel adjunta tools en los turnos administrativos, por lo que omitir el parámetro o usar `medium` puede fallar; otros GPT-5.x pueden degradar silenciosamente a cero tokens de razonamiento. Configurar `reasoning_effort: "none"` evita el 400 porque desactiva el razonamiento (`reasoning_tokens=0`), no porque haga compatibles ambas capacidades. Responses sí permite function tools con `reasoning.effort: "medium"`.

Configuración de referencia del ejemplo (sin secretos):

```json
{
  "model_id": "gpt-5.6-sol",
  "api": "responses",
  "params": {
    "reasoning_effort": "medium",
    "max_tokens": 32768
  }
}
```

El request efectivo usa `reasoning: {"effort": "medium"}` y `max_output_tokens: 32768`; la configuración real del repositorio usa `max_tokens: 65536`. Responses acepta también `temperature: 0.3` como opción comprobada, pero no forma parte del valor predeterminado. La clave se obtiene de `OPENAI_API_KEY` en el entorno.

`stateful` es opcional y puede mantener `previous_response_id`, pero no elimina una limitación conocida: `reasoningContent` todavía no está soportado de forma completa al reconstruir conversaciones multi-turno. El proveedor filtra esos bloques del historial; el modelo razona en cada turno, pero pierde continuidad del razonamiento entre turnos. Evalúa `stateful: true` según el flujo y no prometas continuidad completa hasta que el SDK resuelva esta limitación.

## Caso práctico: LM Studio
- LM Studio expone un servidor local compatible con la API de OpenAI (`/v1/*`). Define `base_url`, `api_key` (o `api_key_env`) y `model_id` en `providers.lmstudio` para reutilizar el `OpenAIModel` de Strands sin cambios adicionales.
- El servidor debe arrancarse con `lms server start` (puede ejecutarse en modo headless). Ajusta `timeout` y otros argumentos mediante `client_args` si necesitas mayores márgenes.
- La REST API nativa (`/api/v0/*`) ofrece métricas enriquecidas. Úsala como consulta auxiliar cuando debas mostrar estadísticas (TTFT, tokens/segundo) en los logs o telemetría.
- `GET /api/v0/models/<model_id>` devuelve `max_context_length`; úsalo para calcular límites sensatos de `max_completion_tokens` (ej. `openai/gpt-oss-20b` expone 131072 tokens de contexto).

## Caso práctico: Mistral AI (Camino A+)

- Shell Sentinel incluye `ShellMistralModel`, un wrapper sobre `MistralModel` de Strands (SDK oficial `mistralai` v2). Configura `providers.mistral` con `model_id`, `api_key_env`/`MISTRAL_API_KEY`, `reasoning_effort` y `params`.
- **Valores por defecto:** `mistral-medium-3.5`, `reasoning_effort: high` (obligatorio en modelos con reasoning), `max_tokens: 16184`.
- El wrapper inyecta `reasoning_effort` en cada petición y mapea chunks de thinking a eventos `reasoningContent` (para `show_thinking`).
- Valida con `make test-mistral` cuando `MISTRAL_API_KEY` esté disponible.

## Caso práctico: Google Gemini

- Shell Sentinel usa directamente el `GeminiModel` de Strands (`strands.models.gemini`, extra `gemini` de `strands-agents`, SDK oficial `google-genai`); no hay wrapper propio. `AgentFactory._build_gemini_model` lo construye a partir de `providers.gemini`: `model_id`, `params` y `client_args`.
- **Credenciales:** `api_key_env` indica la variable de entorno con la clave (`GEMINI_API_KEY` por defecto). Si está vacía, la fábrica prueba también `GEMINI_API_KEY` y `GOOGLE_API_KEY`, los nombres que reconoce el SDK, y lanza `AgentConfigError` cuando ninguna está definida. `api_key` se rechaza tanto en el nivel superior como dentro de `client_args`. Con `client_args.vertexai: true` (más `project`/`location`) no hace falta clave porque el SDK usa credenciales ADC de Google Cloud.
- **Parámetros:** `params` se pasa como `GenerateContentConfig` (`temperature`, `top_p`, `max_output_tokens`, `thinking_config`, `safety_settings`...). La clave común `max_tokens` se normaliza a `max_output_tokens` salvo que esta última ya exista. El ejemplo usa `gemini-3.8-flash`, `temperature: 0.3` y `max_tokens: 16384`.
- **Streaming y thinking:** `GeminiModel.stream` mapea las function calls a `toolUse`, las partes `thought` a `reasoningContent` (visibles con `show_thinking`) y conserva las firmas de pensamiento entre turnos. El usage llega como `prompt_token_count` + `tool_use_prompt_token_count` (`inputTokens`), `candidates_token_count` + `thoughts_token_count` (`outputTokens`) y `cached_content_token_count` (`cacheReadInputTokens`).
- **Prompt caching:** `GeminiModel` no acepta `CacheConfig` y descarta los bloques `cachePoint` con un aviso, así que `providers.gemini.cache` parte de `enabled: false` y un bloque activado se ignora con un aviso de la fábrica. Gemini cachea prefijos de forma implícita en el servidor; lo que informe como cacheado sigue mostrándose en `/status`.
- La suite e2e live tiene una fila `gemini` en `tests/e2e/providers.py` (`RUN_E2E=1 SHELL_SENTINEL_E2E_PROVIDERS=gemini`).

## Prompt caching

- Cada bloque de proveedor de `conf/agent.conf` admite un objeto opcional `cache` con los mismos campos que el `CacheConfig` de Strands (`strands.models.model`): `enabled`, `strategy` (`auto`|`anthropic`), `ttl`, `system_prompt_ttl`, `tools_ttl` y `cache_key`. `AgentFactory` lo convierte con `build_strands_cache_config` y pasa `cache_config=` a `BedrockModel`, `OpenAIModel`, `OpenAIResponsesModel` y `ShellMistralModel` (que lo reenvía a `MistralModel`).
- **Bedrock** necesita cache points explícitos. El valor por defecto `enabled: true` + `strategy: "auto"` deja que Strands los inserte solo en modelos Claude/Anthropic; el resto de modelos no se toca. `ttl` admite `5m`/`1h`; `system_prompt_ttl` y `tools_ttl` admiten `true`/`false` o una cadena TTL.
- **OpenAI y Mistral** cachean prefijos en el servidor y solo consumen `cache_key` (enviado como `prompt_cache_key`; OpenAI también respeta `ttl` cuando vale `in_memory` o `24h`). Shell Sentinel no usa un gestor de sesiones de Strands, así que cuando `cache_key` no está definido la fábrica deriva `shell-sentinel-<sha256(ruta de configuración + model_id)[:16]>` con `derive_cache_key`, de modo que sesiones repetidas comparten prefijo. Usa `cache_key: false` para no enviar clave.
- **LM Studio** reutiliza `OpenAIModel` pero parte de `enabled: false` porque cachea localmente; al activarlo se envía la misma clave de enrutamiento. **Ollama, Cerebras y Gemini** no gestionan caché: un bloque activado se ignora con un aviso del logger `smart_ai_sys_admin.agent.factory`.
- Strands registra `cacheReadInputTokens`/`cacheWriteInputTokens` en las métricas del agente. `AgentRuntime` resume la última invocación (`summarize_cache_usage`), lo registra a nivel INFO y lo expone en `/status`. El `MistralModel` de Strands no rellena esos campos, así que `ShellMistralModel` sobrescribe el chunk `metadata` y copia `prompt_tokens_details.cached_tokens` (`data.usage` en streaming y `response.usage` sin streaming) en `cacheReadInputTokens`, manteniendo `inputTokens` igual a `prompt_tokens` como hace OpenAI. Si el campo falta, el usage se emite sin cambios.

## Límite de turnos por instrucción

- `agent.max_turns` en `conf/agent.conf` (por defecto `25`, `null`/`0` lo desactiva) se carga en `AgentOptions.max_turns` y se valida como entero positivo. `AgentRuntime.invoke` lo pasa a Strands como `agent(prompt, limits={"turns": N})`; el event loop comprueba el límite al inicio de cada ciclo, así que las herramientas pedidas en el último turno siempre terminan y `agent.messages` queda listo para una nueva invocación.
- Al alcanzar el límite, Strands devuelve un `AgentResult` con `stop_reason == "limit_turns"` en lugar de seguir recurriendo. El runtime añade el mensaje localizado `agent.invoke.turn_limit` al texto que haya producido el modelo y registra un WARNING. Un proveedor personalizado no necesita nada extra: el límite vive en el event loop de Strands, independiente de la implementación del modelo. Es la red de seguridad en producción frente a proveedores que agrupan mal los deltas de tool calls en streaming y entregan a la herramienta una entrada vacía una y otra vez.

## Caso práctico: Cerebras
- Integra el SDK oficial (`cerebras_cloud_sdk`) dentro de un `Model` personalizado para aprovechar streaming vía SSE y soporte de herramientas. En `providers.cerebras` define `model_id`, `params`, `client_args` y una referencia a la clave (`api_key_env` o `CEREBRAS_API_KEY`).
- El proveedor construye un cliente `AsyncCerebras` persistente; evita reinstanciarlo en cada llamada para mantener conexiones calientes.
- El método `stream()` convierte los `ChatChunkResponse` en `StreamEvent` nativo (texto, razonamiento y tool calls). Los metadatos (`usage`, `time_info.total_time`) se exponen como `metadata` para el panel de observabilidad.
- Para salidas estructuradas, genera un `ToolSpec` mediante `convert_pydantic_to_tool_spec`, fuerza `tool_choice` y parsea el `tool_call.function.arguments` devuelto.

## Referencias externas
- Documentación oficial: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/custom_model_provider/
- Código de ejemplo (`BedrockModel`): https://github.com/strands-agents/sdk-python/blob/main/src/strands/models/bedrock.py
