# Guide — Custom model providers in Strands Agents SDK

## Scope

This document summarises the steps and criteria for implementing custom model providers for the Strands Agents SDK within Shell Sentinel. It complements the official documentation and serves as an internal checklist.

## Prerequisites

- Familiarity with the `strands.models.Model` hierarchy (review official examples such as `BedrockModel`).
- Understanding of Strands types `Messages`, `StreamEvent` and `ToolSpec`.
- A Python client (sync or async) for the proprietary LLM service to expose.
- Declarative configuration in `conf/` (keys, model IDs, parameters) and credentials via environment variables.

## Implementation flow

1. **Define custom configuration**: create a typed `ModelConfig` (for example `TypedDict`) with supported parameters (`model_id`, `params`, etc.) and expose `get_config`/`update_config` for hot updates.
2. **Initialise the client**: in the constructor resolve credentials from a secure environment, instantiate the remote client and register logging (`smart_ai_sys_admin.agent`).
3. **Implement `stream(...)`**:
   - Receive `messages`, `tool_specs` and `system_prompt`; convert them to the format expected by the external service.
   - Invoke the client and adapt the response to the `StreamEvent` protocol (`messageStart`, `contentBlockDelta`, `messageStop`, `metadata`, etc.).
   - Handle errors (`ContextWindowOverflowException`, timeouts, authentication) with useful traces.
   - If the SDK is synchronous, use `asyncio.to_thread` or another wrapper to avoid blocking the event loop.
4. **Support tools and structured output**: reuse `stream` inside `structured_output(...)`, convert Pydantic models to `ToolSpec`, validate the response and treat missing tool calls as errors.
5. **Register the provider**: expose the class in `smart_ai_sys_admin.agent` (model factory) and add the corresponding configuration in `conf/agent.conf` or derived files.

## Additional considerations

- Keep logs at `DEBUG` level to simplify production troubleshooting.
- Document any new parameter in `docs/user_guide_*.md` when it affects operator workflows.
- Do not hardcode tokens or endpoints; use environment variables and `conf/` entries.
- Add smoke tests or manual scripts to validate provider calls before integrating into the TUI.

## Practical case: OpenAI Responses API

Shell Sentinel selects the endpoint through `providers.openai.api`: `chat_completions` is the default and uses `/v1/chat/completions`; `responses` uses `/v1/responses`. Shared input is normalized per endpoint: `max_tokens` becomes `max_completion_tokens` for Chat Completions or `max_output_tokens` for Responses, while `reasoning_effort`/`reasoning.effort` is converted to the corresponding shape.

The migration was prompted by an HTTP 400 from `gpt-5.6-sol`: Chat Completions does not support function tools together with active `reasoning_effort`. Shell Sentinel attaches tools during administrative turns, so omitting the setting or using `medium` can fail; other GPT-5.x models may silently degrade to zero reasoning tokens. Setting `reasoning_effort: "none"` avoids the 400 by disabling reasoning (`reasoning_tokens=0`), not by making both capabilities compatible. Responses supports function tools with `reasoning.effort: "medium"`.

Reference example configuration (without secrets):

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

The effective request uses `reasoning: {"effort": "medium"}` and `max_output_tokens: 32768`; the repository's real configuration uses `max_tokens: 65536`. Responses also accepts `temperature: 0.3` as a verified option, but it is not a default. Read `OPENAI_API_KEY` from the environment.

Optional `stateful` mode can retain `previous_response_id`, but it does not remove a known limitation: `reasoningContent` is not yet fully supported when reconstructing multi-turn conversations. The provider filters those history blocks; the model reasons on every turn but loses some reasoning continuity between turns.

## Practical case: LM Studio

