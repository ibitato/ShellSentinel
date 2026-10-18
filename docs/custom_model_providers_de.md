# Leitfaden — Benutzerdefinierte Modell-Provider im Strands Agents SDK

## Umfang

Dieses Dokument fasst die Schritte und Kriterien für die Implementierung benutzerdefinierter Modell-Provider für das Strands Agents SDK in Shell Sentinel zusammen. Es ergänzt die offizielle Dokumentation und dient als interne Checkliste.

## Voraussetzungen

- Vertrautheit mit der Hierarchie `strands.models.Model` (offizielle Beispiele wie `BedrockModel` prüfen).
- Verständnis der Strands-Typen `Messages`, `StreamEvent` und `ToolSpec`.
- Python-Client (synchron oder asynchron) für den proprietären LLM-Dienst.
- Deklarative Konfiguration in `conf/` (Schlüssel, Modell-IDs, Parameter) und Credentials über Umgebungsvariablen.

## Implementierungsablauf

1. **Eigene Konfiguration definieren**: typisierte `ModelConfig` (z. B. `TypedDict`) mit unterstützten Parametern (`model_id`, `params`, …) und `get_config`/`update_config` für Hot-Updates.
2. **Client initialisieren**: im Konstruktor Credentials aus der sicheren Umgebung auflösen, Remote-Client instanziieren und Logging registrieren (`smart_ai_sys_admin.agent`).
3. **`stream(...)` implementieren**:
   - `messages`, `tool_specs` und `system_prompt` empfangen und in das Format des externen Dienstes konvertieren.
   - Client aufrufen und Antwort an das `StreamEvent`-Protokoll anpassen (`messageStart`, `contentBlockDelta`, `messageStop`, `metadata`, …).
   - Fehler (`ContextWindowOverflowException`, Timeouts, Authentifizierung) mit hilfreichen Traces behandeln.
   - Bei synchronem SDK `asyncio.to_thread` oder einen Wrapper nutzen, um den Event Loop nicht zu blockieren.
4. **Tools und strukturierte Ausgaben**: `stream` in `structured_output(...)` wiederverwenden, Pydantic-Modelle in `ToolSpec` umwandeln, Antwort validieren und fehlende Tool Calls als Fehler behandeln.
5. **Provider registrieren**: Klasse in `smart_ai_sys_admin.agent` (Modell-Fabrik) exponieren und Konfiguration in `conf/agent.conf` ergänzen.

## Zusätzliche Hinweise

- Logging auf `DEBUG` für einfacheres Troubleshooting in Produktion.
- Neue Parameter in `docs/user_guide_*.md` dokumentieren, wenn sie Operator-Workflows betreffen.
- Keine Tokens oder Endpoints hardcoden; Umgebungsvariablen und `conf/` verwenden.
- Smoke-Tests oder manuelle Skripte vor der TUI-Integration ausführen.

## Praxisbeispiel: OpenAI Responses API

Shell Sentinel wählt den Endpoint über `providers.openai.api`: `chat_completions` ist der Standard und nutzt `/v1/chat/completions`; `responses` nutzt `/v1/responses`. Gemeinsame Eingaben werden je Endpoint normalisiert: `max_tokens` wird für Chat Completions zu `max_completion_tokens` oder für Responses zu `max_output_tokens`; `reasoning_effort`/`reasoning.effort` wird ebenfalls in die passende Form konvertiert.

Auslöser der Migration war ein HTTP 400 von `gpt-5.6-sol`: Chat Completions unterstützt Function Tools nicht zusammen mit aktivem `reasoning_effort`. Shell Sentinel hängt Tools an administrative Turns an, daher kann das Weglassen des Parameters oder `medium` fehlschlagen; andere GPT-5.x-Modelle können still auf null Reasoning-Tokens zurückfallen. `reasoning_effort: "none"` verhindert den Fehler, weil Reasoning deaktiviert wird (`reasoning_tokens=0`), nicht weil beide Funktionen kompatibel werden. Responses unterstützt Function Tools mit `reasoning.effort: "medium"`.

Referenzkonfiguration ohne Secrets:

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

Die effektive Anfrage nutzt `reasoning: {"effort": "medium"}` und `max_output_tokens: 32768`; die reale Repository-Konfiguration nutzt `max_tokens: 65536`. Responses akzeptiert optional auch `temperature: 0.3`, dies ist jedoch kein Standardwert. `OPENAI_API_KEY` wird aus der Umgebung gelesen.

