# Benutzerhandbuch — Shell Sentinel (DE)

## Überblick
Shell Sentinel ist eine Terminal-Anwendung, die eine persistente SSH/SFTP-Sitzung zu einem entfernten Server aufbaut und einen KI-Assistenten bereitstellt, der Anweisungen in natürlicher Sprache in sichere Administrationsaufgaben umsetzt.

## Voraussetzungen
- Terminal mit Farbfähigkeiten (empfohlen: `xterm` oder `xterm-256color`).
- Python 3.12.
- Zugriff auf einen Server mit aktivem SSH/SFTP.

## Installation
1. **Virtuelle Umgebung erstellen**:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. **Abhängigkeiten installieren**:
   ```bash
   make install
   ```

## Sprachkonfiguration
Die Anwendung erkennt die Sprache über `SMART_AI_SYS_ADMIN_LOCALE`. Wenn diese Variable nicht gesetzt ist, wird das Systemlocale verwendet (Standard: Englisch).

Beispiele:
```bash
export SMART_AI_SYS_ADMIN_LOCALE=de   # Deutsch
export SMART_AI_SYS_ADMIN_LOCALE=en   # Englisch
export SMART_AI_SYS_ADMIN_LOCALE=es   # Spanisch
```

## Start der Anwendung
```bash
make run
```

Zu Beginn erscheint ein Willkommensbildschirm, der sich nach 5 Sekunden automatisch schließt oder sobald du eine Taste drückst.

## Oberfläche
- **Gesprächspanel**: zeigt Antworten des Assistenten im Markdown-Format.
- **Eingabefeld**: mehrzeilig; standardmäßig sende mit `Ctrl+S`.
- **Fußzeile**: informiert über den SSH-Verbindungsstatus und ob der Agent gerade arbeitet.

## Wichtige Befehle
Alle Befehle stehen auf Englisch, Spanisch und Deutsch zur Verfügung.

- `/connect <host> <user> <password|key_path> [Port]` — baut die SSH-Sitzung auf (Port optional, Standard 22). SFTP wird bei der ersten Dateiübertragung automatisch geöffnet.
- `/disconnect` — beendet die aktive Verbindung.
- `/help` — listet die verfügbaren Befehle.
- `/status` — zeigt den aktuellen Agenten- und Verbindungsstatus.
- `/exit` — öffnet den Bestätigungsdialog zum Beenden.

Nützliche Aliasse: `/conectar`, `/desconectar`, `/ayuda`, `/salir`, `/verbinden`, `/trennen`, `/hilfe`, `/beenden`.

## Arbeiten mit dem KI-Assistenten
Formuliere Anweisungen in natürlicher Sprache. Wenn es kein Slash-Befehl ist, verarbeitet der Strands-Agent die Eingabe. Beispiele:
- "Zeige die Prozesse mit der höchsten CPU-Auslastung".
- "Lade `/tmp/script.sh` nach `/home/ubuntu/bin/script.sh` hoch".

Der Agent nutzt die aktive SSH-Sitzung für Befehle. Dateiübertragungen öffnen SFTP bei Bedarf über dieselbe Verbindung.

## Konfiguration
- `conf/app_config.json` enthält Styles, Texte und Tastenkürzel in Form von Platzhaltern wie `{{ui.output_panel.title}}`, die automatisch für das aktive Locale ersetzt werden.
- Übersetzungen liegen in `conf/locales/<sprache>/strings.json`. Beim Hinzufügen neuer Texte verwende im Code `_('schlüssel')` und ergänze die Einträge in jeder Sprache.
- `conf/agent.conf` steuert den LLM-Provider, Tools und Timeouts. Nutze `conf/agent.conf.example` als Ausgangspunkt.
- OpenAI unterstützt `api: "chat_completions"` (Standard) und `api: "responses"`. Gemeinsame Werte für `max_tokens` und `reasoning_effort`/`reasoning.effort` werden zu `max_completion_tokens` oder `max_output_tokens` und zur vom Endpoint benötigten Reasoning-Form normalisiert. Nutze Responses für GPT-5.x Function Tools mit Reasoning; Chat Completions kann diese Kombination ablehnen oder null Reasoning-Tokens melden. Optionales `stateful` kann `previous_response_id` wiederverwenden, aber rekonstruiertes Multi-Turn-`reasoningContent` behält noch keine vollständige Reasoning-Kontinuität.
- Halte `OPENAI_API_KEY` in der Umgebung. Das Beispiel nutzt `gpt-5.6-sol`, Responses, Reasoning `medium` und `max_tokens: 32768` (effektiv `max_output_tokens`); die reale Konfiguration nutzt `65536`. Bedrock bleibt bei `max_tokens: 8192`, `remote_command.timeout_seconds: 900` und `remote_command.max_output_chars: 120000`.
- Für `lmstudio` führe `lms server start` aus und passe `base_url`/`api_key` an. Für `cerebras` exportiere `CEREBRAS_API_KEY` (oder setze `api_key_env`) und konfiguriere `client_args`/`params`; das offizielle SDK verarbeitet SSE-Streams. Für Mistral (`provider: "mistral"`) exportiere `MISTRAL_API_KEY` und nutze standardmäßig `reasoning_effort: high` sowie `max_tokens: 16184` mit `mistral-medium-3.5`.

## Fehlerbehebung
- **Farb- oder Anzeigeprobleme**: `TERM` prüfen und ggf. auf `xterm-256color` wechseln.
- **Agent reagiert nicht**: `conf/agent.conf`, Zugangsdaten und Logdateien (`logs/app.log`) kontrollieren.
- **Fehler „Keine aktive SSH-Verbindung“**: Vor Agent-Aufgaben zuerst `/connect` ausführen.
- **SFTP- oder Transferfehler nach erfolgreichem `/connect`**: Die Remote-Shell kann Banner in nicht-interaktiven Sitzungen ausgeben (z. B. `pyfiglet` in `~/.bashrc`). Dekorative Ausgabe nur interaktiv erlauben (`[[ $- == *i* ]]`) oder den Administrator bitten, `Subsystem sftp internal-sftp` in `sshd_config` zu setzen.
- **Zugangsdaten in Logs**: `/connect`-Passwörter werden in `logs/app.log` und in der angezeigten Eingabe als `***` maskiert.
