# Almost Human Sys Admin

Verfügbar in: [English](README_en.md) · [Deutsch](README_de.md) · [Español](README.md)

## Überblick
Almost Human Sys Admin ist ein terminalbasierter, KI-gestützter Systemadministrator. Die Anwendung hält eine persistente SSH/SFTP-Sitzung zu einem entfernten Server aufrecht und setzt Anweisungen in natürlicher Sprache in sichere und nachvollziehbare Aktionen um.

Hinweis zur Kompatibilität: Paketname und Einstiegspunkt bleiben `smart_ai_sys_admin`, damit bestehende Integrationen weiterhin funktionieren.

## Voraussetzungen
- Python 3.10 oder neuer
- Lokale virtuelle Umgebung (empfohlen `.venv`)

## Erste Schritte
1. Virtuelle Umgebung erstellen:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Laufzeit- und Entwicklungsabhängigkeiten installieren:
   ```bash
   make install
   ```
3. Grundlegende Prüfungen ausführen:
   ```bash
   make format
   make lint
   ```

## Verwendung der CLI
- TUI starten mit:
  ```bash
  make run
  # oder
  python -m smart_ai_sys_admin
  ```
- Die Konsole ist in zwei Bereiche aufgeteilt: Ausgabeverlauf (oben) und Eingabefeld (unten). Die Fußzeile zeigt jederzeit den Status der SSH-Verbindung an.
- Anweisungen werden über das konfigurierte Tastenkürzel gesendet (Standard `Strg+S`).
- Unterstützte Befehle (Alias auf Englisch, Spanisch und Deutsch):
- `/connect <host> <user> <password|key_path> [Port]` (`/conectar`, `/verbinden`) öffnet eine persistente SSH/SFTP-Sitzung (Port optional, Standard 22).
  - `/disconnect` (`/desconectar`, `/trennen`) beendet eine aktive Verbindung.
  - `/help` (`/ayuda`, `/hilfe`) zeigt eine Markdown-Zusammenfassung der verfügbaren Befehle.
  - `/exit` (`/salir`, `/beenden`, `/quit`) öffnet den Bestätigungsdialog zum Beenden.
- Ausgaben erscheinen im Markdown-Format im retro-orangen/grünen Farbschema.
- Für eine optimale Darstellung wird ein Terminal wie `xterm` oder `xterm-256color` empfohlen.

## Konfiguration
- Visuelle Einstellungen und Interaktion (Farben, Shortcuts, Meldungen, Verlaufslimits) liegen in `conf/app_config.json`.
- Der Speicherort der Konfiguration lässt sich mit `SMART_AI_SYS_ADMIN_CONFIG_FILE` (Dateipfad) oder `SMART_AI_SYS_ADMIN_CONFIG_DIR` (Verzeichnis) überschreiben.
- Werte sollten nicht im Quellcode fest verdrahtet werden; aktualisiere stattdessen die Konfiguration und starte die App neu.
- Neue Optionen in `conf/app_config.json`:
  - `ui.connection_panel`: Styles für das Fußzeilenpanel, das den Verbindungsstatus anzeigt.
- `logging`: Standardlevel `DEBUG`, Verzeichnis `logs/`, Dateiname `app.log`, Rotationspolitik (täglich, 3 Backups) über `TimedRotatingFileHandler`.
  - Ausführliche Logger (`markdown_it`, `botocore.parsers`, `paramiko.transport` usw.) werden bei `DEBUG` auf `INFO` reduziert, um Rauschen zu vermeiden.
  - `log_to_console`: spiegelt Logeinträge nach stdout (standardmäßig deaktiviert, um die TUI nicht zu stören).

