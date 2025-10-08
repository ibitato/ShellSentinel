# Benutzerhandbuch — Shell Sentinel (DE)

## Überblick
Shell Sentinel ist eine Terminal-Anwendung, die eine persistente SSH/SFTP-Sitzung zu einem entfernten Server aufbaut und einen KI-Assistenten bereitstellt, der Anweisungen in natürlicher Sprache in sichere Administrationsaufgaben umsetzt. Das Projekt wurde zuvor als Almost Human Sys Admin veröffentlicht.

## Voraussetzungen
- Terminal mit Farbfähigkeiten (empfohlen: `xterm` oder `xterm-256color`).
- Python 3.10 oder neuer.
- Zugriff auf einen Server mit aktivem SSH/SFTP.

## Installation
1. **Virtuelle Umgebung erstellen**:
   ```bash
   python3 -m venv .venv
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

- `/connect <host> <user> <password|key_path> [Port]` — baut die Remote-Sitzung auf (Port optional, Standard 22).
- `/disconnect` — beendet die aktive Verbindung.
- `/help` — listet die verfügbaren Befehle.
- `/status` — zeigt den aktuellen Agenten- und Verbindungsstatus.
- `/exit` — öffnet den Bestätigungsdialog zum Beenden.

Nützliche Aliasse: `/conectar`, `/desconectar`, `/ayuda`, `/salir`, `/verbinden`, `/trennen`, `/hilfe`, `/beenden`.

## Arbeiten mit dem KI-Assistenten
Formuliere Anweisungen in natürlicher Sprache. Wenn es kein Slash-Befehl ist, verarbeitet der Strands-Agent die Eingabe. Beispiele:
- "Zeige die Prozesse mit der höchsten CPU-Auslastung".
- "Lade `/tmp/script.sh` nach `/home/ubuntu/bin/script.sh` hoch".

Der Agent nutzt die aktive SSH-/SFTP-Sitzung für Befehle und Dateiübertragungen.

## Konfiguration
- `conf/app_config.json` enthält Styles, Texte und Tastenkürzel in Form von Platzhaltern wie `{{ui.output_panel.title}}`, die automatisch für das aktive Locale ersetzt werden.
- Übersetzungen liegen in `conf/locales/<sprache>/strings.json`. Beim Hinzufügen neuer Texte verwende im Code `_('schlüssel')` und ergänze die Einträge in jeder Sprache.
- `conf/agent.conf` steuert den LLM-Anbieter, Tool-Optionen und Timeouts. Nutze `conf/agent.conf.example` als Ausgangspunkt und starte bei Auswahl von `lmstudio` den lokalen Server mit `lms server start`; passe `base_url` und `api_key` an deine Umgebung an. Für `cerebras` exportierst du `CEREBRAS_API_KEY` (oder definierst `api_key_env`) und konfigurierst `client_args`/`params`; der Provider setzt auf das offizielle SDK und verarbeitet SSE-Streams. Mit `remote_command.max_output_chars` begrenzt du, wie viel Ausgabe der Agent erhält.

## Fehlerbehebung
- **Farb- oder Anzeigeprobleme**: `TERM` prüfen und ggf. auf `xterm-256color` wechseln.
- **Agent reagiert nicht**: `conf/agent.conf`, Zugangsdaten und Logdateien (`logs/app.log`) kontrollieren.
- **Fehler „Keine aktive SSH-Verbindung“**: Vor Agent-Aufgaben zuerst `/connect` ausführen.