- LM Studio exposes a local server compatible with the OpenAI API (`/v1/*`). Set `base_url`, `api_key` (or `api_key_env`) and `model_id` in `providers.lmstudio` to reuse Strands `OpenAIModel` without extra changes.
- Start the server with `lms server start` (headless mode supported). Tune `timeout` and other arguments via `client_args` when needed.
- The native REST API (`/api/v0/*`) offers richer metrics. Use it for telemetry when you need statistics (TTFT, tokens/sec) in logs.
- `GET /api/v0/models/<model_id>` returns `max_context_length`; use it to set sensible `max_completion_tokens` limits (e.g. `openai/gpt-oss-20b` exposes 131072 context tokens).

## Practical case: Mistral AI (Path A+)

- Shell Sentinel ships a `ShellMistralModel` wrapper over Strands `MistralModel` (official `mistralai` v2 SDK). Configure `providers.mistral` with `model_id`, `api_key_env`/`MISTRAL_API_KEY`, `reasoning_effort` and `params`.
- **Defaults:** `mistral-medium-3.5`, `reasoning_effort: high` (mandatory for reasoning-capable models), `max_tokens: 16184`.
- The wrapper injects `reasoning_effort` into every API request and maps thinking chunks to `reasoningContent` stream events (for `show_thinking`).
- **Streamed tool calls:** some models served by Mistral (for example `zai-glm-5-3`) send the tool-call `id` and name only in the first delta; later fragments carry the SDK default id `"null"` and only a slice of the JSON arguments. The wrapper groups fragments by `index` (or a real `id`), appends id-less fragments to the last open call, keeps parallel tool calls separate, serialises dict arguments to JSON and logs a warning naming the tool when the reassembled call still lacks an id, a name or valid JSON. Without this, `remote_ssh_command` received an empty input and the agent looped until `agent.max_turns` (previously `RecursionError`).
- Validate with `make test-mistral` when `MISTRAL_API_KEY` is available (the PoC tests are marked `e2e`, so `make test` never runs them).

## Practical case: Google Gemini

- Shell Sentinel uses Strands' `GeminiModel` (`strands.models.gemini`, `gemini` extra of `strands-agents`, official `google-genai` SDK) directly; there is no custom wrapper. `AgentFactory._build_gemini_model` builds it from `providers.gemini`: `model_id`, `params` and `client_args`.
- **Credentials:** `api_key_env` names the environment variable with the key (`GEMINI_API_KEY` by default). When it is empty the factory also tries `GEMINI_API_KEY` and `GOOGLE_API_KEY`, the names the SDK recognises, and raises `AgentConfigError` when none is set. `api_key` is rejected both at the top level and inside `client_args`. With `client_args.vertexai: true` (plus `project`/`location`) no key is required because the SDK uses Google Cloud ADC credentials.
- **Parameters:** `params` is passed as `GenerateContentConfig` (`temperature`, `top_p`, `max_output_tokens`, `thinking_config`, `safety_settings`...). The shared `max_tokens` key is normalised to `max_output_tokens` unless the latter is already present. The example uses `gemini-3.8-flash`, `temperature: 0.3` and `max_tokens: 16384`.
- **Streaming and thinking:** `GeminiModel.stream` maps function calls to `toolUse`, `thought` parts to `reasoningContent` (shown with `show_thinking`) and preserves thought signatures across turns. Usage arrives as `prompt_token_count` + `tool_use_prompt_token_count` (`inputTokens`), `candidates_token_count` + `thoughts_token_count` (`outputTokens`) and `cached_content_token_count` (`cacheReadInputTokens`).
- **Prompt caching:** `GeminiModel` does not accept `CacheConfig` and drops `cachePoint` blocks with a warning, so `providers.gemini.cache` defaults to `enabled: false` and an enabled block is ignored with a factory warning. Gemini caches prefixes implicitly on the server; whatever it reports as cached is still surfaced by `/status`.
- The live e2e suite has a `gemini` row in `tests/e2e/providers.py` (`RUN_E2E=1 SHELL_SENTINEL_E2E_PROVIDERS=gemini`).

## Prompt caching