### Internationalisierung
- Die Oberfläche unterstützt Englisch (Standard), Deutsch und Spanisch. Die Sprache wird über `SMART_AI_SYS_ADMIN_LOCALE` oder – falls nicht gesetzt – über das Systemlocale ermittelt.
- Übersetzbare Texte befinden sich in `conf/locales/<sprache>/strings.json`. Für neue Sprachen eine vorhandene Datei kopieren, die Schlüssel übersetzen und Platzhalter `{...}` unverändert lassen.
- Sprache zur Laufzeit erzwingen:
  ```bash
  export SMART_AI_SYS_ADMIN_LOCALE=de
  make run
  ```
- `conf/app_config.json` enthält Platzhalter `{{übersetzungs.schlüssel}}`, die beim Laden ersetzt werden. Beim Anpassen der Werte die doppelten geschweiften Klammern nicht entfernen.

### Konfiguration des KI-Agenten (Strands Agents)
- Kopiere `conf/agent.conf.example` nach `conf/agent.conf` und wähle im Block `provider` zwischen Amazon Bedrock, OpenAI, LM Studio, Cerebras oder Ollama/lokal.
- Entscheidest du dich für LM Studio, starte den lokalen Server mit `lms server start` und kontrolliere `providers.lmstudio` (`base_url`, `model_id`, `api_key_env`/`api_key`, `client_args`), damit die Einstellungen zu deiner Installation passen.
- Für Cerebras exportierst du `CEREBRAS_API_KEY` (oder setzt `api_key_env`) und passt `providers.cerebras` (`model_id`, `params`, `client_args.timeout`, etc.) an; der Custom Provider nutzt das offizielle SDK und transformiert die SSE-Events.
- Jeder Anbieter besitzt einen eigenen `system_prompt` in `system_prompts/`. Eigene Prompts können per Pfad eingebunden werden.
- Hinterlege Zugangsdaten über Umgebungsvariablen (z. B. `export OPENAI_API_KEY="..."`). Im Konfigurationsfile werden keine Secrets im Klartext gespeichert.
- OpenAI- und Bedrock-Defaults erlauben lange Antworten; das Beispiel setzt `max_completion_tokens` (OpenAI) auf **32 768** und `max_tokens` (Bedrock) auf **8 192**. Passe die Werte an deine Kontingente an.
- Anmeldeinformationen stammen aus der Umgebung (`AWS_*`, `OPENAI_API_KEY` usw.). Du kannst auch `SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE` oder `SMART_AI_SYS_ADMIN_CONFIG_DIR` verwenden, um Dateipfade zu überschreiben.
- In `tools` aktivierst du Strands Agents Tools sowie das benutzerdefinierte `remote_ssh_command`, das die TUI-SSH-Sitzung nutzt (`timeout_seconds` ist optional).
- `remote_ssh_command` verwendet standardmäßig **900 Sekunden (15 Minuten)** laut `conf/agent.conf`. Falls längere Befehle erwartet werden, den Agenten bitten, `timeout_seconds` entsprechend zu setzen.
- Für Model Context Protocol (MCP) Server deklarierst du jeden Transport (`stdio`, `sse`, `streamable_http`) im Abschnitt `mcp`. Die Agentenverbindung bleibt während der Sitzung aktiv und stellt die Tools bereit.
  - Beispiel: Transport `firecrawl-stdio` startet `npx -y firecrawl-mcp`. Über `env_passthrough` erbt der Agent Variablen wie `FIRECRAWL_API_KEY`. Werte vor dem Start der TUI exportieren.
- Beim Start erscheint ein retro-inspirierter Begrüßungsbildschirm (Orange), der sich nach 5 Sekunden oder einem Tastendruck schließt.
- `/connect` hält SSH und SFTP parallel aktiv. Der Agent stellt `remote_sftp_transfer(action, local_path, remote_path, overwrite=False)` bereit, um Dateien hoch- (`upload`/`put`) oder herunterzuladen (`download`/`get`). Der Name lässt sich bei Bedarf über `tools.sftp_transfer.name` anpassen.
- Admin-Aufgaben sind sowohl auf GNU/Linux- als auch auf Windows-Systemen möglich, sofern SSH/SFTP verfügbar ist. Befehle für das Zielsystem (PowerShell/cmd auf Windows) anpassen und Pfade vor Dateiübertragungen prüfen.

