# Mistral AI Cloud — Integration Assessment for Shell Sentinel

**Document type:** Research / decision support (project tier, English only)  
**Version assessed:** Shell Sentinel 1.1.1, Strands Agents SDK 1.45.0  
**Date:** 2026-06-29  
**Scope:** Mistral AI **cloud API only** (La Plateforme). No local/Ollama/LM Studio paths. Desk research plus **live API PoC** (2026-06-29).

---

## 1. Executive summary

### Recommendation: **Path A** (Strands `MistralModel` + official `mistralai` SDK via thin Shell Sentinel wiring)

Shell Sentinel should add a first-class `mistral` provider key that delegates to **`strands.models.mistral.MistralModel`**, following the same thin-integration pattern as LM Studio (factory + config + system prompt), **not** a custom SDK wrapper like Cerebras.

**Path B** (reusing the existing `openai` provider with `base_url: https://api.mistral.ai/v1`) is a valid **short-term operator workaround** documented in the user guide, but it is **not** the preferred product path because it couples Mistral to OpenAI compatibility semantics and creates maintenance ambiguity if Path A is added later.

**Path C** (custom `MistralModel` in `smart_ai_sys_admin/agent/providers/`) is **not justified** for the current TUI use case: Strands already ships a maintained adapter that uses the official `mistralai` v2 client, supports streaming, function calling, and structured output.

| Decision | Choice |
|----------|--------|
| Primary integration | **A+ — Strands `MistralModel` + `ShellMistralModel` wrapper** |
| Interim without code changes | **B — OpenAI-compat bridge** (optional doc-only) |
| Custom SDK provider | **C — Reject** unless Strands adapter gaps are proven in a future PoC |

**Estimated implementation effort (Path A+):** completed in 1.2.0 — see `ShellMistralModel`, `providers.mistral` in `conf/agent.conf.example`.

---

## 2. Scope and methodology

### In scope

- Shell Sentinel agent stack: Strands SDK, `conf/agent.conf`, TUI `AgentRuntime`, built-in tools, optional MCP (e.g. Firecrawl).
- Mistral cloud: La Plateforme API, official Python SDK `mistralai` 2.x.
- Three integration paths: Strands native, OpenAI-compatible endpoint, custom provider.

### Out of scope

- Local inference (Ollama, LM Studio) — already covered by `local` / `lmstudio` providers.
- Live API smoke tests, cost benchmarking, production rollout.

### Method

1. Code audit of Shell Sentinel provider layer and tool requirements.
2. Audit of `strands.models.mistral.MistralModel` in the pinned Strands 1.45.0 environment.
3. Review of Mistral public documentation and `mistralai` SDK README (PyPI 2.5.0, GitHub client-python).
4. Comparative scoring against TUI requirements.

---

## 3. Current state — Shell Sentinel + Strands

### 3.1 Supported providers today

| Key | Model class | Notes |
|-----|-------------|-------|
| `bedrock` | `BedrockModel` | AWS credentials, region |
| `openai` | `OpenAIModel` | `OPENAI_API_KEY`, optional `base_url` |
| `local` | `OllamaModel` | Local Ollama host |
| `lmstudio` | `OpenAIModel` | OpenAI-compatible local server |
| `cerebras` | Custom `CerebrasModel` | Official SDK, SSE streaming |

**Mistral is not registered.** Evidence:

- `ProviderLiteral` in `src/smart_ai_sys_admin/agent/config.py` lists only the five keys above.
- `AgentFactory._build_model()` has no Mistral branch.
- `conf/agent.conf.example` has no `providers.mistral` block.
- No `system_prompts/mistral.md`.
- `_format_provider_label()` in `runtime.py` has no `"mistral"` entry.

### 3.2 Integration pattern (extension points)

Adding a provider requires changes aligned with `docs/custom_model_providers_en.md`:

| Layer | File | Role |
|-------|------|------|
| Config | `agent/config.py` | `ProviderLiteral`, dataclass, JSON parsing |
| Factory | `agent/factory.py` | `_build_<provider>_model()` |
| Runtime UI | `agent/runtime.py` | Footer label in `/status` |
| Prompt | `system_prompts/<provider>.md` | Operator instructions (Spanish content) |
| Example | `conf/agent.conf.example` | Operator template |
| Tests | `tests/unit/test_agent_config.py` | Provider parsing |
| Deps | `pyproject.toml`, lockfiles | Optional extras |

