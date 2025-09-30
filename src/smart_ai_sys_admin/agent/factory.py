"""Fabricación del agente de Strands según la configuración cargada."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import (
    NullConversationManager,
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)
from strands.models import BedrockModel
from strands.models.ollama import OllamaModel
from strands.models.openai import OpenAIModel

from .config import (
    AgentConfig,
    AgentConfigError,
    AgentOptions,
    BedrockProviderConfig,
    LocalProviderConfig,
    MCPConfig,
    OpenAIProviderConfig,
    ProviderBaseConfig,
    RemoteCommandConfig,
)

logger = logging.getLogger("smart_ai_sys_admin.agent.factory")


@dataclass(frozen=True)
class AgentBuildResult:
    """Resultado de la construcción del agente."""

    agent: Agent
    mcp_config: MCPConfig


class AgentFactory:
    """Construye instancias de `Agent` de Strands a partir de la configuración declarativa."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def build_agent(self, tools: Sequence[Any] | None = None) -> AgentBuildResult:
        provider_cfg = self._config.provider_config()
        model = self._build_model(provider_cfg)
        conversation_manager = self._build_conversation_manager(self._config.options)
        system_prompt = provider_cfg.system_prompt

        # Copiamos las herramientas para no mutar la lista externa
        tools_list = list(tools or [])
        agent = Agent(
            model=model,
            tools=tools_list or None,
            system_prompt=system_prompt,
            conversation_manager=conversation_manager,
            trace_attributes=dict(self._config.options.trace_attributes),
            load_tools_from_directory=self._config.tools.load_directory,
        )
        agent.show_thinking = getattr(provider_cfg, "show_thinking", False)  # type: ignore[attr-defined]
        return AgentBuildResult(agent=agent, mcp_config=self._config.mcp)

    # ------------------------------------------------------------------
    # Construcción de componentes auxiliares
    # ------------------------------------------------------------------

    def _build_model(self, provider_cfg: ProviderBaseConfig) -> Any:
        if isinstance(provider_cfg, BedrockProviderConfig):
            return self._build_bedrock_model(provider_cfg)
        if isinstance(provider_cfg, OpenAIProviderConfig):
            return self._build_openai_model(provider_cfg)
        if isinstance(provider_cfg, LocalProviderConfig):
            return self._build_local_model(provider_cfg)
        raise AgentConfigError("Tipo de proveedor no soportado")

    def _build_bedrock_model(self, cfg: BedrockProviderConfig) -> BedrockModel:
        params = dict(cfg.params)
        client_cfg = dict(cfg.client)

        # Usar streaming predeterminado si no se especifica
        if "streaming" not in params:
            params["streaming"] = self._config.options.streaming

        # Determinar región base
        region = params.get("region_name") or cfg.region_name

        session = None
        profile = client_cfg.get("profile")
        access_key = client_cfg.get("access_key_id")
        secret_key = client_cfg.get("secret_access_key")
        session_token = client_cfg.get("session_token")

        if profile or access_key or secret_key or session_token:
            try:
                import boto3

                session_kwargs: dict[str, object] = {}
                if profile:
                    session_kwargs["profile_name"] = profile
                if region:
                    session_kwargs["region_name"] = region
                if access_key and secret_key:
                    session_kwargs["aws_access_key_id"] = access_key
                    session_kwargs["aws_secret_access_key"] = secret_key
                    if session_token:
                        session_kwargs["aws_session_token"] = session_token
                session = boto3.Session(**session_kwargs)
            except Exception as exc:  # pragma: no cover - depende del entorno local
                raise AgentConfigError(
                    "No se pudo inicializar la sesión de boto3 con las credenciales proporcionadas"
                ) from exc

        if session:
            params.pop("region_name", None)
            params["boto_session"] = session
        elif region and "region_name" not in params:
            params["region_name"] = region

        # endpoint_url y otros parámetros adicionales se pueden añadir en params
        if client_cfg.get("endpoint_url"):
            logger.debug(
                "Se indicó endpoint_url para Bedrock; se usará la configuración estándar de boto3"
            )

        logger.debug("Instanciando BedrockModel con parámetros: %s", params.keys())
        return BedrockModel(model_id=cfg.model_id, **params)

    def _build_openai_model(self, cfg: OpenAIProviderConfig) -> OpenAIModel:
        client_args = dict(cfg.client_args)
        api_key_env = client_args.pop("api_key_env", None)
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                raise AgentConfigError(
                    "No se encontró la variable de entorno "
                    f"'{api_key_env}' para la clave de OpenAI."
                )
            client_args["api_key"] = api_key
        logger.debug("Instanciando OpenAIModel con argumentos del cliente: %s", client_args.keys())
        params = dict(cfg.params)
        return OpenAIModel(
            client_args=client_args or None, model_id=cfg.model_id, params=params or None
        )

    def _build_local_model(self, cfg: LocalProviderConfig) -> OllamaModel:
        params = dict(cfg.params)
        logger.debug(
            "Instanciando OllamaModel contra %s con parámetros: %s", cfg.host, params.keys()
        )
        return OllamaModel(host=cfg.host, model_id=cfg.model_id, **params)

    def _build_conversation_manager(self, options: AgentOptions):
        conversation = options.conversation
        if conversation.strategy == "sliding_window":
            window_size = int(conversation.options.get("window_size", 40))
            truncate = bool(conversation.options.get("truncate_tool_results", True))
            return SlidingWindowConversationManager(
                window_size=window_size,
                should_truncate_results=truncate,
            )
        if conversation.strategy == "summarizing":
            ratio = float(conversation.options.get("summary_ratio", 0.3))
            preserve = int(conversation.options.get("preserve_recent_messages", 10))
            return SummarizingConversationManager(
                summary_ratio=ratio,
                preserve_recent_messages=preserve,
            )
        return NullConversationManager()

    # ------------------------------------------------------------------
    # Accesores convenientes
    # ------------------------------------------------------------------

    @property
    def default_tool_names(self) -> tuple[str, ...]:
        return self._config.tools.default_tools

    @property
    def remote_command(self) -> RemoteCommandConfig:
        return self._config.tools.remote_command

    @property
    def sftp_transfer_name(self) -> str:
        return self._config.tools.sftp_transfer_name

    @property
    def mcp_config(self) -> MCPConfig:
        return self._config.mcp

    @property
    def consent_bypass(self) -> bool:
        return self._config.tools.consent_bypass


__all__ = [
    "AgentBuildResult",
    "AgentFactory",
]
