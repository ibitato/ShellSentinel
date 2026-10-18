"""Inicialización y ejecución del agente Strands."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from strands.agent.agent_result import AgentResult

from ..connection import SSHConnectionManager
from ..localization import _
from .config import (
    AgentConfig,
    AgentConfigError,
    ProviderBaseConfig,
    load_agent_config,
)
from .factory import AgentFactory
from .mcp_manager import MCPManager, MCPServerStatus
from .permissions import ToolPermissionManager
from .tools import remote_ssh_command, resolve_tools


class AgentRuntime:
    """Orquesta la vida del agente Strands dentro de la aplicación TUI."""

    def __init__(
        self,
        connection_manager: SSHConnectionManager,
        logger: logging.Logger | None = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._logger = logger or logging.getLogger("smart_ai_sys_admin.agent.runtime")
        self._config: AgentConfig | None = None
        self._factory: AgentFactory | None = None
        self._mcp_manager: MCPManager | None = None
        self._agent = None
        self._status_message: str | None = None
        self._error_message: str | None = None
        self._ready = False
        self._hide_thinking = False
        self._permission_manager = ToolPermissionManager(logger=self._logger)
        self._last_cache_usage: dict[str, int] | None = None

    @property
    def ready(self) -> bool:
        return self._ready and self._agent is not None

    @property
    def status_message(self) -> str | None:
        return self._status_message

    @property
    def error_message(self) -> str | None:
        return self._error_message

    # ------------------------------------------------------------------
    # Información de soporte para la interfaz
    # ------------------------------------------------------------------

    def agent_summary(self) -> dict[str, Any]:
        """Devuelve un resumen del estado del agente para comandos como `/status`."""

        summary: dict[str, Any] = {
            "ready": self.ready,
            "streaming": False,
            "provider": None,
            "model": None,
            "config_path": None,
            "status": self._status_message,
            "error": self._error_message,
            "mcp_servers": [self._describe_mcp_server(st) for st in self.mcp_statuses],
            "cache_enabled": None,
            "cache_usage": self.last_cache_usage,
        }
        if not self._config:
            return summary

        summary["streaming"] = self._config.options.streaming
        summary["max_turns"] = self._config.options.max_turns
        summary["config_path"] = str(self._config.config_path)
        try:
            provider_cfg = self._config.provider_config()
        except AgentConfigError:
            return summary

        summary["provider"] = self._format_provider_label(provider_cfg)
        summary["model"] = getattr(provider_cfg, "model_id", None)
        if self._factory is not None:
            summary["cache_enabled"] = self._factory.cache_enabled
        return summary

    @property
    def last_cache_usage(self) -> dict[str, int] | None:
        """Uso de caché del último turno: tokens de entrada, leídos y escritos en caché."""

        return dict(self._last_cache_usage) if self._last_cache_usage else None

    @property
    def mcp_statuses(self) -> tuple[MCPServerStatus, ...]:
        """Estado de cada servidor MCP configurado tras el arranque."""

        if not self._mcp_manager:
            return ()
        return self._mcp_manager.statuses

    @staticmethod
    def _describe_mcp_server(status: MCPServerStatus) -> str:
        key = "agent.mcp.status.ready" if status.ready else "agent.mcp.status.failed"
        line = _(
            key,
            id=status.identifier,
            transport=status.transport_type,
            count=status.tool_count,
            message=status.message or "",
        )
        if status.ready and status.message:
            line += f" — {status.message}"
        return line

    def mcp_startup_report(self) -> str | None:
        """Markdown con los servidores MCP que no arrancaron, o ``None`` si todos lo hicieron."""

        statuses = self.mcp_statuses
        failed = [st for st in statuses if not st.ready]
        if not failed:
            return None
        lines = [_("agent.mcp.status.summary_failed", failed=len(failed), total=len(statuses))]
        lines.extend(f"- {self._describe_mcp_server(st)}" for st in failed)
        return "\n".join(lines)

    def provider_footer_summary(self) -> str:
        """Devuelve la etiqueta localizada para mostrar proveedor y modelo activos."""

        if not self._config:
            return ""
        try:
            provider_cfg = self._config.provider_config()
        except AgentConfigError:
            return ""

        model = getattr(provider_cfg, "model_id", None)
        if not model:
            return ""

        provider_label = self._format_provider_label(provider_cfg)
        if not provider_label:
            return ""

        summary = _(
            "connection.status.provider",
            provider=provider_label,
            model=model,
        )
        if summary == "connection.status.provider":
            return f"{provider_label} · {model}"
        return summary

    def initialize(self) -> None:
        try:
            config = load_agent_config()
        except AgentConfigError as exc:
            self._error_message = (
                "⚠️ No se pudo cargar `conf/agent.conf`: "
                f"{exc}. El modo agente permanecerá deshabilitado."
            )
            self._logger.error("Error cargando la configuración del agente: %s", exc)
            return

        self._config = config
        self._factory = AgentFactory(config)
        self._permission_manager.set_logger(self._logger)
        provider_cfg = config.provider_config()
        self._hide_thinking = not provider_cfg.show_thinking

        tool_name = self._factory.remote_command.name
        if tool_name:
            current_name: str | None = None
            if hasattr(remote_ssh_command, "tool_name"):
                try:
                    current_name = remote_ssh_command.tool_name  # type: ignore[attr-defined]
                except Exception:  # pragma: no cover - defensivo
                    current_name = None
            if current_name != tool_name:
                if hasattr(remote_ssh_command, "tool_spec"):
                    try:
                        spec = remote_ssh_command.tool_spec  # type: ignore[attr-defined]
                    except Exception:  # pragma: no cover - defensivo
                        spec = None
                    if isinstance(spec, dict):
                        spec["name"] = tool_name
                if hasattr(remote_ssh_command, "_tool_name"):
                    remote_ssh_command._tool_name = tool_name  # type: ignore[attr-defined]

        base_tools = resolve_tools(enabled_builtin=self._factory.default_tool_names)
        self._mcp_manager = MCPManager(config.mcp, self._logger)
        try:
            mcp_tools = self._mcp_manager.activate()
        except Exception as exc:  # pragma: no cover - defensivo
            self._logger.error("Error activando transporte MCP: %s", exc)
            mcp_tools = []
        all_tools = [*base_tools, *mcp_tools]

        try:
            build = self._factory.build_agent(all_tools)
        except Exception as exc:  # pragma: no cover - depende del entorno
            self._logger.error("Error inicializando el agente Strands: %s", exc)
            self._error_message = (
                "⚠️ No fue posible inicializar el agente Strands. Revisa los registros "
                "para más detalles."
            )
            if self._mcp_manager:
                self._mcp_manager.close()
            self._permission_manager.restore()
            return

        self._agent = build.agent
        # Compartimos la conexión SSH con la tool personalizada
        self._agent.ssh_manager = self._connection_manager  # type: ignore[attr-defined]
        timeout = self._factory.remote_command.timeout_seconds
        if timeout is not None:
            self._agent.remote_command_timeout = timeout  # type: ignore[attr-defined]
        max_output_chars = self._factory.remote_command.max_output_chars
        if max_output_chars is not None:
            self._agent.remote_command_max_output_chars = max_output_chars  # type: ignore[attr-defined]
        if self._factory.consent_bypass:
            self._permission_manager.activate()
        else:
            self._permission_manager.restore()
        self._ready = True
        config_path = config.config_path
        self._status_message = f"✅ Agente Strands inicializado (configuración: `{config_path}`)"

    @property
    def max_turns(self) -> int | None:
        """Límite de turnos por instrucción (``agent.max_turns``); ``None`` si está desactivado."""

        if not self._config:
            return None
        return self._config.options.max_turns

    def invoke(self, prompt: str) -> str:
        if not self.ready:
            raise RuntimeError("El agente no está disponible.")
        assert self._agent is not None
        # ``limits`` acota la invocación en Strands: al alcanzar ``turns`` el event loop
        # termina con ``stop_reason="limit_turns"`` en vez de seguir recurriendo.
        call_kwargs: dict[str, Any] = {}
        max_turns = self.max_turns
        if max_turns is not None:
            call_kwargs["limits"] = {"turns": max_turns}
        try:
            result = self._agent(prompt, **call_kwargs)
        except Exception as exc:  # pragma: no cover - depende del proveedor
            self._logger.exception("Error ejecutando el agente")
            return f"❌ El agente falló al procesar la instrucción: {exc}"
        if isinstance(result, AgentResult):
            self._record_cache_usage(result)
            text = self._render_agent_result(result)
            if getattr(result, "stop_reason", None) == "limit_turns":
                return self._append_turn_limit_notice(text, max_turns)
            return text or "(sin respuesta)"
        return str(result)

    def _append_turn_limit_notice(self, text: str, max_turns: int | None) -> str:
        """Añade al texto del agente el aviso localizado de límite de turnos alcanzado."""

        self._logger.warning(
            "El agente alcanzó el límite de %s turnos por instrucción (agent.max_turns); "
            "invocación detenida por Strands con stop_reason='limit_turns'",
            max_turns,
        )
        notice = _("agent.invoke.turn_limit", limit=max_turns)
        return f"{text}\n\n{notice}" if text else notice

    def _render_agent_result(self, result: AgentResult) -> str:
        text = str(result)
        if self._hide_thinking:
            text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
        return text.strip()

    def _record_cache_usage(self, result: AgentResult) -> None:
        """Extrae de las métricas de Strands los tokens cacheados del último turno."""

        usage = _last_invocation_usage(result)
        if usage is None:
            self._last_cache_usage = None
            return

        snapshot = summarize_cache_usage(usage)
        self._last_cache_usage = snapshot
        self._logger.info(
            "Prompt cache del último turno: %d de %d tokens de entrada leídos de caché "
            "(%d escritos)",
            snapshot["cached_tokens"],
            snapshot["input_tokens"],
            snapshot["written_tokens"],
        )

    def shutdown(self) -> None:
        if self._mcp_manager:
            self._mcp_manager.close()
        self._mcp_manager = None
        self._ready = False
        self._permission_manager.restore()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------

    def _format_provider_label(self, provider_cfg: ProviderBaseConfig) -> str:
        mapping = {
            "bedrock": "Amazon Bedrock",
            "openai": "OpenAI",
            "local": "Ollama",
            "lmstudio": "LM Studio",
            "cerebras": "Cerebras",
            "mistral": "Mistral AI",
            "gemini": "Google Gemini",
        }

        provider_key = self._config.provider if self._config else None
        if provider_key and provider_key in mapping:
            return mapping[provider_key]

        class_name = provider_cfg.__class__.__name__
        suffix = "ProviderConfig"
        if class_name.endswith(suffix):
            class_name = class_name[: -len(suffix)]

        # Separar nombres en CamelCase para crear una etiqueta legible.
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", class_name)
        label = " ".join(parts).strip()
        return label or (provider_key or "")


def _last_invocation_usage(result: AgentResult) -> Mapping[str, Any] | None:
    """Devuelve el ``Usage`` de la última invocación del agente, o ``None`` si no hay métricas."""

    metrics = getattr(result, "metrics", None)
    if metrics is None:
        return None
    invocations = getattr(metrics, "agent_invocations", None) or []
    usage: Any = None
    if invocations:
        usage = getattr(invocations[-1], "usage", None)
    if not usage:
        usage = getattr(metrics, "accumulated_usage", None)
    if not isinstance(usage, Mapping):
        return None
    return usage


def summarize_cache_usage(usage: Mapping[str, Any]) -> dict[str, int]:
    """Normaliza un ``Usage`` de Strands en tokens de entrada, leídos y escritos en caché.

    Bedrock informa ``inputTokens`` sin contar los tokens cacheados, mientras que OpenAI
    los incluye en ``prompt_tokens``. Se aplica la misma heurística que
    ``strands.telemetry.metrics``: si entrada + salida coincide con el total, los tokens
    cacheados ya están incluidos; en caso contrario se suman.
    """

    input_tokens = int(usage.get("inputTokens", 0) or 0)
    output_tokens = int(usage.get("outputTokens", 0) or 0)
    total_tokens = int(usage.get("totalTokens", 0) or 0)
    cached = int(usage.get("cacheReadInputTokens", 0) or 0)
    written = int(usage.get("cacheWriteInputTokens", 0) or 0)

    if input_tokens + output_tokens != total_tokens:
        input_tokens += cached + written

    percent = round(100 * cached / input_tokens) if input_tokens > 0 else 0
    return {
        "input_tokens": input_tokens,
        "cached_tokens": cached,
        "written_tokens": written,
        "percent": percent,
    }


__all__ = ["AgentRuntime", "summarize_cache_usage"]
