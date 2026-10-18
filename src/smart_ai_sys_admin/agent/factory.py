"""Fabricación del agente de Strands según la configuración cargada."""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strands import Agent
from strands.agent.conversation_manager import (
    NullConversationManager,
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)
from strands.models import BedrockModel, OpenAIResponsesModel
from strands.models.model import CacheConfig
from strands.models.ollama import OllamaModel
from strands.models.openai import OpenAIModel

from .config import (
    MISTRAL_DEFAULT_MAX_TOKENS,
    AgentConfig,
    AgentConfigError,
    AgentOptions,
    BedrockProviderConfig,
    CerebrasProviderConfig,
    LMStudioProviderConfig,
    LocalProviderConfig,
    MCPConfig,
    MistralProviderConfig,
    OpenAIProviderConfig,
    ProviderBaseConfig,
    ProviderCacheConfig,
    RemoteCommandConfig,
)
from .providers import CerebrasModel, ShellMistralModel

logger = logging.getLogger("smart_ai_sys_admin.agent.factory")

CACHE_KEY_PREFIX = "shell-sentinel-"


def derive_cache_key(config_path: Path | str, model_id: str) -> str:
    """Deriva una clave de enrutamiento de caché estable para OpenAI/Mistral.

    Shell Sentinel no usa un gestor de sesiones de Strands, así que sin esta clave cada
    arranque sería un prefijo distinto para el proveedor. La clave combina la ruta de la
    configuración y el ``model_id`` para que sesiones repetidas compartan el prefijo
    cacheado sin filtrar información sensible.
    """

    digest = hashlib.sha256(f"{config_path}|{model_id}".encode()).hexdigest()
    return f"{CACHE_KEY_PREFIX}{digest[:16]}"