**Thin path (LM Studio):** wrap an existing Strands model class — no custom `Model` subclass in Shell Sentinel.

**Heavy path (Cerebras):** custom `Model` in `agent/providers/` when Strands has no suitable adapter.

### 3.3 TUI agent requirements (from code)

| Requirement | Implementation | Mistral relevance |
|-------------|----------------|-------------------|
| Streaming responses | `agent.streaming` + Strands `Agent` | Required for responsive TUI |
| Function / tool calling | `DEFAULT_STRANDS_TOOLS` + MCP tools | Core workflow: `remote_ssh_command`, SFTP, file tools, optional Firecrawl (~26 MCP tools observed in production sessions) |
| Long SSH output in context | `remote_command.max_output_chars` (default 120k in example config); sliding window truncates tool results | Model context window must accommodate system prompt + history + tool payloads |
| Credentials via env | `api_key_env` pattern | `MISTRAL_API_KEY` (Strands default) |
| Non-interactive tool consent | `tools.consent.bypass` + `ToolPermissionManager` | Provider-agnostic |
| `show_thinking` | Strips `<think>` in `AgentRuntime` | Mistral reasoning models (e.g. Magistral) may need validation; not same as Anthropic extended thinking |
| Locale-aware system prompt | `_prepend_language_directive()` | Same as other providers |

**Default tool set** (`agent/tools.py`):

- Strands tools: `shell`, `file_read`, `file_write`, `sleep`
- App tools: `local_datetime`, `remote_ssh_command`, `remote_sftp_transfer`
- Plus MCP tools when enabled in `conf/agent.conf`

**Note:** `tools.default` in config is parsed but `AgentRuntime` currently passes the full default tool list regardless — high tool surface area for any provider.

### 3.4 Dependencies today

```text
strands-agents[openai,ollama]>=1.45.0
cerebras_cloud_sdk>=1.67.0   # custom Cerebras only
```

`mistralai` is **not** installed until `strands-agents[mistral]` (or direct `mistralai>=2.0,<3.0`) is added.

---

## 4. Strands `MistralModel` audit (SDK path already inside Strands)

Strands Agents **1.45.0** includes `strands/models/mistral.py`, importing:

```python
from mistralai.client import Mistral
```

Extra dependency (from Strands METADATA): `mistralai>=2.0,<3.0` with optional extra `strands-agents[mistral]`.

### 4.1 Capabilities

| Feature | Supported | Notes |
|---------|-----------|-------|
| Chat completions | Yes | `chat.complete_async`, `chat.stream_async` |
| Streaming | Yes | Default `stream: True`; emits Strands `StreamEvent` |
| Function calling | Yes | Tools formatted as OpenAI-style function definitions |
| Structured output | Yes | Via forced tool call + Pydantic schema |
| System prompt | Yes | Prepended as `role: system` message |
| API key | Yes | Constructor arg or `MISTRAL_API_KEY` env var |

### 4.2 Configuration surface (`MistralConfig`)

| Parameter | Purpose |
|-----------|---------|
| `model_id` | e.g. `mistral-large-latest`, `codestral-latest` |
| `max_tokens` | Completion cap |
| `temperature` | 0.0–1.0 (warns if > 0.7) |
| `top_p` | Nucleus sampling |
| `stream` | Streaming toggle |

### 4.3 Known limitations (from Strands source)

| Limitation | Impact on Shell Sentinel |
|------------|-------------------------|
| `tool_choice` parameter **ignored** | Low for current agent — Strands warns but tools still sent; agent loop selects tools organically |
| Location sources in content blocks skipped | None today — no geo content in prompts |
| `ModelThrottledException` on rate limits | Operators may see failures under heavy MCP usage; retry/backoff is SDK-side |
| New `Mistral` client per `stream()` call (`async with Mistral(...)`) | Possible extra latency vs persistent client; unlikely blocker for interactive TUI |
| Debug logs may include full `request=<%s>` | Align with existing DEBUG logging policy; no credential in request body |

### 4.4 Conclusion on Strands adapter

The Strands `MistralModel` **already wraps the official Mistral SDK**. Shell Sentinel does **not** need a separate “direct SDK” path (Path C) unless a future PoC proves Strands adapter is broken for our tool+MCP workload.