Optionales `stateful` kann `previous_response_id` beibehalten, beseitigt aber eine bekannte Einschränkung nicht: `reasoningContent` wird beim Rekonstruieren von Multi-Turn-Gesprächen noch nicht vollständig unterstützt. Der Provider filtert diese Verlaufsblöcke; das Modell denkt in jedem Turn nach, verliert zwischen Turns jedoch einen Teil der Reasoning-Kontinuität.

## Praxisbeispiel: LM Studio

- LM Studio stellt einen lokalen OpenAI-kompatiblen Server bereit (`/v1/*`). `base_url`, `api_key` (oder `api_key_env`) und `model_id` in `providers.lmstudio` setzen, um Strands `OpenAIModel` ohne Änderungen zu nutzen.
- Server mit `lms server start` starten (Headless möglich). `timeout` und weitere Argumente über `client_args` anpassen.
- Die native REST-API (`/api/v0/*`) liefert Metriken für Telemetrie (TTFT, Tokens/s).
- `GET /api/v0/models/<model_id>` liefert `max_context_length` für sinnvolle `max_completion_tokens` (z. B. `openai/gpt-oss-20b` mit 131072 Kontext-Tokens).

## Praxisbeispiel: Mistral AI (Pfad A+)

- Shell Sentinel liefert `ShellMistralModel`, einen Wrapper über Strands `MistralModel` (offizielles `mistralai` v2 SDK). Konfiguriere `providers.mistral` mit `model_id`, `api_key_env`/`MISTRAL_API_KEY`, `reasoning_effort` und `params`.
- **Standardwerte:** `mistral-medium-3.5`, `reasoning_effort: high` (Pflicht bei Reasoning-Modellen), `max_tokens: 16184`.
- Der Wrapper injiziert `reasoning_effort` in jede API-Anfrage und mappt Thinking-Chunks auf `reasoningContent`-Stream-Events (`show_thinking`).
- Validierung mit `make test-mistral`, wenn `MISTRAL_API_KEY` gesetzt ist.

## Praxisbeispiel: Google Gemini

- Shell Sentinel nutzt Strands' `GeminiModel` (`strands.models.gemini`, Extra `gemini` von `strands-agents`, offizielles `google-genai`-SDK) direkt; es gibt keinen eigenen Wrapper. `AgentFactory._build_gemini_model` baut es aus `providers.gemini`: `model_id`, `params` und `client_args`.
- **Anmeldedaten:** `api_key_env` benennt die Umgebungsvariable mit dem Schlüssel (standardmäßig `GEMINI_API_KEY`). Ist sie leer, probiert die Factory zusätzlich `GEMINI_API_KEY` und `GOOGLE_API_KEY`, die Namen, die das SDK kennt, und wirft `AgentConfigError`, wenn keine gesetzt ist. `api_key` wird sowohl auf oberster Ebene als auch in `client_args` abgelehnt. Mit `client_args.vertexai: true` (plus `project`/`location`) ist kein Schlüssel nötig, weil das SDK Google-Cloud-ADC-Anmeldedaten verwendet.
- **Parameter:** `params` wird als `GenerateContentConfig` übergeben (`temperature`, `top_p`, `max_output_tokens`, `thinking_config`, `safety_settings`...). Der gemeinsame Schlüssel `max_tokens` wird zu `max_output_tokens` normalisiert, sofern dieser nicht bereits vorhanden ist. Das Beispiel nutzt `gemini-3.8-flash`, `temperature: 0.3` und `max_tokens: 16384`.
- **Streaming und Thinking:** `GeminiModel.stream` mappt Function Calls auf `toolUse`, `thought`-Parts auf `reasoningContent` (sichtbar mit `show_thinking`) und bewahrt Thought-Signaturen über Turns hinweg. Das Usage kommt als `prompt_token_count` + `tool_use_prompt_token_count` (`inputTokens`), `candidates_token_count` + `thoughts_token_count` (`outputTokens`) und `cached_content_token_count` (`cacheReadInputTokens`).
- **Prompt-Caching:** `GeminiModel` akzeptiert kein `CacheConfig` und verwirft `cachePoint`-Blöcke mit einer Warnung; daher startet `providers.gemini.cache` mit `enabled: false`, und ein aktivierter Block wird mit einer Factory-Warnung ignoriert. Gemini cacht Präfixe serverseitig implizit; was es als gecacht meldet, zeigt `/status` weiterhin an.
- Die Live-E2E-Suite hat eine Zeile `gemini` in `tests/e2e/providers.py` (`RUN_E2E=1 SHELL_SENTINEL_E2E_PROVIDERS=gemini`).

## Prompt-Caching