### Plugin-System
- Plugins werden automatisch aus dem Verzeichnis `plugins/` geladen (konfigurierbar über `SMART_AI_SYS_ADMIN_PLUGINS_DIR`; mehrere Pfade können mit `:` getrennt angegeben werden). Jede `.py`-Datei muss eine Funktion `register(registry)` bereitstellen.
- Innerhalb von `register(...)` lassen sich mit `PluginSlashCommand` zusätzliche Slash-Befehle definieren. Die Handler-Funktion erhält die Argumentliste der Benutzer:innen und gibt Markdown zurück, das im Chat angezeigt wird. Logging aus dem Plugin integriert sich in das bestehende Log-System der TUI.
- Über `registry.register_translations(locale, payload)` können Plugins eigene Übersetzungen registrieren. Die in `description_key`, `usage_key` und `help_key` referenzierten Schlüssel sollten dort definiert sein, damit Lokalisierung und Hilfe funktionieren.
- Optional lässt sich eine `suggestion(command, args)`-Funktion hinterlegen, um den Autovervollständigungs-Hinweis zu steuern. Ohne diese Funktion wird der Text aus `usage_key` angezeigt.
- Registrierte Befehle erscheinen automatisch in `/help`, nutzen die Eingabe-Historie und folgen denselben Ausgaberegeln wie die eingebauten Commands.

```python
# plugins/credentials.py
from smart_ai_sys_admin.plugins import PluginRegistry, PluginSlashCommand


def _fetch_credentials(args: list[str]) -> str:
    if not args:
        return "⚠️ Bitte den Servernamen angeben."
    server = args[0]
    # Hier könnte eine interne API aufgerufen werden
    return f"Zugangsdaten für `{server}`: user demo / password 1234"


def register(registry: PluginRegistry) -> None:
    registry.register_translations(
        "de",
        {
            "plugins": {
                "credentials": {
                    "description": "Ruft Zugangsdaten von der internen API ab",
                    "usage": "Verwendung: `{command} <server>`",
                    "help": "`{command}` fragt die Unternehmens-API ab und zeigt die Zugangsdaten im Chat.",
                }
            }
        },
    )

    registry.register_command(
        PluginSlashCommand(
            name="/credentials",
            aliases=("/zugangsdaten",),
            handler=_fetch_credentials,
            description_key="plugins.credentials.description",
            usage_key="plugins.credentials.usage",
            help_key="plugins.credentials.help",
        )
    )
```

### Benutzerhandbücher
- Ausführliche Schritt-für-Schritt-Anleitungen findest du in `docs/user_guide_de.md`, `docs/user_guide_en.md` und `docs/user_guide_es.md`. Halte alle Versionen synchron, wenn Funktionen geändert werden.

## Projektstruktur
- `requirements.txt`: Laufzeitabhängigkeiten (Textual, Strands Agents, Community-Tools).
- `requirements-dev.txt`: Entwicklungsabhängigkeiten (`-r requirements.txt`, Linting, Tests).
- `src/smart_ai_sys_admin/`: Hauptquellcode der Anwendung (TUI und Utilities).
- `tests/`: Platzhalter für automatische Tests.
- `Makefile`: Aufgaben zum Installieren, Formatieren, Linten, Testen, Ausführen und Bereinigen.
- `AGENTS.md`: Leitfaden für menschliche Mitwirkende und KI-Agenten.

## Lizenz
- Kostenfrei für Bildung, Studierende und Teams bis zu 5 Personen.
- Für Installationen mit mehr als 5 Arbeitsplätzen/Benutzern ist eine kommerzielle Lizenz mit dem Maintainer zu vereinbaren.
- Vollständige Details siehe `LICENSE` (Almost Human Sys Admin Community License 1.0).

Bei Fragen zu kommerziellen Lizenzen oder erweitertem Support bitte ein GitHub-Issue eröffnen oder den Maintainer direkt kontaktieren.