---

## 5. Mistral cloud and `mistralai` SDK (external)

### 5.1 Platform and authentication

- **Console:** [La Plateforme](https://console.mistral.ai)
- **Documentation:** [docs.mistral.ai](https://docs.mistral.ai)
- **API key:** Environment variable `MISTRAL_API_KEY` (documented by Mistral and Strands)
- **Python SDK:** `mistralai` 2.x (PyPI latest 2.5.0 at time of study); GitHub [mistralai/client-python](https://github.com/mistralai/client-python)
- **SDK v2:** Official migration from v1; uses `Mistral` client with `chat.complete_async` / `chat.stream_async`

### 5.2 API surface relevant to Shell Sentinel

- **Chat completions:** `POST /v1/chat/completions` (documented in Mistral API reference)
- **OpenAI compatibility:** Mistral exposes an OpenAI-compatible REST API at `https://api.mistral.ai/v1` (industry-standard pattern; used by Path B)
- **Function calling:** Documented capability including **parallel function calling** ([Function Calling](https://docs.mistral.ai/capabilities/function_calling))
- **Streaming:** SSE streaming supported in SDK and API

### 5.3 Model lineup (cloud — indicative)

Mistral documentation lists model aliases including (non-exhaustive):

| Model alias | Typical use for sysadmin TUI |
|-------------|----------------------------|
| `mistral-large-latest` | General reasoning + tools |
| `mistral-medium-latest` | Balance cost/capability |
| `codestral-latest` | Code/shell-oriented tasks |
| `devstral-latest` / `devstral-small-latest` | Agentic / dev workflows |
| `magistral-medium-latest` / `magistral-small-latest` | Reasoning-focused |
| `ministral-*` | Smaller/faster variants |

**Operator guidance:** Prefer `mistral-large-latest` or `codestral-latest` for SSH diagnostics with tools; validate context limits on the chosen model in Mistral model docs before relying on very large `max_output_chars` tool returns.

### 5.4 Function calling vs Shell Sentinel tool load

Mistral supports tool definitions and parallel tool calls. Shell Sentinel may expose **7+ built-in tools plus dozens of MCP tools** when Firecrawl is enabled.

| Risk | Severity | Mitigation |
|------|----------|------------|
| Tool schema/token overhead | Medium | Keep MCP disabled unless needed; sliding window + `truncate_tool_results` |
| Model-specific tool limits | Medium | Document recommended models; future PoC with full MCP enabled |
| Rate limiting under multi-step agent loops | Medium | Monitor `ModelThrottledException`; tune concurrency |

**Desk research gap:** Exact maximum tools per request for each model was not validated without live API calls. Mark as **PoC follow-up** before declaring full MCP parity.

### 5.5 Data residency and compliance

Mistral AI cloud processing is subject to Mistral’s terms and regional offerings on La Plateforme. Operators handling regulated infrastructure should review:

- [Mistral privacy / terms](https://docs.mistral.ai) and enterprise agreements
- Whether prompts containing SSH output, hostnames, or credentials may leave the operator environment

Shell Sentinel already warns against logging secrets; cloud LLM use adds **data egress** risk independent of provider choice.

---

## 6. Path comparison — A / B / C

### Path A — Strands `MistralModel` (recommended)

**How it works:** Add `providers.mistral` in `conf/agent.conf`; factory builds `strands.models.mistral.MistralModel` with `api_key` from `MISTRAL_API_KEY` or `api_key_env`.

**Example config sketch (not shipped in this study):**

```json
"mistral": {
  "system_prompt": "system_prompts/mistral.md",
  "model_id": "mistral-large-latest",
  "show_thinking": false,
  "api_key_env": "MISTRAL_API_KEY",
  "client_args": {},
  "params": {
    "temperature": 0.3,
    "max_tokens": 8192,
    "stream": true
  }
}
```

**Pros**

- Official SDK via maintained Strands adapter
- Native streaming + tools + structured output
- Consistent with architecture (`Agent` + Strands `Model`)
- Low Shell Sentinel code surface (mirror LM Studio)

**Cons**

- New dependency: `mistralai`
- Strands `tool_choice` ignored
- Per-request client instantiation in Strands adapter

### Path B — Existing `openai` provider + Mistral base URL

**How it works:** Set `"provider": "openai"` with:

```json
"client_args": {
  "api_key_env": "MISTRAL_API_KEY",
  "base_url": "https://api.mistral.ai/v1"
},
"model_id": "mistral-large-latest"
```

**Pros**

- **Zero code changes** — works today in theory
- Fastest way for power users to trial Mistral

**Cons**

- OpenAI compatibility layer may diverge (tools, streaming edge cases, error formats)
- `max_tokens` vs `max_completion_tokens` mapping follows OpenAI provider logic
- Product confusion: footer shows “OpenAI” while using Mistral
- Dual maintenance if Path A is added later

### Path C — Custom `MistralModel` in Shell Sentinel (Cerebras pattern)

**How it works:** Implement `smart_ai_sys_admin.agent.providers.mistral` subclassing `strands.models.Model`, calling `mistralai` directly.

**Pros**

- Full control over client lifecycle, logging, retries
- Could optimize for Shell Sentinel-specific quirks

**Cons**

- Duplicates Strands `MistralModel` (~550 lines)
- Highest maintenance burden on SDK upgrades
- No identified capability gap vs Path A

**Verdict:** **Do not pursue** unless Path A fails PoC.

---

## 7. TUI requirement coverage matrix

Legend: **C** Covered | **P** Partial | **U** Unknown (needs PoC) | **N** Not covered

| Requirement | Path A (Strands) | Path B (OpenAI compat) | Path C (Custom) |
|-------------|------------------|------------------------|-----------------|
| Streaming in TUI | C | P (compat dependent) | C |
| `remote_ssh_command` / SFTP | C | C | C |
| Built-in Strands tools | C | P | C |
| MCP tools (large set) | P | P | P |
| Env-based API key | C | C | C |
| `/status` provider label | C (after wiring) | N (shows OpenAI) | C |
| `show_thinking` / reasoning | U | U | U |
| Structured output (if used by Strands internals) | C | P | C |
| Rate limit handling | P (`ModelThrottledException`) | P | P |
| Regression risk on 1.1.x | Low | Low | High |

---

## 8. Weighted decision matrix

| Criterion | Weight | Path A | Path B | Path C |
|-----------|--------|--------|--------|--------|
| TUI fit (stream + tools + context) | High | **Strong** | Moderate | Strong |
| Implementation / maintenance effort | High | **Low–medium** | **Minimal** | High |
| Strands architecture alignment | Medium | **Strong** | Weak | Moderate |
| Regression risk | Medium | **Low** | Low | High |
| Dependencies / licensing | Low | Accept (+`mistralai`) | **None** | Accept (+`mistralai`) |
| Operator clarity (product UX) | Medium | **Strong** | Weak | Strong |

**Weighted outcome:** Path A wins on all high-weight criteria except immediate zero-effort trial, where Path B wins briefly.

**Recommended product strategy:** Implement **Path A** as the supported integration; optionally document **Path B** in user guide as an advanced workaround until Path A ships.

---

## 9. Risks and mitigations

| Risk | Description | Mitigation |
|------|-------------|------------|
| Tool overload | Many MCP + built-in tools | Disable MCP by default; document model choice; PoC with real workload |
| Context overflow | Large SSH dumps in tool results | Existing sliding window + truncation; tune `max_tokens` / model |
| Secret leakage to cloud | Prompts contain host output | Operator policy; existing log redaction for `/connect`; warn in docs |
| Throttling | 429 under agent loops | Retry in SDK; reduce parallel tool fan-out |
| Strands adapter bugs | Edge cases in tool streaming | PoC before release; pin Strands version |
| Dual paths (A + B) | Operator confusion | Deprecate B doc once A is released |

---

## 10. Implementation backlog (if Path A approved)

**Not part of this study deliverable** — reference for next sprint on `evolutiva/mejoras`:

| File | Change |
|------|--------|
| `pyproject.toml` | `strands-agents[mistral,openai,ollama]` or add `mistralai` explicitly |
| `requirements.txt` / lockfiles | `make lock` |
| `src/smart_ai_sys_admin/agent/config.py` | `MistralProviderConfig`, `"mistral"` in `ProviderLiteral` |
| `src/smart_ai_sys_admin/agent/factory.py` | `_build_mistral_model()` → `MistralModel` |
| `src/smart_ai_sys_admin/agent/runtime.py` | `"mistral": "Mistral AI"` label |
| `system_prompts/mistral.md` | Operator prompt (Spanish) |
| `conf/agent.conf.example` | Example block |
| `tests/fixtures/agent.conf.minimal.json` | Parsing test |
| `tests/unit/test_agent_config.py` | Parametrize mistral |
| `docs/user_guide_{en,es,de}.md` | Operator setup (`MISTRAL_API_KEY`, model IDs) |
| `docs/custom_model_providers_*.md` | Optional “Practical case: Mistral” section |

**Optional follow-up PoC (not done here):**

1. Set `MISTRAL_API_KEY`, enable `mistral` provider (after implementation).
2. Connect to test server; run one agent turn invoking `local_datetime` + `remote_ssh_command`.
3. Repeat with MCP Firecrawl enabled; observe tool count and throttling.

---

## 11. References

### Shell Sentinel (codebase)

- `src/smart_ai_sys_admin/agent/config.py` — provider schema
- `src/smart_ai_sys_admin/agent/factory.py` — model factory
- `src/smart_ai_sys_admin/agent/runtime.py` — agent lifecycle
- `src/smart_ai_sys_admin/agent/tools.py` — tool registry
- `docs/custom_model_providers_en.md` — integration checklist
- `conf/agent.conf.example` — operator configuration

### Strands Agents SDK 1.45.0

- `strands/models/mistral.py` — `MistralModel` implementation
- Optional extra: `strands-agents[mistral]` → `mistralai>=2.0,<3.0`
- Documentation: [Mistral model provider](https://strandsagents.com/docs/user-guide/concepts/model-providers/mistral/) (Strands docs)

### Mistral AI

- [docs.mistral.ai](https://docs.mistral.ai) — platform documentation
- [Function calling](https://docs.mistral.ai/capabilities/function_calling)
- [Models overview](https://docs.mistral.ai/models/)
- [console.mistral.ai](https://console.mistral.ai) — API keys
- [github.com/mistralai/client-python](https://github.com/mistralai/client-python) — SDK v2
- API chat completions: `POST /v1/chat/completions`

---

## 12. API PoC validation (2026-06-29)

A contained integration suite exercises the target model against the live API:

| Item | Value |
|------|-------|
| Suite | `tests/integration/mistral/` |
| Run | `make test-mistral` (requires `MISTRAL_API_KEY`) |
| Model | `mistral-medium-3.5` |
| Reasoning | `reasoning_effort=high` (SDK direct calls) |
| Result | **8/8 tests passed** |

### What was validated

| Scenario | SDK (`mistralai`) | Strands `MistralModel` |
|----------|-------------------|------------------------|
| Model listed with chat + tools + reasoning | Yes | N/A |
| Chat with `reasoning_effort=high` | Yes | Not yet (config gap) |
| Single tool call (`remote_ssh_command` schema) | Yes | Yes (streaming) |
| Tool selection among 21 schemas | Yes | Request serialization only |
| Streaming text events | N/A | Yes |
| `reasoning_effort` only `high` \| `none` for this model | Documented | N/A |

### Residual gaps before production wiring

1. **Strands adapter:** `MistralModel.MistralConfig` does not expose `reasoning_effort`; Path A factory should pass it via config extension or `client_args` once Strands supports it (or thin override in `format_request`).
2. **Full agent load:** PoC used 21 synthetic tools, not the full Shell Sentinel stack (~30+ with MCP Firecrawl). Operational risk is reduced but not eliminated.
3. **Dependency:** add `strands-agents[mistral]` (or `mistralai`) to runtime `requirements.txt` when implementing Path A.

### Conclusion

The PoC **supports Path A** with low integration risk for chat, streaming, and function calling. The main follow-up is product wiring (config/factory/prompt) plus optional `reasoning_effort` in operator config.

---

## 13. Sign-off checklist (study closure)

| Criterion | Status |
|-----------|--------|
| Explicit recommendation (A / B / C) | **A** (+ optional B as interim doc) |
| Each TUI requirement scored per path | Section 7 |
| File list for future implementation | Section 10 |
| Live API PoC with contained test suite | **Done** — `make test-mistral`, 12/12 pass (incl. ShellMistralModel) |
| Product wiring (config/factory/prompt/docs) | **Done** — release 1.2.0 |
| Mistral cloud scope only | Confirmed |