def build_strands_cache_config(
    cache: ProviderCacheConfig, *, default_cache_key: str | None = None
) -> CacheConfig | None:
    """Traduce ``ProviderCacheConfig`` a ``strands.models.model.CacheConfig``.

    Devuelve ``None`` cuando la caché está desactivada. Solo se pasan a Strands los campos
    que el operador fijó (o la clave derivada), de modo que los valores por defecto de
    Strands se mantienen y sus avisos sobre campos no soportados siguen siendo fiables.
    """

    if not cache.enabled:
        return None

    kwargs: dict[str, Any] = {}
    if cache.strategy is not None:
        kwargs["strategy"] = cache.strategy
    if cache.ttl is not None:
        kwargs["ttl"] = cache.ttl
    if cache.system_prompt_ttl is not None:
        kwargs["system_prompt_ttl"] = cache.system_prompt_ttl
    if cache.tools_ttl is not None:
        kwargs["tools_ttl"] = cache.tools_ttl

    cache_key = cache.cache_key if cache.cache_key is not None else default_cache_key
    if cache_key is not None:
        kwargs["cache_key"] = cache_key

    return CacheConfig(**kwargs)


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
            if provider_cfg.api == "responses":
                return self._build_openai_responses_model(provider_cfg)
            return self._build_openai_model(provider_cfg)
        if isinstance(provider_cfg, LocalProviderConfig):
            return self._build_local_model(provider_cfg)
        if isinstance(provider_cfg, LMStudioProviderConfig):
            return self._build_lmstudio_model(provider_cfg)
        if isinstance(provider_cfg, CerebrasProviderConfig):
            return self._build_cerebras_model(provider_cfg)
        if isinstance(provider_cfg, MistralProviderConfig):
            return self._build_mistral_model(provider_cfg)
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

        # Bedrock exige cache points explícitos: Strands los inserta con ``strategy="auto"``
        # solo para modelos Claude/Anthropic, así que otros modelos no se ven afectados.
        cache_config = build_strands_cache_config(cfg.cache)
        if cache_config is not None:
            params["cache_config"] = cache_config
            logger.debug("Prompt caching de Bedrock activo: %s", cache_config)

        logger.debug("Instanciando BedrockModel con parámetros: %s", params.keys())
        return BedrockModel(model_id=cfg.model_id, **params)

    def _resolve_openai_client_args(self, cfg: OpenAIProviderConfig) -> dict[str, Any]:
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
        return client_args

    def _routing_cache_config(self, cfg: ProviderBaseConfig, model_id: str) -> CacheConfig | None:
        """Caché para proveedores que enrutan por clave (OpenAI, Mistral, LM Studio).

        Estos servidores cachean prefijos automáticamente; Strands solo envía la clave de
        enrutamiento (``prompt_cache_key``). Si el operador no fijó ``cache_key`` se deriva
        una estable a partir de la ruta de configuración y el modelo.
        """

        config_path = getattr(self._config, "config_path", None) or ""
        default_key = derive_cache_key(config_path, model_id)
        cache_config = build_strands_cache_config(cfg.cache, default_cache_key=default_key)
        if cache_config is not None:
            logger.debug("Prompt caching por clave activo: cache_key=%s", cache_config.cache_key)
        return cache_config

    @staticmethod
    def _warn_cache_config_not_supported(provider: str, cache: ProviderCacheConfig) -> None:
        """Avisa cuando se activa la caché en un proveedor que no la gestiona desde Strands."""

        if cache.enabled:
            logger.warning(
                "providers.%s.cache está activado pero el proveedor '%s' no admite prompt caching "
                "configurable desde Strands; el bloque se ignora.",
                provider,
                provider,
            )

    def _build_openai_model(self, cfg: OpenAIProviderConfig) -> OpenAIModel:
        client_args = self._resolve_openai_client_args(cfg)
        logger.debug("Instanciando OpenAIModel con argumentos del cliente: %s", client_args.keys())
        params = dict(cfg.params)
        return OpenAIModel(
            client_args=client_args or None,
            model_id=cfg.model_id,
            params=params or None,
            cache_config=self._routing_cache_config(cfg, cfg.model_id),
        )

    def _build_openai_responses_model(self, cfg: OpenAIProviderConfig) -> OpenAIResponsesModel:
        client_args = self._resolve_openai_client_args(cfg)
        logger.debug(
            "Instanciando OpenAIResponsesModel con argumentos del cliente: %s",
            client_args.keys(),
        )
        params = dict(cfg.params)
        return OpenAIResponsesModel(
            client_args=client_args or None,
            model_id=cfg.model_id,
            params=params or None,
            stateful=cfg.stateful,
            cache_config=self._routing_cache_config(cfg, cfg.model_id),
        )

    def _build_local_model(self, cfg: LocalProviderConfig) -> OllamaModel:
        params = dict(cfg.params)
        # Ollama cachea el prefijo localmente por su cuenta; Strands no aplica CacheConfig.
        self._warn_cache_config_not_supported("local", cfg.cache)
        logger.debug(
            "Instanciando OllamaModel contra %s con parámetros: %s", cfg.host, params.keys()
        )
        return OllamaModel(host=cfg.host, model_id=cfg.model_id, **params)

    def _build_lmstudio_model(self, cfg: LMStudioProviderConfig) -> OpenAIModel:
        client_args = dict(cfg.client_args)
        if "base_url" not in client_args:
            client_args["base_url"] = cfg.base_url

        api_key = None
        if cfg.api_key_env:
            api_key = os.getenv(cfg.api_key_env)
            if not api_key:
                logger.debug(
                    "Variable de entorno %s no definida; se usará api_key explícita si existe",
                    cfg.api_key_env,
                )
        if not api_key:
            api_key = cfg.api_key or client_args.get("api_key")

        if not api_key:
            raise AgentConfigError(
                "LM Studio requiere especificar 'api_key' o 'api_key_env' en la configuración"
            )

        client_args["api_key"] = api_key

        params = dict(cfg.params)
        if "stream" not in params:
            params["stream"] = self._config.options.streaming

        logger.debug(
            "Instanciando OpenAIModel contra LM Studio en %s con parámetros: %s",
            client_args["base_url"],
            params.keys(),
        )
        # LM Studio cachea localmente; la caché queda desactivada por defecto, pero si el
        # operador la activa se envía la clave de enrutamiento OpenAI-compatible.
        return OpenAIModel(
            client_args=client_args,
            model_id=cfg.model_id,
            params=params or None,
            cache_config=self._routing_cache_config(cfg, cfg.model_id),
        )

    def _build_cerebras_model(self, cfg: CerebrasProviderConfig) -> CerebrasModel:
        params = dict(cfg.params)
        client_args = dict(cfg.client_args)
        # El proveedor Cerebras de Shell Sentinel no implementa prompt caching.
        self._warn_cache_config_not_supported("cerebras", cfg.cache)
        logger.debug("Instanciando CerebrasModel con parámetros: %s", params.keys())
        return CerebrasModel(
            model_id=cfg.model_id,
            params=params,
            client_args=client_args,
            api_key=cfg.api_key,
            api_key_env=cfg.api_key_env,
        )

    def _build_mistral_model(self, cfg: MistralProviderConfig) -> ShellMistralModel:
        client_args = dict(cfg.client_args)
        api_key = cfg.api_key
        if cfg.api_key_env:
            api_key = os.getenv(cfg.api_key_env)
            if not api_key:
                raise AgentConfigError(
                    "No se encontró la variable de entorno "
                    f"'{cfg.api_key_env}' para la clave de Mistral."
                )
        if not api_key:
            api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise AgentConfigError(
                "Mistral requiere especificar 'api_key', 'api_key_env' o definir MISTRAL_API_KEY."
            )

        params = dict(cfg.params)
        if "stream" not in params:
            params["stream"] = self._config.options.streaming
        if "max_tokens" not in params:
            params["max_tokens"] = MISTRAL_DEFAULT_MAX_TOKENS
        # ShellMistralModel reenvía ``cache_config`` a MistralModel vía **model_config.
        cache_config = self._routing_cache_config(cfg, cfg.model_id)
        if cache_config is not None:
            params["cache_config"] = cache_config

        logger.debug(
            "Instanciando ShellMistralModel con model_id=%s reasoning_effort=%s",
            cfg.model_id,
            cfg.reasoning_effort,
        )
        return ShellMistralModel(
            api_key=api_key,
            client_args=client_args or None,
            model_id=cfg.model_id,
            reasoning_effort=cfg.reasoning_effort,  # type: ignore[arg-type]
            **params,
        )

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
    def default_tool_names(self) -> tuple[str, ...] | None:
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

    @property
    def cache_enabled(self) -> bool:
        """Indica si el proveedor activo envía configuración de caché a Strands."""

        provider_cfg = self._config.provider_config()
        if isinstance(provider_cfg, (LocalProviderConfig, CerebrasProviderConfig)):
            return False
        return provider_cfg.cache.enabled


__all__ = [
    "AgentBuildResult",
    "AgentFactory",
    "CACHE_KEY_PREFIX",
    "build_strands_cache_config",
    "derive_cache_key",
]
