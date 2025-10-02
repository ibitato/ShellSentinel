window.TRANSLATIONS = {
  en: {
    nav: {
      product: "Product",
      features: "Features",
      how: "How it works",
      quickstart: "Quick start",
      help: "Help",
      download: "Download",
    },
    hero: {
      badge: "Terminal-native AI agent",
      title: "Automate remote administration with confidence",
      subtitle:
        "Almost Human Sys Admin pairs a retro-styled TUI with an intelligent agent that understands your intent, keeps SSH/SFTP sessions alive and documents every action.",
      primaryCta: "Download (coming soon)",
      secondaryCta: "Explore quick start",
      note:
        "Designed for operations teams that value reliability, auditability and multilingual experiences without leaving the terminal.",
    },
    product: {
      eyebrow: "Overview",
      title: "A companion for demanding sysadmins",
      lead:
        "Built for teams that manage sensitive infrastructure: persistent sessions, safe remote tooling and localized guidance in English, Spanish and German.",
      bullets: [
        "Persistent SSH and SFTP channels orchestrated by an AI agent that understands natural language instructions.",
        "Configurable providers including LM Studio, Cerebras, Amazon Bedrock, OpenAI and Ollama-compatible runtimes.",
        "Audit-friendly design with localized prompts, retro aesthetics and structured logging to track every operation.",
      ],
    },
    features: {
      eyebrow: "Capabilities",
      title: "Product highlights",
      lead:
        "Each module is engineered to deliver operational confidence, from secure connections to dynamic documentation.",
      cards: [
        {
          icon: "🛰️",
          title: "Agentic SSH orchestration",
          body:
            "Maintain a single SSH/SFTP session per host, reuse it for commands or transfers and keep timeouts under control with custom tool permissions.",
        },
        {
          icon: "🌐",
          title: "Multilingual terminal UI",
          body:
            "Switch between English, Spanish and German instantly. Strings live in JSON locales and the TUI resolves them automatically on load.",
        },
        {
          icon: "🧩",
          title: "Custom provider SDK",
          body:
            "Integrate LM Studio, Cerebras or your in-house LLM through Strands SDK custom providers with streaming and tool-calling support.",
        },
        {
          icon: "🛡️",
          title: "Operational safety",
          body:
            "Timeout-aware remote commands, explicit consent policies and local date/time tooling keep the agent grounded before executing actions.",
        },
      ],
    },
    how: {
      eyebrow: "Workflow",
      title: "How it works",
      lead:
        "From bootstrapping the agent to automating repetitive tasks, the flow stays consistent and observable.",
      steps: [
        {
          title: "1. Configure the agent",
          body:
            "Load `conf/agent.conf`, pick your preferred provider and export the required API keys. The app resolves placeholders and secrets at runtime.",
        },
        {
          title: "2. Connect once",
          body:
            "Use `/connect` to establish an SSH/SFTP session. Credentials, key-based auth and custom ports are supported out of the box.",
        },
        {
          title: "3. Brief the agent",
          body:
            "Describe your intent in natural language or fire `/status` to inspect provider, model and streaming configuration before proceeding.",
        },
        {
          title: "4. Execute and audit",
          body:
            "The agent calls `remote_ssh_command` or `remote_sftp_transfer` as needed. Every action is logged with timestamps so you can review later.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Kick-off",
      title: "Quick start in minutes",
      lead:
        "Spin up the local environment, point the agent to your provider of choice and start collaborating with the terminal-native assistant.",
      steps: [
        {
          title: "Prepare the environment",
          body:
            "Create a virtualenv (`python -m venv .venv`) and install dependencies with `make install`.",
        },
        {
          title: "Review the configuration",
          body:
            "Copy `conf/agent.conf.example` to `conf/agent.conf`, adjust providers, tokens and tool permissions. Locale strings live under `conf/locales/`.",
        },
        {
          title: "Launch the TUI",
          body:
            "Run `make run` (or `python -m smart_ai_sys_admin`). You will see the welcome screen, command input area and the status footer.",
        },
        {
          title: "Connect & explore",
          body:
            "Execute `/connect bastion admin-key` to open a session, `/status` to inspect the agent and `/help` for command aliases in all languages.",
        },
      ],
      note:
        "Tip: keep `make format` and `make lint` handy before committing configuration changes or extending the agent.",
    },
    help: {
      eyebrow: "Support",
      title: "Help & knowledge base",
      lead:
        "Comprehensive resources to master the assistant, troubleshoot connections and customize providers.",
      panels: [
        {
          title: "Command palette",
          body:
            "Slash commands power the interaction model. Each command has localized aliases and Markdown output for easy sharing.",
          bullets: [
            "`/connect` · open SSH/SFTP sessions with password or key authentication.",
            "`/disconnect` · close the active session gracefully before exiting.",
            "`/status` · inspect provider, model, streaming flag, config path and SSH status.",
            "`/help` · list every available command including plugin extensions.",
          ],
        },
        {
          title: "Documentation",
          body:
            "Guides ship in English, Spanish and German. Configuration values live in `conf/app_config.json` and are referenced from locales.",
          bullets: [
            "User guides: `docs/user_guide_en.md`, `docs/user_guide_es.md`, `docs/user_guide_de.md`.",
            "Custom providers: `docs/custom_model_providers_es.md` plus Strands SDK notes.",
            "Agent prompts: tune `system_prompts/` to align outputs with your governance.",
          ],
        },
        {
          title: "Troubleshooting",
          body:
            "Keep an eye on `logs/` for detailed traces. The app logs connection attempts, tool invocations and MCP activity at DEBUG level.",
          bullets: [
            "Verify your terminal supports 256 colours (`xterm-256color`).",
            "Ensure credentials are exported before launching the TUI (e.g. `CEREBRAS_API_KEY`).",
            "Timeout-sensitive tasks: ask the agent to raise `timeout_seconds` when needed.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Frequently asked questions",
      lead:
        "Clarify how the assistant integrates with your infrastructure and provider strategy.",
      items: [
        {
          question: "Does the agent execute commands without approval?",
          answer:
            "It reuses the SSH session you opened and honours tool permission policies. You can enforce confirmations or long timeouts in configuration.",
        },
        {
          question: "Can I integrate a different LLM provider?",
          answer:
            "Yes. Extend the Strands SDK custom provider scaffold under `smart_ai_sys_admin/agent/providers/` and register it in `conf/agent.conf`.",
        },
        {
          question: "How do locales work?",
          answer:
            "All visible strings live in `conf/locales/<lang>/strings.json`. The app resolves `{{decorated.keys}}` from `conf/app_config.json` automatically.",
        },
        {
          question: "Is there a graphical dashboard?",
          answer:
            "The experience is intentionally terminal-first to stay close to SSH workflows. Plugins can output Markdown with diagrams if required.",
        },
      ],
    },
    download: {
      eyebrow: "Availability",
      title: "Download & onboarding",
      lead:
        "Official packages are in progress. Keep the quick start guide handy while we prepare installers and signed archives.",
      primaryCta: "Packaging in progress",
      secondaryCta: "Read installation guide",
      note:
        "Want early access to binaries? Subscribe to the product bulletin (coming soon).",
    },
    footer: {
      tagline:
        "Your terminal copilot for critical infrastructure operations with safety and multilingual guidance.",
      linksTitle: "Explore",
      helpTitle: "Help",
      helpCenter: "Help center",
      faq: "FAQ",
      download: "Download",
      contactTitle: "Stay in touch",
      contactBody:
        "Reach out to support@almosthuman.systems to discuss enterprise rollouts or dedicated pilots.",
      rights: "© 2024 Almost Human Sys Admin. All rights reserved.",
      privacy: "Privacy policy",
      terms: "Terms of service",
    },
  },
  es: {
    nav: {
      product: "Producto",
      features: "Funciones",
      how: "Cómo funciona",
      quickstart: "Inicio rápido",
      help: "Ayuda",
      download: "Descarga",
    },
    hero: {
      badge: "Agente IA para terminal",
      title: "Automatiza la administración remota con confianza",
      subtitle:
        "Almost Human Sys Admin combina una TUI de estilo retro con un agente inteligente que entiende tus instrucciones, mantiene vivas las sesiones SSH/SFTP y documenta cada acción.",
      primaryCta: "Descarga (próximamente)",
      secondaryCta: "Ver guía rápida",
      note:
        "Pensado para equipos de operaciones que buscan fiabilidad, trazabilidad y soporte multilingüe sin abandonar la terminal.",
    },
    product: {
      eyebrow: "Resumen",
      title: "Tu copiloto para infraestructuras exigentes",
      lead:
        "Ideal para equipos que gestionan sistemas críticos: sesiones persistentes, herramientas remotas seguras y acompañamiento localizado en inglés, español y alemán.",
      bullets: [
        "Canal SSH y SFTP persistente orquestado por un agente que entiende instrucciones en lenguaje natural.",
        "Proveedores configurables: LM Studio, Cerebras, Amazon Bedrock, OpenAI y runtimes compatibles con Ollama.",
        "Diseño audit friendly con prompts localizados, estética retro y logging estructurado para revisar cada operación.",
      ],
    },
    features: {
      eyebrow: "Capacidades",
      title: "Lo más destacado",
      lead:
        "Cada módulo está diseñado para aportar confianza operativa, desde la conexión segura hasta la documentación dinámica.",
      cards: [
        {
          icon: "🛰️",
          title: "Orquestación SSH agentica",
          body:
            "Mantén una sesión SSH/SFTP por host, reutilízala para comandos o transferencias y controla los timeouts con permisos específicos.",
        },
        {
          icon: "🌐",
          title: "Interfaz multilingüe",
          body:
            "Cambia entre inglés, español y alemán al instante. Las cadenas viven en JSON y la TUI las resuelve automáticamente.",
        },
        {
          icon: "🧩",
          title: "SDK de proveedores",
          body:
            "Integra LM Studio, Cerebras o tu propio LLM mediante los custom providers del Strands SDK con soporte de streaming y herramientas.",
        },
        {
          icon: "🛡️",
          title: "Operación segura",
          body:
            "Comandos remotos conscientes de timeout, políticas de consentimiento y la herramienta de fecha local mantienen al agente anclado a la realidad.",
        },
      ],
    },
    how: {
      eyebrow: "Flujo",
      title: "Cómo funciona",
      lead:
        "Del arranque del agente a la automatización diaria, el flujo es consistente y observable.",
      steps: [
        {
          title: "1. Configura el agente",
          body:
            "Carga `conf/agent.conf`, elige proveedor y exporta las claves necesarias. Los placeholders y secretos se resuelven en tiempo de ejecución.",
        },
        {
          title: "2. Conéctate una vez",
          body:
            "Usa `/connect` para establecer la sesión SSH/SFTP. Soporta credenciales, claves y puertos personalizados.",
        },
        {
          title: "3. Indica tu intención",
          body:
            "Describe lo que necesitas o lanza `/status` para revisar proveedor, modelo y configuración antes de actuar.",
        },
        {
          title: "4. Ejecuta y audita",
          body:
            "El agente invoca `remote_ssh_command` o `remote_sftp_transfer` según corresponda. Todo queda registrado con marcas de tiempo.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Puesta en marcha",
      title: "Inicio rápido en minutos",
      lead:
        "Levanta el entorno local, apunta al proveedor que prefieras y empieza a colaborar con el asistente desde la terminal.",
      steps: [
        {
          title: "Prepara el entorno",
          body:
            "Crea un virtualenv (`python -m venv .venv`) e instala dependencias con `make install`.",
        },
        {
          title: "Revisa la configuración",
          body:
            "Copia `conf/agent.conf.example` a `conf/agent.conf`, ajusta proveedores, tokens y permisos. Las traducciones viven en `conf/locales/`.",
        },
        {
          title: "Lanza la TUI",
          body:
            "Ejecuta `make run` (o `python -m smart_ai_sys_admin`). Verás la pantalla de bienvenida, el input y el footer de estado.",
        },
        {
          title: "Conecta y explora",
          body:
            "Ejecuta `/connect bastion admin-key` para abrir la sesión, `/status` para inspeccionar el agente y `/help` para ver los alias.",
        },
      ],
      note:
        "Consejo: antes de subir cambios, ejecuta `make format` y `make lint` para mantener la calidad.",
    },
    help: {
      eyebrow: "Soporte",
      title: "Centro de ayuda",
      lead:
        "Recursos para dominar el asistente, resolver incidencias y personalizar proveedores.",
      panels: [
        {
          title: "Comandos clave",
          body:
            "Los comandos slash impulsan la experiencia. Cada uno cuenta con alias localizados y salida en Markdown.",
          bullets: [
            "`/connect` · abre sesiones SSH/SFTP con contraseña o clave.",
            "`/disconnect` · cierra la sesión activa antes de salir.",
            "`/status` · revisa proveedor, modelo, streaming, ruta de config y estado SSH.",
            "`/help` · lista los comandos disponibles, incluidos plugins.",
          ],
        },
        {
          title: "Documentación",
          body:
            "Guías en inglés, español y alemán. Los valores de configuración residen en `conf/app_config.json` y referencian las traducciones.",
          bullets: [
            "Guías de usuario: `docs/user_guide_en.md`, `docs/user_guide_es.md`, `docs/user_guide_de.md`.",
            "Proveedores personalizados: `docs/custom_model_providers_es.md` con notas del Strands SDK.",
            "Prompts del agente: ajusta `system_prompts/` para alinearlos con tus políticas.",
          ],
        },
        {
          title: "Resolución de problemas",
          body:
            "Consulta `logs/` para obtener trazas detalladas. La app registra conexiones, tools y MCP en nivel DEBUG.",
          bullets: [
            "Verifica que tu terminal soporte 256 colores (`xterm-256color`).",
            "Exporta las credenciales antes de lanzar la TUI (ej. `CEREBRAS_API_KEY`).",
            "Para comandos largos, pide al agente que ajuste `timeout_seconds`.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Preguntas frecuentes",
      lead:
        "Resolvemos dudas habituales sobre integración y operación del agente.",
      items: [
        {
          question: "¿El agente ejecuta comandos sin control?",
          answer:
            "Reutiliza la sesión SSH que abriste y respeta las políticas de permisos. Puedes exigir confirmaciones o ampliar timeouts en la configuración.",
        },
        {
          question: "¿Puedo integrar otro proveedor de LLM?",
          answer:
            "Sí. Extiende el scaffold de custom providers en `smart_ai_sys_admin/agent/providers/` y regístralo en `conf/agent.conf`.",
        },
        {
          question: "¿Cómo funcionan los idiomas?",
          answer:
            "Todas las cadenas visibles viven en `conf/locales/<idioma>/strings.json`. La app resuelve `{{clave.decorada}}` desde `conf/app_config.json` automáticamente.",
        },
        {
          question: "¿Existe un dashboard gráfico?",
          answer:
            "La experiencia está pensada para terminal. Los plugins pueden generar Markdown enriquecido si necesitas más visualizaciones.",
        },
      ],
    },
    download: {
      eyebrow: "Disponibilidad",
      title: "Descarga y onboarding",
      lead:
        "Estamos preparando paquetes oficiales. Mientras tanto, utiliza la guía de instalación para trabajar desde el código fuente.",
      primaryCta: "Empaquetado en progreso",
      secondaryCta: "Ver guía de instalación",
      note:
        "¿Quieres enterarte cuando haya binarios? Suscríbete al boletín (próximamente).",
    },
    footer: {
      tagline:
        "Tu copiloto de terminal para operar infraestructuras críticas con seguridad y guía multilingüe.",
      linksTitle: "Explora",
      helpTitle: "Ayuda",
      helpCenter: "Centro de ayuda",
      faq: "FAQ",
      download: "Descarga",
      contactTitle: "Contacto",
      contactBody:
        "Escríbenos a support@almosthuman.systems para evaluar despliegues empresariales o pilotos dedicados.",
      rights: "© 2024 Almost Human Sys Admin. Todos los derechos reservados.",
      privacy: "Política de privacidad",
      terms: "Términos de servicio",
    },
  },
  de: {
    nav: {
      product: "Produkt",
      features: "Funktionen",
      how: "Funktionsweise",
      quickstart: "Schnellstart",
      help: "Hilfe",
      download: "Download",
    },
    hero: {
      badge: "Terminalbasierter KI-Agent",
      title: "Automatisiere Remote-Administration mit Sicherheit",
      subtitle:
        "Almost Human Sys Admin verbindet eine Retro-TUI mit einem intelligenten Agenten, der Anweisungen versteht, SSH/SFTP-Sitzungen wach hält und jede Aktion protokolliert.",
      primaryCta: "Download (bald verfügbar)",
      secondaryCta: "Schnellstart ansehen",
      note:
        "Entwickelt für Operationsteams, die Verlässlichkeit, Nachvollziehbarkeit und Mehrsprachigkeit schätzen – direkt in der Konsole.",
    },
    product: {
      eyebrow: "Überblick",
      title: "Der Begleiter für anspruchsvolle Admins",
      lead:
        "Perfekt für Teams mit sensibler Infrastruktur: persistente Sitzungen, sichere Remote-Tools und lokalisierte Assistenz auf Englisch, Spanisch und Deutsch.",
      bullets: [
        "Persistente SSH- und SFTP-Kanäle, gesteuert von einem Agenten, der natürliche Sprache versteht.",
        "Konfigurierbare Provider: LM Studio, Cerebras, Amazon Bedrock, OpenAI sowie Ollama-kompatible Laufzeiten.",
        "Audit-freundliches Design mit lokalisierten Prompts, Retro-Optik und strukturiertem Logging für vollständige Nachverfolgung.",
      ],
    },
    features: {
      eyebrow: "Funktionen",
      title: "Produkt-Highlights",
      lead:
        "Jedes Modul ist darauf ausgelegt, operatives Vertrauen zu schaffen – von der sicheren Verbindung bis zur Dokumentation.",
      cards: [
        {
          icon: "🛰️",
          title: "Agentische SSH-Orchestrierung",
          body:
            "Halte pro Host eine SSH/SFTP-Sitzung offen, nutze sie für Befehle oder Transfers und steuere Timeouts über Berechtigungen.",
        },
        {
          icon: "🌐",
          title: "Mehrsprachige Oberfläche",
          body:
            "Wechsle nahtlos zwischen Englisch, Spanisch und Deutsch. Texte liegen in JSON-Dateien und werden beim Start geladen.",
        },
        {
          icon: "🧩",
          title: "Custom-Provider-SDK",
          body:
            "Binde LM Studio, Cerebras oder interne LLMs über Strands-SDK-Provider ein – inklusive Streaming und Tool-Unterstützung.",
        },
        {
          icon: "🛡️",
          title: "Betriebliche Sicherheit",
          body:
            "Timeout-sensitive Remote-Kommandos, Freigaberegeln und das Datum/Uhrzeit-Tool halten den Agenten geerdet.",
        },
      ],
    },
    how: {
      eyebrow: "Ablauf",
      title: "So funktioniert es",
      lead:
        "Vom initialen Setup bis zur laufenden Automatisierung bleibt der Prozess transparent und nachvollziehbar.",
      steps: [
        {
          title: "1. Agent konfigurieren",
          body:
            "Lade `conf/agent.conf`, wähle deinen Provider und exportiere notwendige API-Schlüssel. Platzhalter und Secrets werden zur Laufzeit aufgelöst.",
        },
        {
          title: "2. Einmal verbinden",
          body:
            "Mit `/connect` richtest du SSH/SFTP ein. Passwort, Schlüssel und eigene Ports sind unterstützt.",
        },
        {
          title: "3. Absicht beschreiben",
          body:
            "Formuliere dein Ziel oder nutze `/status`, um Provider, Modell und Streaming-Einstellungen zu prüfen.",
        },
        {
          title: "4. Ausführen & prüfen",
          body:
            "Der Agent ruft `remote_ssh_command` oder `remote_sftp_transfer` auf. Alle Aktionen werden mit Zeitstempeln protokolliert.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Schnellstart",
      title: "In wenigen Minuten startklar",
      lead:
        "Richte die Umgebung ein, wähle deinen Provider und arbeite gemeinsam mit dem terminalnativen Assistenten.",
      steps: [
        {
          title: "Umgebung vorbereiten",
          body:
            "Erstelle ein Virtualenv (`python -m venv .venv`) und installiere Abhängigkeiten über `make install`.",
        },
        {
          title: "Konfiguration prüfen",
          body:
            "Kopiere `conf/agent.conf.example` nach `conf/agent.conf`, passe Provider, Tokens und Berechtigungen an. Übersetzungen liegen in `conf/locales/`.",
        },
        {
          title: "TUI starten",
          body:
            "Starte `make run` (oder `python -m smart_ai_sys_admin`). Begrüßungsbildschirm, Eingabe und Footer erscheinen sofort.",
        },
        {
          title: "Verbinden & entdecken",
          body:
            "Mit `/connect bastion admin-key` öffnest du die Sitzung, `/status` zeigt Agentendetails und `/help` listet alle Befehle.",
        },
      ],
      note:
        "Tipp: Vor Commits immer `make format` und `make lint` ausführen, um Qualität sicherzustellen.",
    },
    help: {
      eyebrow: "Hilfe",
      title: "Help Center",
      lead:
        "Ressourcen, um den Assistenten zu meistern, Probleme zu lösen und Provider anzupassen.",
      panels: [
        {
          title: "Wichtige Befehle",
          body:
            "Slash-Commands steuern die Interaktion. Alle bieten lokalisierte Aliasse und Markdown-Ausgabe.",
          bullets: [
            "`/connect` · öffnet SSH/SFTP-Sitzungen mit Passwort oder Schlüssel.",
            "`/disconnect` · beendet die aktuelle Sitzung sauber.",
            "`/status` · zeigt Provider, Modell, Streaming-Flag, Konfigurationspfad und SSH-Status.",
            "`/help` · listet alle verfügbaren Befehle inklusive Plugins.",
          ],
        },
        {
          title: "Dokumentation",
          body:
            "Guides auf Englisch, Spanisch und Deutsch. Konfigurationswerte finden sich in `conf/app_config.json` und referenzieren die Locales.",
          bullets: [
            "User Guides: `docs/user_guide_en.md`, `docs/user_guide_es.md`, `docs/user_guide_de.md`.",
            "Custom Provider Leitfaden: `docs/custom_model_providers_es.md` plus Strands-Hinweise.",
            "Agent-Prompts: optimiere `system_prompts/` für deine Richtlinien.",
          ],
        },
        {
          title: "Fehlerbehebung",
          body:
            "Sieh in `logs/` nach detaillierten Protokollen. Verbindungen, Tools und MCP-Events laufen auf DEBUG.",
          bullets: [
            "Stelle sicher, dass dein Terminal 256 Farben unterstützt (`xterm-256color`).",
            "Exportiere Credentials vor dem Start (z. B. `CEREBRAS_API_KEY`).",
            "Für lange Befehle den Agenten um ein höheres `timeout_seconds` bitten.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Häufige Fragen",
      lead:
        "Antworten auf typische Fragen zur Integration und täglichen Nutzung.",
      items: [
        {
          question: "Führt der Agent Befehle autonom aus?",
          answer:
            "Er nutzt die von dir geöffnete SSH-Sitzung und respektiert Berechtigungen. Bestätigungen oder längere Timeouts lassen sich konfigurieren.",
        },
        {
          question: "Kann ich andere LLM-Provider anbinden?",
          answer:
            "Ja. Erweitere das Custom-Provider-Gerüst unter `smart_ai_sys_admin/agent/providers/` und registriere es in `conf/agent.conf`.",
        },
        {
          question: "Wie funktioniert die Lokalisierung?",
          answer:
            "Alle Texte liegen in `conf/locales/<lang>/strings.json`. `conf/app_config.json` referenziert sie über Platzhalter.",
        },
        {
          question: "Gibt es ein grafisches Dashboard?",
          answer:
            "Der Fokus liegt bewusst auf der Konsole. Plugins können dennoch Markdown mit Diagrammen erzeugen, falls benötigt.",
        },
      ],
    },
    download: {
      eyebrow: "Verfügbarkeit",
      title: "Download & Onboarding",
      lead:
        "Offizielle Pakete sind in Vorbereitung. Nutze bis dahin den Installationsleitfaden, um direkt mit dem Code zu arbeiten.",
      primaryCta: "Packaging in Arbeit",
      secondaryCta: "Installationsleitfaden lesen",
      note:
        "Interesse an frühen Binaries? Melde dich für den Newsletter an (bald verfügbar).",
    },
    footer: {
      tagline:
        "Dein Terminal-Co-Pilot für kritische Infrastruktur – sicher und mehrsprachig.",
      linksTitle: "Entdecken",
      helpTitle: "Hilfe",
      helpCenter: "Help Center",
      faq: "FAQ",
      download: "Download",
      contactTitle: "Kontakt",
      contactBody:
        "Schreib an support@almosthuman.systems, um Enterprise-Einsätze oder Pilotprojekte zu besprechen.",
      rights: "© 2024 Almost Human Sys Admin. Alle Rechte vorbehalten.",
      privacy: "Datenschutz",
      terms: "Nutzungsbedingungen",
    },
  },
};
