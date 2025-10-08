window.TRANSLATIONS = {
  en: {
    nav: {
      product: "Product",
      features: "Features",
      gallery: "Screenshots",
      how: "How it works",
      quickstart: "Quick start",
      docs: "Documentation",
      help: "Help",
      download: "Download",
    },
    hero: {
      badge: "Conversational ops assistant",
      title: "Manage remote servers through natural language",
      subtitle:
        "Shell Sentinel turns infrastructure management into a dialogue—pairing persistent SSH/SFTP sessions with an LLM that understands your intent and shares operational context.",
      primaryCta: "Download now",
      secondaryCta: "Explore quick start",
      note:
        "Bring human dialogue to infrastructure work while keeping tight control, observability and multilingual guidance.",
      openLightbox: "Open full-size screenshot",
    },
    product: {
      eyebrow: "Overview",
      title: "Human-centric operations, AI flexibility",
      lead:
        "Delivers the familiarity of collaborating with an experienced SRE while leveraging AI to adapt, explain and execute across languages.",
      bullets: [
        "Express goals in natural language; the assistant translates them into safe SSH/SFTP actions you can review.",
        "Embedded knowledge base surfaces internal guides, best practices and context-sensitive hints in English, Spanish and German.",
        "Modular LLM providers and plugin-ready architecture extend commands, dashboards and automations without touching the core.",
      ],
    },
    features: {
      eyebrow: "Capabilities",
      title: "What makes it different",
      lead:
        "Human-friendly conversations, machine precision and extensible tooling—packaged in a retro terminal experience.",
      cards: [
        {
          icon: "🗣️",
          title: "Conversational command routing",
          body:
            "Describe desired outcomes and let the assistant sequence commands, validate parameters and request confirmation when needed.",
        },
        {
          icon: "📚",
          title: "Context-rich knowledge",
          body:
            "Built-in guidance connects to manuals and localized best practices so answers stay actionable and explainable.",
        },
        {
          icon: "🔄",
          title: "Extensible providers & plugins",
          body:
            "Swap LLM backends or ship plugins that add commands, dashboards or MCP bridges—all without modifying the TUI core.",
        },
        {
          icon: "🛡️",
          title: "Human-centered safety",
          body:
            "Permission prompts, timeout awareness and the local datetime tool keep the conversation grounded before executing remotely.",
        },
      ],
    },
    gallery: {
      eyebrow: "In action",
      title: "Shell Sentinel in the terminal",
      lead:
        "Discover the retro TUI, guided plans and audit-ready summaries the assistant produces.",
      items: [
        {
          alt: "Shell Sentinel command palette highlighting slash commands and plugins",
          caption: "Command palette mixing built-in actions with plugin shortcuts.",
          src: "assets/img/shell-sentinel-command-palette.png",
        },
        {
          alt: "Shell Sentinel displaying a guided remediation plan",
          caption: "Remediation plan with confirmation checkpoints before execution.",
          src: "assets/img/shell-sentinel-plan-overview.png",
        },
        {
          alt: "Shell Sentinel plugin inspector listing registered extensions",
          caption: "Plugin inspector showing localisation and suggestions per command.",
          src: "assets/img/shell-sentinel-plugin-inspector.png",
        },
        {
          alt: "Shell Sentinel session summary consolidating recent actions",
          caption: "Session summary delivering audit-ready context for operations teams.",
          src: "assets/img/shell-sentinel-session-summary.png",
        },
      ],
    },
    how: {
      eyebrow: "Workflow",
      title: "How it works",
      lead:
        "From the first SSH handshake to continuous optimization, the assistant keeps you in the loop with conversational context.",
      steps: [
        {
          title: "1. Provision the copilot",
          body:
            "Copy `conf/agent.conf`, choose your provider, connect internal knowledge sources or MCP tools and export required credentials.",
        },
        {
          title: "2. Open a trusted session",
          body:
            "Run `/connect` to establish a persistent SSH/SFTP channel. Keys, passwords and custom ports are supported out of the box.",
        },
        {
          title: "3. Describe what you need",
          body:
            "Speak in any supported language. The assistant clarifies ambiguous steps, suggests commands and confirms before execution.",
        },
        {
          title: "4. Review, learn and iterate",
          body:
            "Responses arrive in Markdown with logs and context links. Refine prompts, capture learnings and keep the dialogue active.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Kick-off",
      title: "Quick start in minutes",
      lead:
        "Get the environment ready, enable your preferred knowledge sources and start managing servers through conversation.",
      steps: [
        {
          title: "Set up the workspace",
          body:
            "Create a virtual environment (`python -m venv .venv`), activate it and install dependencies with `make install`.",
        },
        {
          title: "Tailor the configuration",
          body:
            "Copy `conf/agent.conf.example` to `conf/agent.conf`, choose the provider stack, enable tools and align locales in `conf/locales/`.",
        },
        {
          title: "Launch the assistant",
          body:
            "Run `make run` to open the TUI, display the welcome screen and load the footer with current provider and model details.",
        },
        {
          title: "Start the dialogue",
          body:
            "Use `/connect` to open the session, ask in natural language (e.g. “Check disk space on /var”) and iterate with `/status` or `/help`.",
        },
      ],
      note:
        "Before committing changes, run `make format` and `make lint` to keep the repo clean.",
    },
    docs: {
      eyebrow: "Manuals",
      title: "Product manuals & handbooks",
      lead:
        "Dive into the living documentation: user guides, provider cookbooks, contributor handbooks and plugin development guides curated for each language.",
      cards: [
        {
          title: "User Guide",
          summary:
            "Install Shell Sentinel, configure locales, explore the interface and master conversational workflows.",
          href: "manuals/user-guide-en.html",
          cta: "Read online",
        },
        {
          title: "Plugin development",
          summary:
            "Step-by-step guide to build, localise and distribute plugins that extend Shell Sentinel.",
          href: "manuals/plugin-development-en.html",
          cta: "Read online",
        },
        {
          title: "Product overview",
          summary:
            "Architecture, technology stack and operational responsibilities behind Shell Sentinel.",
          href: "manuals/project-overview-en.html",
          cta: "Read online",
        },
      ],
    },
    help: {
      eyebrow: "Support",
      title: "Help & knowledge base",
      lead:
        "Resources to turn conversations into reliable actions, maintain shared knowledge and troubleshoot quickly.",
      panels: [
        {
          title: "Conversational commands",
          body:
            "Slash commands remain the backbone for precise control while the assistant keeps the dialogue flowing.",
          bullets: [
            "`/connect` · Establish persistent SSH/SFTP sessions with key or password auth.",
            "`/disconnect` · Close the active session safely before leaving the TUI.",
            "`/status` · Inspect provider, model, streaming flag, config path and SSH state at any time.",
            "`/help` · List commands and plugin extensions with localized descriptions.",
          ],
        },
        {
          title: "Knowledge & documentation",
          body:
            "Keep the assistant aligned with your organization by updating the multilingual documentation set.",
          bullets: [
            "Multi-language user guides covering onboarding, day-to-day operations and FAQs.",
            "Plugin documentation that explains how to extend commands, dashboards and integrations.",
            "A system prompt library to fine-tune tone, guardrails and workflow guidance.",
          ],
        },
        {
          title: "Operational best practices",
          body:
            "Stay grounded with logs, locale awareness and timeout controls while collaborating in natural language.",
          bullets: [
            "Confirm your terminal supports 256 colours (`xterm-256color`).",
            "Export credentials (e.g. `CEREBRAS_API_KEY`) before launching the TUI.",
            "Request higher `timeout_seconds` when long-running tasks are expected.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Frequently asked questions",
      lead:
        "Clarify how the conversational assistant fits into your operational workflows.",
      items: [
        {
          question: "How is this different from traditional automation?",
          answer:
            "Instead of scripting every step, you describe intent. The assistant reasons with you, shows suggested commands and seeks approval before execution.",
        },
        {
          question: "How does the assistant stay grounded in reality?",
          answer:
            "It reuses your live SSH session, consults the local datetime tool and logs every action so you can verify outputs instantly.",
        },
        {
          question: "Can it incorporate my own knowledge base?",
          answer:
            "Yes. Keep documentation in your preferred knowledge base, expose it via MCP or plugins, and reference it during conversations for guided responses.",
        },
        {
          question: "Which languages can I speak to it?",
          answer:
            "The TUI ships with English, Spanish and German locales. Add more by extending `conf/locales/` and updating your configuration.",
        },
      ],
    },
    download: {
      eyebrow: "Availability",
      title: "Download & onboarding",
      lead:
        "Stable builds are published through GitHub Releases. Grab version 1.0.0 and keep the quick start guide close when setting up.",
      primaryCta: "Download Shell Sentinel 1.0",
      secondaryCta: "Follow quick start guide",
      note:
        "Install from source by creating a virtual environment, running make install and launching make run.",
      license:
        "Shell Sentinel ships under a source-available licence: non-commercial use only, with modifications and derivative works prohibited unless you obtain written permission.",
    },
    footer: {
      tagline:
        "Your conversational copilot for managing critical infrastructure with trust and transparency.",
      linksTitle: "Explore",
      helpTitle: "Help",
      helpCenter: "Help center",
      faq: "FAQ",
      download: "Download",
      contactTitle: "Stay in touch",
      contactBody:
        "Reach us at support@shellsentinel.net to discuss enterprise integrations or pilot programs.",
      rights: "© 2025 Shell Sentinel. All rights reserved.",
      privacy: "Privacy policy",
      terms: "Terms of service",
    },
  },
  es: {
    nav: {
      product: "Producto",
      features: "Funciones",
      gallery: "Capturas",
      how: "Cómo funciona",
      quickstart: "Inicio rápido",
      docs: "Documentación",
      help: "Ayuda",
      download: "Descarga",
    },
    hero: {
      badge: "Asistente conversacional de operaciones",
      title: "Gestiona servidores remotos con lenguaje natural",
      subtitle:
        "Shell Sentinel convierte la administración de infraestructuras en una conversación: combina sesiones SSH/SFTP persistentes con un LLM que entiende tu intención y comparte contexto operativo.",
      primaryCta: "Descargar ahora",
      secondaryCta: "Explorar guía rápida",
      note:
        "Lleva el lenguaje humano al trabajo de infraestructura manteniendo el control, la observabilidad y la guía multilingüe.",
      openLightbox: "Abrir captura a tamaño completo",
    },
    product: {
      eyebrow: "Resumen",
      title: "Operaciones centradas en personas con flexibilidad IA",
      lead:
        "Reproduce la familiaridad de colaborar con un ser humano y se apoya en la IA para adaptarse, explicar y ejecutar en varios idiomas.",
      bullets: [
        "Expresa objetivos en lenguaje natural; el asistente los traduce en acciones SSH/SFTP seguras que puedes revisar.",
        "Una base de conocimiento integrada destaca guías internas, buenas prácticas y pistas contextuales en inglés, español y alemán.",
        "Proveedores LLM modulares y una arquitectura preparada para plugins extienden comandos, paneles y automatizaciones sin tocar el core.",
      ],
    },
    features: {
      eyebrow: "Capacidades",
      title: "Qué lo hace diferente",
      lead:
        "Conversaciones humanas, precisión de máquina y herramientas extensibles dentro de una experiencia retro en terminal.",
      cards: [
        {
          icon: "🗣️",
          title: "Enrutamiento conversacional",
          body:
            "Describe resultados deseados y deja que el asistente secuencie comandos, valide parámetros y pida confirmación cuando sea necesario.",
        },
        {
          icon: "📚",
          title: "Conocimiento contextual",
          body:
            "La guía integrada enlaza con manuales y mejores prácticas localizadas para respuestas accionables y explicables.",
        },
        {
          icon: "🔄",
          title: "Proveedores y plugins extensibles",
          body:
            "Cambia de backend LLM o crea plugins que añadan comandos, paneles o puentes MCP sin modificar el núcleo de la TUI.",
        },
        {
          icon: "🛡️",
          title: "Seguridad centrada en humanos",
          body:
            "Solicitudes de permiso, control de timeouts y la herramienta de fecha local mantienen la conversación anclada antes de ejecutar remotamente.",
        },
      ],
    },
    gallery: {
      eyebrow: "En acción",
      title: "Shell Sentinel en la terminal",
      lead:
        "Conoce la TUI retro, los planes guiados y los resúmenes auditables que entrega el asistente.",
      items: [
        {
          alt: "Paleta de comandos de Shell Sentinel con accesos directos de plugins",
          caption: "Paleta de comandos que combina acciones nativas con atajos de plugins.",
          src: "assets/img/shell-sentinel-command-palette.png",
        },
        {
          alt: "Shell Sentinel mostrando un plan guiado de remediación",
          caption: "Plan de remediación con puntos de confirmación antes de ejecutar cada paso.",
          src: "assets/img/shell-sentinel-plan-overview.png",
        },
        {
          alt: "Inspector de plugins de Shell Sentinel con extensiones registradas",
          caption: "Inspector de plugins con traducciones y sugerencias según cada comando.",
          src: "assets/img/shell-sentinel-plugin-inspector.png",
        },
        {
          alt: "Resumen de sesión de Shell Sentinel consolidando acciones recientes",
          caption: "Resumen de sesión con contexto listo para auditorías del equipo de operaciones.",
          src: "assets/img/shell-sentinel-session-summary.png",
        },
      ],
    },
    how: {
      eyebrow: "Flujo",
      title: "Cómo funciona",
      lead:
        "Desde el primer handshake SSH hasta la optimización continua, el asistente te mantiene al tanto con contexto conversacional.",
      steps: [
        {
          title: "1. Prepara el copiloto",
          body:
            "Copia `conf/agent.conf`, elige proveedor, conecta fuentes de conocimiento internas o herramientas MCP y exporta las credenciales necesarias.",
        },
        {
          title: "2. Abre una sesión confiable",
          body:
            "Ejecuta `/connect` para establecer un canal SSH/SFTP persistente. Claves, contraseñas y puertos personalizados están soportados.",
        },
        {
          title: "3. Explica lo que necesitas",
          body:
            "Habla en cualquiera de los idiomas soportados. El asistente aclara pasos ambiguos, sugiere comandos y confirma antes de ejecutar.",
        },
        {
          title: "4. Revisa, aprende e itera",
          body:
            "Las respuestas llegan en Markdown con logs y enlaces. Refina prompts, captura aprendizajes y mantén viva la conversación.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Puesta en marcha",
      title: "Inicio rápido en minutos",
      lead:
        "Prepara el entorno, activa tus fuentes de conocimiento y empieza a gestionar servidores mediante conversación.",
      steps: [
        {
          title: "Configura el workspace",
          body:
            "Crea un entorno virtual (`python -m venv .venv`), actívalo e instala dependencias con `make install`.",
        },
        {
          title: "Ajusta la configuración",
          body:
            "Copia `conf/agent.conf.example` a `conf/agent.conf`, elige proveedores, activa herramientas y alinea los locales en `conf/locales/`.",
        },
        {
          title: "Inicia el asistente",
          body:
            "Ejecuta `make run` para abrir la TUI, mostrar la bienvenida y cargar el footer con proveedor y modelo actuales.",
        },
        {
          title: "Empieza la conversación",
          body:
            "Usa `/connect` para abrir la sesión, pide en lenguaje natural (ej. “Revisa el espacio en /var”) e itera con `/status` o `/help`.",
        },
      ],
      note:
        "Antes de subir cambios, ejecuta `make format` y `make lint` para mantener el repositorio limpio.",
    },
    docs: {
      eyebrow: "Manuales",
      title: "Manuales y cuadernos de referencia",
      lead:
        "Consulta la documentación viva: guías de usuario, recetas de proveedores, manuales de contribución y guías de desarrollo de plugins.",
      cards: [
        {
          title: "Guía de usuario",
          summary:
            "Instala la aplicación, ajusta idiomas, conoce los comandos clave y colabora con el asistente en español.",
          href: "manuals/user-guide-es.html",
          cta: "Leer en línea",
        },
        {
          title: "Desarrollo de plugins",
          summary:
            "Guía práctica para crear, traducir y distribuir plugins personalizados dentro de Shell Sentinel.",
          href: "manuals/plugin-development-es.html",
          cta: "Leer en línea",
        },
        {
          title: "Proveedores personalizados",
          summary:
            "Checklist para integrar proveedores LLM personalizados en el ecosistema de Shell Sentinel.",
          href: "manuals/custom-providers-es.html",
          cta: "Leer en línea",
        },
        {
          title: "Manual de colaboración",
          summary:
            "Políticas internas sobre documentación multilingüe, publicación web y control de calidad del producto.",
          href: "manuals/contributor-handbook-es.html",
          cta: "Leer en línea",
        },
      ],
    },
    help: {
      eyebrow: "Soporte",
      title: "Centro de ayuda",
      lead:
        "Recursos para convertir conversaciones en acciones fiables, mantener el conocimiento compartido y resolver incidencias rápido.",
      panels: [
        {
          title: "Comandos conversacionales",
          body:
            "Los comandos slash siguen ofreciendo control preciso mientras el asistente sostiene el diálogo.",
          bullets: [
            "`/connect` · Abre sesiones SSH/SFTP persistentes con clave o contraseña.",
            "`/disconnect` · Cierra la sesión activa de forma segura antes de salir.",
            "`/status` · Consulta proveedor, modelo, streaming, ruta de configuración y estado SSH.",
            "`/help` · Lista comandos y extensiones de plugins con descripciones localizadas.",
          ],
        },
        {
          title: "Conocimiento y documentación",
          body:
            "Mantén alineado al asistente actualizando el set de documentación multilingüe.",
          bullets: [
            "Guías de usuario disponibles en EN/ES/DE con onboarding, flujos y FAQ actualizadas.",
            "La documentación de plugins explica cómo extender comandos, paneles y nuevas integraciones.",
            "La biblioteca de system prompts permite ajustar tono, medidas de seguridad y pasos operativos.",
          ],
        },
        {
          title: "Buenas prácticas operativas",
          body:
            "Mantén la sesión anclada con logs, locales y control de timeouts mientras colaboras en lenguaje natural.",
          bullets: [
            "Confirma que tu terminal soporta 256 colores (`xterm-256color`).",
            "Exporta credenciales (p. ej. `CEREBRAS_API_KEY`) antes de lanzar la TUI.",
            "Solicita un `timeout_seconds` mayor cuando preveas tareas largas.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Preguntas frecuentes",
      lead:
        "Aclara cómo encaja el asistente conversacional en tus flujos operativos.",
      items: [
        {
          question: "¿En qué se diferencia de la automatización tradicional?",
          answer:
            "En lugar de guiones rígidos, describes tu intención. El asistente razona contigo, muestra comandos sugeridos y pide aprobación antes de ejecutar.",
        },
        {
          question: "¿Cómo se mantiene alineado con la realidad?",
          answer:
            "Reutiliza tu sesión SSH activa, consulta la herramienta de fecha local y registra cada acción para que verifiques resultados al instante.",
        },
        {
          question: "¿Puede usar mi propia base de conocimiento?",
          answer:
            "Sí. Mantén la documentación en tu base de conocimiento preferida, exponla vía MCP o plugins y utilízala en la conversación para respuestas guiadas.",
        },
        {
          question: "¿En qué idiomas puedo hablarle?",
          answer:
            "La TUI incluye inglés, español y alemán. Añade más extendiendo `conf/locales/` y actualizando la configuración.",
        },
      ],
    },
    download: {
      eyebrow: "Disponibilidad",
      title: "Descarga y onboarding",
      lead:
        "La versión estable 1.0.0 está disponible en GitHub Releases. Descárgala y ten la guía de inicio rápido a mano durante la instalación.",
      primaryCta: "Descargar Shell Sentinel 1.0",
      secondaryCta: "Seguir guía de inicio rápido",
      note:
        "Instala desde el código creando un entorno virtual, ejecutando make install y arrancando con make run.",
      license:
        "Shell Sentinel se distribuye con una licencia de código disponible: solo se permite uso no comercial y queda prohibido modificar o crear derivados sin permiso escrito.",
    },
    footer: {
      tagline:
        "Tu copiloto conversacional para gestionar infraestructuras críticas con confianza y transparencia.",
      linksTitle: "Explora",
      helpTitle: "Ayuda",
      helpCenter: "Centro de ayuda",
      faq: "FAQ",
      download: "Descarga",
      contactTitle: "Contacto",
      contactBody:
        "Escríbenos a support@shellsentinel.net para valorar integraciones empresariales o pilotos.",
      rights: "© 2025 Shell Sentinel. Todos los derechos reservados.",
      privacy: "Política de privacidad",
      terms: "Términos de servicio",
    },
  },
  de: {
    nav: {
      product: "Produkt",
      features: "Funktionen",
      gallery: "Screenshots",
      how: "Funktionsweise",
      quickstart: "Schnellstart",
      docs: "Dokumentation",
      help: "Hilfe",
      download: "Download",
    },
    hero: {
      badge: "Konversationeller Ops-Assistent",
      title: "Verwalte entfernte Server mit natürlicher Sprache",
      subtitle:
        "Shell Sentinel verwandelt Infrastrukturverwaltung in einen Dialog: persistente SSH/SFTP-Sitzungen treffen auf ein LLM, das deine Absicht versteht und Kontext teilt.",
      primaryCta: "Jetzt herunterladen",
      secondaryCta: "Schnellstart ansehen",
      note:
        "Bringe menschliche Sprache in die Infrastrukturarbeit und behalte gleichzeitig Kontrolle, Observability und Mehrsprachigkeit.",
      openLightbox: "Screenshot in voller Größe öffnen",
    },
    product: {
      eyebrow: "Überblick",
      title: "Menschenzentrierte Ops mit KI-Flexibilität",
      lead:
        "Das Erlebnis fühlt sich an wie die Zusammenarbeit mit einem erfahrenen SRE und nutzt gleichzeitig KI, um sich anzupassen, zu erklären und in mehreren Sprachen auszuführen.",
      bullets: [
        "Formuliere Ziele in natürlicher Sprache; der Assistent übersetzt sie in überprüfbare, sichere SSH/SFTP-Aktionen.",
        "Eine integrierte Wissensbasis liefert interne Leitfäden, Best Practices und kontextbezogene Hinweise auf Englisch, Spanisch und Deutsch.",
        "Modulare LLM-Provider und eine plugin-fähige Architektur erweitern Befehle, Dashboards und Automatisierungen ohne Core-Änderungen.",
      ],
    },
    features: {
      eyebrow: "Funktionen",
      title: "Warum es heraussticht",
      lead:
        "Menschliche Gespräche, maschinelle Präzision und erweiterbare Tools – alles in einer Retro-Terminal-Erfahrung.",
      cards: [
        {
          icon: "🗣️",
          title: "Konversationelles Routing",
          body:
            "Beschreibe gewünschte Ergebnisse; der Assistent reiht Befehle, prüft Parameter und holt Bestätigungen ein.",
        },
        {
          icon: "📚",
          title: "Kontextreiches Wissen",
          body:
            "Integrierte Hinweise verweisen auf Guides und lokalisierte Best Practices, damit Antworten nachvollziehbar bleiben.",
        },
        {
          icon: "🔄",
          title: "Erweiterbare Provider & Plugins",
          body:
            "Wechsle LLM-Backends oder entwickle Plugins für zusätzliche Befehle, Dashboards oder MCP-Brücken – ganz ohne Kernänderungen.",
        },
        {
          icon: "🛡️",
          title: "Menschorientierte Sicherheit",
          body:
            "Freigabe-Dialoge, Timeout-Achtsamkeit und das lokale Datums-Tool sorgen für Bodenhaftung vor Remote-Befehlen.",
        },
      ],
    },
    gallery: {
      eyebrow: "Im Einsatz",
      title: "Shell Sentinel im Terminal",
      lead:
        "Ein Blick auf die Retro-TUI, geführte Pläne und revisionssichere Zusammenfassungen des Assistenten.",
      items: [
        {
          alt: "Shell-Sentinel-Befehlsübersicht mit Plugin-Kürzeln",
          caption: "Befehls-Palette, die Kernbefehle und Plugin-Verknüpfungen kombiniert.",
          src: "assets/img/shell-sentinel-command-palette.png",
        },
        {
          alt: "Shell Sentinel zeigt einen geführten Remediationsplan",
          caption: "Geführter Plan mit Freigabe-Punkten vor jedem ausgeführten Schritt.",
          src: "assets/img/shell-sentinel-plan-overview.png",
        },
        {
          alt: "Shell Sentinel Plugin-Inspector mit registrierten Erweiterungen",
          caption: "Plugin-Inspector mit Übersetzungen und Vorschlägen pro Kommando.",
          src: "assets/img/shell-sentinel-plugin-inspector.png",
        },
        {
          alt: "Shell Sentinel Session-Report mit den letzten Aktionen",
          caption: "Sessionszusammenfassung mit auditfähigem Kontext für das Ops-Team.",
          src: "assets/img/shell-sentinel-session-summary.png",
        },
      ],
    },
    how: {
      eyebrow: "Ablauf",
      title: "So funktioniert es",
      lead:
        "Vom ersten SSH-Handshake bis zur kontinuierlichen Optimierung hält dich der Assistent mit konversationellem Kontext auf dem Laufenden.",
      steps: [
        {
          title: "1. Copilot vorbereiten",
          body:
            "Kopiere `conf/agent.conf`, wähle deinen Provider, binde interne Wissensquellen oder MCP-Tools ein und exportiere benötigte Credentials.",
        },
        {
          title: "2. Vertrauenswürdige Session öffnen",
          body:
            "Starte `/connect`, um einen persistenten SSH/SFTP-Kanal aufzubauen. Schlüssel, Passwörter und eigene Ports sind möglich.",
        },
        {
          title: "3. Bedarf formulieren",
          body:
            "Sprich in einer unterstützten Sprache. Der Assistent klärt Unklarheiten, schlägt Befehle vor und bestätigt vor der Ausführung.",
        },
        {
          title: "4. Prüfen, lernen, iterieren",
          body:
            "Antworten erscheinen als Markdown mit Logs und Links. Verfeinere Prompts, halte Erkenntnisse fest und führe den Dialog fort.",
        },
      ],
    },
    quickstart: {
      eyebrow: "Schnellstart",
      title: "In wenigen Minuten loslegen",
      lead:
        "Bereite die Umgebung vor, aktiviere Wissensquellen und steuere Server per Gespräch.",
      steps: [
        {
          title: "Workspace einrichten",
          body:
            "Erstelle ein Virtualenv (`python -m venv .venv`), aktiviere es und installiere Abhängigkeiten mit `make install`.",
        },
        {
          title: "Konfiguration verfeinern",
          body:
            "Kopiere `conf/agent.conf.example` nach `conf/agent.conf`, wähle Provider, aktiviere Tools und passe Locales in `conf/locales/` an.",
        },
        {
          title: "Assistent starten",
          body:
            "Starte `make run`, um die TUI zu öffnen, den Welcome-Screen zu sehen und den Footer mit Provider-Details zu laden.",
        },
        {
          title: "Dialog beginnen",
          body:
            "Nutze `/connect`, um die Session zu öffnen, frage in natürlicher Sprache (z. B. „Prüfe den freien Speicher auf /var“) und nutze `/status` oder `/help` zum Nachfassen.",
        },
      ],
      note:
        "Vor Commits `make format` und `make lint` ausführen, damit das Repository sauber bleibt.",
    },
    docs: {
      eyebrow: "Handbücher",
      title: "Produkt-Handbücher & Leitfäden",
      lead:
        "Greife auf die lebende Dokumentation zu – Benutzerhandbücher, Provider-Guides, Beitragsrichtlinien und Plugin-Entwicklungsleitfäden.",
      cards: [
        {
          title: "Benutzerhandbuch",
          summary:
            "Richte die Umgebung ein, entdecke die TUI und nutze den Assistenten auf Deutsch im operativen Alltag.",
          href: "manuals/user-guide-de.html",
          cta: "Online lesen",
        },
        {
          title: "Plugin-Entwicklung",
          summary:
            "Schritt-für-Schritt-Anleitung zur Erstellung, Lokalisierung und Verteilung eigener Plugins.",
          href: "manuals/plugin-development-de.html",
          cta: "Online lesen",
        },
      ],
    },
    help: {
      eyebrow: "Hilfe",
      title: "Help Center",
      lead:
        "Ressourcen, um Gespräche in verlässliche Aktionen zu überführen, Wissen zu pflegen und Probleme schnell zu lösen.",
      panels: [
        {
          title: "Konversationelle Befehle",
          body:
            "Slash-Commands liefern präzise Kontrolle, während der Assistent den Dialog führt.",
          bullets: [
            "`/connect` · Öffnet persistente SSH/SFTP-Sitzungen mit Schlüssel oder Passwort.",
            "`/disconnect` · Beendet die aktive Session sicher.",
            "`/status` · Zeigt Provider, Modell, Streaming-Flag, Konfigurationspfad und SSH-Status.",
            "`/help` · Listet alle Befehle und Plugin-Erweiterungen mit lokalisierten Beschreibungen.",
          ],
        },
        {
          title: "Wissen & Dokumentation",
          body:
            "Halte den Assistenten synchron, indem du die mehrsprachige Dokumentation aktuell hältst.",
          bullets: [
            "Benutzerhandbücher in EN/ES/DE mit Onboarding, Betriebsabläufen und FAQ.",
            "Plugin-Dokumentation erläutert, wie sich Befehle, Dashboards und Integrationen erweitern lassen.",
            "Die System-Prompt-Bibliothek steuert Tonalität, Sicherheitsmaßnahmen und Workflows.",
          ],
        },
        {
          title: "Betriebliche Best Practices",
          body:
            "Arbeite gesichert mit Logs, Locale-Bewusstsein und Timeout-Kontrolle, während du dich auf natürliche Sprache stützt.",
          bullets: [
            "Stelle sicher, dass dein Terminal 256 Farben unterstützt (`xterm-256color`).",
            "Exportiere Credentials (z. B. `CEREBRAS_API_KEY`) vor dem Start der TUI.",
            "Bitte bei langen Tasks um ein höheres `timeout_seconds`.",
          ],
        },
      ],
    },
    faq: {
      eyebrow: "FAQ",
      title: "Häufige Fragen",
      lead:
        "So integriert sich der konversationelle Assistent in deine Betriebsabläufe.",
      items: [
        {
          question: "Worin liegt der Unterschied zu klassischer Automatisierung?",
          answer:
            "Anstatt jeden Schritt zu skripten, beschreibst du das Ziel. Der Assistent diskutiert mit dir, zeigt Vorschläge und holt Freigaben ein.",
        },
        {
          question: "Wie bleibt der Assistent realitätsnah?",
          answer:
            "Er nutzt deine laufende SSH-Sitzung, fragt das lokale Datum/Uhrzeit ab und protokolliert jede Aktion zur sofortigen Überprüfung.",
        },
        {
          question: "Kann er meine Wissensbasis einbinden?",
          answer:
            "Ja. Halte die Dokumentation in deiner bevorzugten Wissensbasis bereit, binde sie über MCP oder Plugins ein und referenziere sie im Gespräch für geführte Antworten.",
        },
        {
          question: "Welche Sprachen werden unterstützt?",
          answer:
            "Die TUI enthält Englisch, Spanisch und Deutsch. Weitere Sprachen fügst du über `conf/locales/` hinzu.",
        },
      ],
    },
    download: {
      eyebrow: "Verfügbarkeit",
      title: "Download & Onboarding",
      lead:
        "Der stabile Release 1.0.0 steht über GitHub Releases bereit. Lade ihn herunter und halte den Schnellstart für die Einrichtung bereit.",
      primaryCta: "Shell Sentinel 1.0 herunterladen",
      secondaryCta: "Schnellstart öffnen",
      note:
        "Installation aus dem Quellcode: Virtuelle Umgebung erstellen, make install ausführen und mit make run starten.",
      license:
        "Shell Sentinel steht unter einer Source-Available-Lizenz: ausschließlich nicht-kommerzielle Nutzung; Modifikationen oder Ableitungen sind nur mit schriftlicher Genehmigung erlaubt.",
    },
    footer: {
      tagline:
        "Dein konversationeller Copilot für kritische Infrastruktur mit Vertrauen und Transparenz.",
      linksTitle: "Entdecken",
      helpTitle: "Hilfe",
      helpCenter: "Help Center",
      faq: "FAQ",
      download: "Download",
      contactTitle: "Kontakt",
      contactBody:
        "Schreibe an support@shellsentinel.net, um Enterprise-Integrationen oder Pilotprojekte zu besprechen.",
      rights: "© 2025 Shell Sentinel. Alle Rechte vorbehalten.",
      privacy: "Datenschutz",
      terms: "Nutzungsbedingungen",
    },
  },
};
