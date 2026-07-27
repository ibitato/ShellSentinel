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
- Validate with `make test-mistral` when `MISTRAL_API_KEY` is available.

## Practical case: Cerebras

- Integrate the official SDK (`cerebras_cloud_sdk`) inside a custom `Model` for SSE streaming and tool support. In `providers.cerebras` define `model_id`, `params`, `client_args` and a key reference (`api_key_env` or `CEREBRAS_API_KEY`).
- The provider builds a persistent `AsyncCerebras` client; avoid re-instantiating it on every call.
- `stream()` converts `ChatChunkResponse` into native `StreamEvent` (text, reasoning, tool calls). Metadata (`usage`, `time_info.total_time`) is exposed as `metadata` for observability.
- For structured output, generate a `ToolSpec` via `convert_pydantic_to_tool_spec`, force `tool_choice` and parse `tool_call.function.arguments`.

## External references

- Official documentation: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/custom_model_provider/
- Example code (`BedrockModel`): https://github.com/strands-agents/sdk-python/blob/main/src/strands/models/bedrock.py
