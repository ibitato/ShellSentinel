"""Carga y representación de la configuración del agente Strands."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

ProviderLiteral = Literal["bedrock", "openai", "local", "lmstudio"]
ConversationStrategyLiteral = Literal["sliding_window", "summarizing", "none"]
MCPTransportLiteral = Literal["stdio", "sse", "streamable_http"]


class AgentConfigError(RuntimeError):
    """Error lanzado cuando la configuración del agente es inválida."""


@dataclass(frozen=True)
class ProviderBaseConfig:
    system_prompt_path: Path
    system_prompt: str
    show_thinking: bool


@dataclass(frozen=True)
class BedrockProviderConfig(ProviderBaseConfig):
    model_id: str
    region_name: str | None
    params: Mapping[str, Any]
    client: Mapping[str, Any]


@dataclass(frozen=True)
class OpenAIProviderConfig(ProviderBaseConfig):
    model_id: str
    client_args: Mapping[str, Any]
    params: Mapping[str, Any]


@dataclass(frozen=True)
class LocalProviderConfig(ProviderBaseConfig):
    host: str
    model_id: str
    params: Mapping[str, Any]


@dataclass(frozen=True)
class LMStudioProviderConfig(ProviderBaseConfig):
    model_id: str
    base_url: str
    api_key: str | None
    api_key_env: str | None
    client_args: Mapping[str, Any]
    params: Mapping[str, Any]


@dataclass(frozen=True)
class ConversationConfig:
    strategy: ConversationStrategyLiteral
    options: Mapping[str, Any]


@dataclass(frozen=True)
class AgentOptions:
    streaming: bool
    conversation: ConversationConfig
    trace_attributes: Mapping[str, Any]


@dataclass(frozen=True)
class RemoteCommandConfig:
    name: str
    timeout_seconds: int | None


@dataclass(frozen=True)
class ToolsConfig:
    default_tools: tuple[str, ...]
    remote_command: RemoteCommandConfig
    sftp_transfer_name: str
    load_directory: bool
    consent_bypass: bool


@dataclass(frozen=True)
class MCPTransportConfig:
    identifier: str
    transport_type: MCPTransportLiteral
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    env: Mapping[str, str] = field(default_factory=dict)
    env_passthrough: tuple[str, ...] = ()
    cwd: str | None = None
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class MCPConfig:
    enabled: bool
    load_server_tools: bool
    transports: tuple[MCPTransportConfig, ...]


@dataclass(frozen=True)
class AgentConfig:
    provider: ProviderLiteral
    providers: Mapping[ProviderLiteral, ProviderBaseConfig]
    options: AgentOptions
    tools: ToolsConfig
    mcp: MCPConfig
    config_path: Path

    def provider_config(self) -> ProviderBaseConfig:
        try:
            return self.providers[self.provider]
        except KeyError as exc:  # pragma: no cover - defensivo
            raise AgentConfigError(
                f"No existe configuración para el proveedor '{self.provider}'."
            ) from exc


AGENT_CONFIG_FILE_ENV = "SMART_AI_SYS_ADMIN_AGENT_CONFIG_FILE"
CONFIG_DIR_ENV = "SMART_AI_SYS_ADMIN_CONFIG_DIR"
DEFAULT_FILENAME = "agent.conf"


def _default_conf_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "conf"


def _resolve_config_path(explicit_path: str | None = None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser()
    env_file = os.environ.get(AGENT_CONFIG_FILE_ENV)
    if env_file:
        return Path(env_file).expanduser()
    base_dir = Path(os.environ.get(CONFIG_DIR_ENV, _default_conf_dir())).expanduser()
    return base_dir / DEFAULT_FILENAME


def _load_system_prompt(base_dir: Path, relative_path: str) -> tuple[str, Path]:
    raw_path = Path(relative_path).expanduser()
    candidates: list[Path] = []

    if raw_path.is_absolute():
        candidates.append(raw_path.resolve())
    else:
        candidates.append((base_dir / raw_path).resolve())
        project_root = Path(__file__).resolve().parents[3]
        candidates.append((project_root / raw_path).resolve())

    checked: list[Path] = []
    for candidate in candidates:
        if candidate in checked:
            continue
        checked.append(candidate)
        if not candidate.is_file():
            continue
        try:
            content = candidate.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - depende del sistema
            raise AgentConfigError(
                f"No se pudo leer el system prompt en '{candidate}': {exc}"
            ) from exc
        return content, candidate

    searched = ", ".join(str(path) for path in checked) or relative_path
    raise AgentConfigError(
        "No se encontró el system prompt en las rutas candidatas: "
        f"{searched}."
    )


def _mapping_proxy(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(payload or {}))


def _tuple_from_sequence(items: Sequence[str] | None) -> tuple[str, ...]:
    return tuple(items or ())


def _build_provider_configs(
    payload: Mapping[str, Any], config_dir: Path
) -> Mapping[ProviderLiteral, ProviderBaseConfig]:
    providers: dict[ProviderLiteral, ProviderBaseConfig] = {}

    if "bedrock" in payload:
        data = payload["bedrock"]
        system_prompt, prompt_path = _load_system_prompt(config_dir, data["system_prompt"])
        providers["bedrock"] = BedrockProviderConfig(
            system_prompt_path=prompt_path,
            system_prompt=system_prompt,
            show_thinking=bool(data.get("show_thinking", False)),
            model_id=data["model_id"],
            region_name=data.get("region_name"),
            params=_mapping_proxy(data.get("params")),
            client=_mapping_proxy(data.get("client")),
        )

    if "openai" in payload:
        data = payload["openai"]
        system_prompt, prompt_path = _load_system_prompt(config_dir, data["system_prompt"])
        raw_params = dict(data.get("params", {}))
        if "max_tokens" in raw_params and "max_completion_tokens" not in raw_params:
            raw_params["max_completion_tokens"] = raw_params.pop("max_tokens")
        providers["openai"] = OpenAIProviderConfig(
            system_prompt_path=prompt_path,
            system_prompt=system_prompt,
            show_thinking=bool(data.get("show_thinking", False)),
            model_id=data["model_id"],
            client_args=_mapping_proxy(data.get("client_args")),
            params=_mapping_proxy(raw_params),
        )

    if "local" in payload:
        data = payload["local"]
        system_prompt, prompt_path = _load_system_prompt(config_dir, data["system_prompt"])
        providers["local"] = LocalProviderConfig(
            system_prompt_path=prompt_path,
            system_prompt=system_prompt,
            show_thinking=bool(data.get("show_thinking", False)),
            host=data["host"],
            model_id=data["model_id"],
            params=_mapping_proxy(data.get("params")),
        )

    if "lmstudio" in payload:
        data = payload["lmstudio"]
        system_prompt, prompt_path = _load_system_prompt(config_dir, data["system_prompt"])
        base_url = data.get("base_url")
        if not base_url:
            raise AgentConfigError(
                "La configuración de LM Studio requiere la clave 'base_url'."
            )
        providers["lmstudio"] = LMStudioProviderConfig(
            system_prompt_path=prompt_path,
            system_prompt=system_prompt,
            show_thinking=bool(data.get("show_thinking", False)),
            model_id=data["model_id"],
            base_url=base_url,
            api_key=data.get("api_key"),
            api_key_env=data.get("api_key_env"),
            client_args=_mapping_proxy(data.get("client_args")),
            params=_mapping_proxy(data.get("params")),
        )

    return MappingProxyType(providers)


def _build_conversation_config(payload: Mapping[str, Any]) -> ConversationConfig:
    strategy = payload.get("strategy", "sliding_window")
    if strategy not in {"sliding_window", "summarizing", "none"}:
        raise AgentConfigError(f"Estrategia de conversación desconocida: {strategy}")
    options = _mapping_proxy({k: v for k, v in payload.items() if k != "strategy"})
    return ConversationConfig(strategy=strategy, options=options)


def _build_agent_options(payload: Mapping[str, Any]) -> AgentOptions:
    streaming = bool(payload.get("streaming", True))
    conversation_cfg = _build_conversation_config(payload.get("conversation", {}))
    trace_attributes = _mapping_proxy(payload.get("trace_attributes"))
    return AgentOptions(
        streaming=streaming, conversation=conversation_cfg, trace_attributes=trace_attributes
    )


def _build_tools_config(payload: Mapping[str, Any]) -> ToolsConfig:
    default_tools = _tuple_from_sequence(payload.get("default", []))
    remote_cfg = payload.get("remote_command", {})
    remote = RemoteCommandConfig(
        name=remote_cfg.get("name", "remote_ssh_command"),
        timeout_seconds=remote_cfg.get("timeout_seconds"),
    )
    sftp_name = payload.get("sftp_transfer", {}).get("name", "remote_sftp_transfer")
    load_directory = bool(payload.get("load_directory", False))
    consent = bool(payload.get("consent", {}).get("bypass", False))
    return ToolsConfig(
        default_tools=default_tools,
        remote_command=remote,
        sftp_transfer_name=sftp_name,
        load_directory=load_directory,
        consent_bypass=consent,
    )


def _build_transport(payload: Mapping[str, Any]) -> MCPTransportConfig:
    transport_type = payload.get("type")
    if transport_type not in {"stdio", "sse", "streamable_http"}:
        raise AgentConfigError(f"Tipo de transporte MCP inválido: {transport_type}")
    identifier = payload.get("id")
    if not identifier:
        raise AgentConfigError("Cada transporte MCP debe tener un identificador 'id'.")
    return MCPTransportConfig(
        identifier=identifier,
        transport_type=transport_type,
        command=payload.get("command"),
        args=tuple(payload.get("args", [])),
        url=payload.get("url"),
        headers=_mapping_proxy(payload.get("headers")),
        env=_mapping_proxy(payload.get("env")),
        env_passthrough=_tuple_from_sequence(payload.get("env_passthrough")),
        cwd=payload.get("cwd"),
        timeout_seconds=payload.get("timeout_seconds"),
    )


def _build_mcp_config(payload: Mapping[str, Any]) -> MCPConfig:
    enabled = bool(payload.get("enabled", False))
    load_server_tools = bool(payload.get("load_server_tools", True))
    transports = tuple(_build_transport(item) for item in payload.get("transports", []))
    return MCPConfig(enabled=enabled, load_server_tools=load_server_tools, transports=transports)


def load_agent_config(path: str | Path | None = None) -> AgentConfig:
    """Carga la configuración del agente desde disco."""

    config_path = _resolve_config_path(str(path) if path else None)
    if not config_path.is_file():
        raise AgentConfigError(
            f"No se encontró el archivo de configuración del agente en '{config_path}'."
        )

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AgentConfigError(
            f"El archivo '{config_path}' no contiene JSON válido: {exc}"
        ) from exc

    version = raw.get("version", 1)
    if version != 1:
        raise AgentConfigError(f"Versión de configuración no soportada: {version}")

    provider = raw.get("provider")
    if provider not in {"bedrock", "openai", "local", "lmstudio"}:
        raise AgentConfigError("Debes especificar un proveedor válido en 'provider'.")

    providers_section = raw.get("providers")
    if not isinstance(providers_section, Mapping):
        raise AgentConfigError("La sección 'providers' es obligatoria y debe ser un objeto.")

    config_dir = config_path.parent
    providers = _build_provider_configs(providers_section, config_dir)
    if provider not in providers:
        raise AgentConfigError(
            f"No se encontró configuración para el proveedor seleccionado '{provider}'."
        )

    agent_options = _build_agent_options(raw.get("agent", {}))
    tools = _build_tools_config(raw.get("tools", {}))
    mcp = _build_mcp_config(raw.get("mcp", {}))

    return AgentConfig(
        provider=provider,
        providers=providers,
        options=agent_options,
        tools=tools,
        mcp=mcp,
        config_path=config_path,
    )


__all__ = [
    "AgentConfig",
    "AgentConfigError",
    "AgentOptions",
    "BedrockProviderConfig",
    "ConversationConfig",
    "LocalProviderConfig",
    "LMStudioProviderConfig",
    "MCPConfig",
    "MCPTransportConfig",
    "OpenAIProviderConfig",
    "ProviderBaseConfig",
    "ProviderLiteral",
    "RemoteCommandConfig",
    "ToolsConfig",
    "load_agent_config",
]