- Every provider block in `conf/agent.conf` accepts an optional `cache` object with the same fields as Strands' `CacheConfig` (`strands.models.model`): `enabled`, `strategy` (`auto`|`anthropic`), `ttl`, `system_prompt_ttl`, `tools_ttl` and `cache_key`. `AgentFactory` converts it with `build_strands_cache_config` and passes `cache_config=` to `BedrockModel`, `OpenAIModel`, `OpenAIResponsesModel` and `ShellMistralModel` (which forwards it to `MistralModel`).
- **Bedrock** needs explicit cache points. The default `enabled: true` + `strategy: "auto"` lets Strands inject them only for Claude/Anthropic model ids; other models are left untouched. `ttl` accepts `5m`/`1h`; `system_prompt_ttl` and `tools_ttl` accept `true`/`false` or a TTL string.
- **OpenAI and Mistral** cache prefixes server-side and only consume `cache_key` (sent as `prompt_cache_key`; OpenAI also honours `ttl` when it is `in_memory` or `24h`). Shell Sentinel has no Strands session manager, so when `cache_key` is unset the factory derives `shell-sentinel-<sha256(config path + model_id)[:16]>` with `derive_cache_key`, making repeat sessions share a prefix. Set `cache_key: false` to send no key.
- **LM Studio** reuses `OpenAIModel` but defaults to `enabled: false` because it caches locally; enabling it sends the same routing key. **Ollama, Cerebras and Gemini** have no cache handling: an enabled block is ignored with a warning from `smart_ai_sys_admin.agent.factory`.
- Strands records `cacheReadInputTokens`/`cacheWriteInputTokens` in the agent metrics. `AgentRuntime` summarises the last invocation (`summarize_cache_usage`), logs it at INFO and exposes it to `/status`. Strands' `MistralModel` does not populate those fields, so `ShellMistralModel` overrides the `metadata` chunk and copies `prompt_tokens_details.cached_tokens` (streaming `data.usage` and non-streaming `response.usage`) into `cacheReadInputTokens`, keeping `inputTokens` equal to `prompt_tokens` as OpenAI does. When the field is absent the usage is emitted unchanged.

## Turn limit per instruction

- `agent.max_turns` in `conf/agent.conf` (default `25`, `null`/`0` disables) is parsed into `AgentOptions.max_turns` and validated as a positive integer. `AgentRuntime.invoke` passes it to Strands as `agent(prompt, limits={"turns": N})`; the event loop checks the cap at the top of every cycle, so the tools requested by the last turn always finish and `agent.messages` stays reinvokable.
- When the cap fires Strands returns an `AgentResult` with `stop_reason == "limit_turns"` instead of recursing. The runtime appends the localized `agent.invoke.turn_limit` message to whatever text the model produced and logs a WARNING. A custom provider needs no extra work: the cap lives in the Strands event loop, independent of the model implementation. It is the production safety net for providers that mis-group streamed tool-call deltas and keep handing empty input to the tool.

## Practical case: Cerebras

- Integrate the official SDK (`cerebras_cloud_sdk`) inside a custom `Model` for SSE streaming and tool support. In `providers.cerebras` define `model_id`, `params`, `client_args` and a key reference (`api_key_env` or `CEREBRAS_API_KEY`).
- The provider builds a persistent `AsyncCerebras` client; avoid re-instantiating it on every call.
- `stream()` converts `ChatChunkResponse` into native `StreamEvent` (text, reasoning, tool calls). Metadata (`usage`, `time_info.total_time`) is exposed as `metadata` for observability.
- For structured output, generate a `ToolSpec` via `convert_pydantic_to_tool_spec`, force `tool_choice` and parse `tool_call.function.arguments`.

## External references

- Official documentation: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/custom_model_provider/
- Example code (`BedrockModel`): https://github.com/strands-agents/sdk-python/blob/main/src/strands/models/bedrock.py