- Jeder Provider-Block in `conf/agent.conf` akzeptiert ein optionales Objekt `cache` mit denselben Feldern wie Strands' `CacheConfig` (`strands.models.model`): `enabled`, `strategy` (`auto`|`anthropic`), `ttl`, `system_prompt_ttl`, `tools_ttl` und `cache_key`. `AgentFactory` wandelt es mit `build_strands_cache_config` um und übergibt `cache_config=` an `BedrockModel`, `OpenAIModel`, `OpenAIResponsesModel` und `ShellMistralModel` (das es an `MistralModel` weiterreicht).
- **Bedrock** benötigt explizite Cache-Points. Der Standard `enabled: true` + `strategy: "auto"` lässt Strands sie nur bei Claude/Anthropic-Modell-IDs setzen; andere Modelle bleiben unverändert. `ttl` akzeptiert `5m`/`1h`; `system_prompt_ttl` und `tools_ttl` akzeptieren `true`/`false` oder einen TTL-String.
- **OpenAI und Mistral** cachen Präfixe serverseitig und verwenden nur `cache_key` (gesendet als `prompt_cache_key`; OpenAI berücksichtigt zusätzlich `ttl`, wenn es `in_memory` oder `24h` ist). Shell Sentinel nutzt keinen Strands-Session-Manager; ist `cache_key` nicht gesetzt, leitet die Factory `shell-sentinel-<sha256(Konfigurationspfad + model_id)[:16]>` über `derive_cache_key` ab, sodass wiederholte Sitzungen ein Präfix teilen. `cache_key: false` sendet keinen Schlüssel.
- **LM Studio** nutzt `OpenAIModel`, startet aber mit `enabled: false`, weil es lokal cacht; beim Aktivieren wird derselbe Routing-Schlüssel gesendet. **Ollama, Cerebras und Gemini** haben keine Cache-Behandlung: ein aktivierter Block wird mit einer Warnung des Loggers `smart_ai_sys_admin.agent.factory` ignoriert.
- Strands erfasst `cacheReadInputTokens`/`cacheWriteInputTokens` in den Agent-Metriken. `AgentRuntime` fasst die letzte Invocation zusammen (`summarize_cache_usage`), protokolliert sie auf INFO und stellt sie `/status` bereit. Strands' `MistralModel` füllt diese Felder nicht, daher überschreibt `ShellMistralModel` den `metadata`-Chunk und kopiert `prompt_tokens_details.cached_tokens` (`data.usage` beim Streaming, `response.usage` ohne Streaming) nach `cacheReadInputTokens`; `inputTokens` bleibt wie bei OpenAI gleich `prompt_tokens`. Fehlt das Feld, wird das Usage unverändert weitergegeben.

## Turn-Limit pro Anweisung

- `agent.max_turns` in `conf/agent.conf` (Standard `25`, `null`/`0` deaktiviert) wird in `AgentOptions.max_turns` geladen und als positive Ganzzahl validiert. `AgentRuntime.invoke` übergibt es an Strands als `agent(prompt, limits={"turns": N})`; der Event-Loop prüft das Limit zu Beginn jedes Zyklus, sodass die im letzten Turn angeforderten Tools immer abschließen und `agent.messages` erneut aufrufbar bleibt.
- Beim Erreichen des Limits liefert Strands ein `AgentResult` mit `stop_reason == "limit_turns"`, statt weiter zu rekursieren. Die Runtime hängt die lokalisierte Meldung `agent.invoke.turn_limit` an den vom Modell erzeugten Text an und protokolliert ein WARNING. Ein eigener Provider braucht nichts Zusätzliches: Das Limit lebt im Event-Loop von Strands, unabhängig von der Modellimplementierung. Es ist das Sicherheitsnetz in Produktion gegen Provider, die gestreamte Tool-Call-Deltas falsch gruppieren und dem Tool immer wieder eine leere Eingabe übergeben.

## Praxisbeispiel: Cerebras

- Offizielles SDK (`cerebras_cloud_sdk`) in ein benutzerdefiniertes `Model` für SSE-Streaming und Tool-Support integrieren. In `providers.cerebras` `model_id`, `params`, `client_args` und Schlüsselreferenz (`api_key_env` oder `CEREBRAS_API_KEY`) definieren.
- Persistenter `AsyncCerebras`-Client; nicht bei jedem Aufruf neu instanziieren.
- `stream()` wandelt `ChatChunkResponse` in native `StreamEvent` um; `metadata` mit Nutzung und Zeiten.
- Für strukturierte Ausgaben `ToolSpec` erzeugen, `tool_choice` erzwingen und `tool_call.function.arguments` parsen.

## Externe Referenzen

- Offizielle Dokumentation: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/custom_model_provider/
- Beispielcode (`BedrockModel`): https://github.com/strands-agents/sdk-python/blob/main/src/strands/models/bedrock.py
