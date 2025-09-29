"""Carga de configuraciones para Smart-AI-Sys-Admin."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InputConfig:
    placeholder: str
    background: str
    text_style: str
    submit_binding: str
    min_lines: int
    max_lines: int
    padding: str


@dataclass(frozen=True)
class PanelConfig:
    title: str
    border_style: str
    text_style: str
    background: str | None = None


@dataclass(frozen=True)
class OutputPanelConfig(PanelConfig):
    initial_markdown: str = ""
    placeholder_response_markdown: str = ""


@dataclass(frozen=True)
class ExitDialogConfig:
    title: str
    message: str
    confirm_label: str
    cancel_label: str
    prompt_markdown: str


@dataclass(frozen=True)
class DialogsConfig:
    exit: ExitDialogConfig


@dataclass(frozen=True)
class UIConfig:
    history_limit: int
    output_panel: OutputPanelConfig
    user_panel: PanelConfig
    input_widget: InputConfig
    connection_panel: PanelConfig
    dialogs: DialogsConfig


@dataclass(frozen=True)
class TerminalConfig:
    allowed_terms: tuple[str, ...]
    warning_message: str
    warning_icon: str
    unknown_label: str
    detected_label: str


@dataclass(frozen=True)
class ShortcutConfig:
    binding: str
    description: str


@dataclass(frozen=True)
class ShortcutsConfig:
    exit: ShortcutConfig


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    directory: str
    filename: str
    format: str
    when: str
    interval: int
    backup_count: int
    log_to_console: bool


@dataclass(frozen=True)
class AppConfig:
    terminal: TerminalConfig
    ui: UIConfig
    shortcuts: ShortcutsConfig
    logging: LoggingConfig


CONFIG_FILE_ENV = "SMART_AI_SYS_ADMIN_CONFIG_FILE"
CONFIG_DIR_ENV = "SMART_AI_SYS_ADMIN_CONFIG_DIR"
DEFAULT_CONFIG_FILENAME = "app_config.json"


def _default_conf_dir() -> Path:
    module_path = Path(__file__).resolve()
    return module_path.parents[3] / "conf"


def _resolve_config_path() -> Path:
    file_env = os.environ.get(CONFIG_FILE_ENV)
    if file_env:
        return Path(file_env).expanduser()

    dir_env = os.environ.get(CONFIG_DIR_ENV)
    base_dir = Path(dir_env).expanduser() if dir_env else _default_conf_dir()
    return base_dir / DEFAULT_CONFIG_FILENAME


def load_config() -> AppConfig:
    """Carga el archivo de configuración desde el directorio `conf`."""
    config_path = _resolve_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración en '{config_path}'.")
    with config_path.open("r", encoding="utf-8") as config_file:
        payload: dict[str, Any] = json.load(config_file)
    terminal = TerminalConfig(
        allowed_terms=tuple(payload["terminal"]["allowed_terms"]),
        warning_message=payload["terminal"]["warning_message"],
        warning_icon=payload["terminal"]["warning_icon"],
        unknown_label=payload["terminal"]["unknown_label"],
        detected_label=payload["terminal"]["detected_label"],
    )
    ui_config = payload["ui"]
    output_panel = OutputPanelConfig(**ui_config["output_panel"])
    user_panel = PanelConfig(**ui_config["user_panel"])
    connection_panel = PanelConfig(**ui_config["connection_panel"])
    input_widget = InputConfig(**ui_config["input_widget"])
    dialogs_config = ui_config["dialogs"]
    exit_dialog = ExitDialogConfig(**dialogs_config["exit"])
    dialogs = DialogsConfig(exit=exit_dialog)
    ui = UIConfig(
        history_limit=ui_config["history_limit"],
        output_panel=output_panel,
        user_panel=user_panel,
        input_widget=input_widget,
        connection_panel=connection_panel,
        dialogs=dialogs,
    )
    shortcuts_config = payload["shortcuts"]
    shortcuts = ShortcutsConfig(exit=ShortcutConfig(**shortcuts_config["exit"]))
    logging_config_data = payload["logging"]
    logging_config = LoggingConfig(
        level=logging_config_data["level"],
        directory=logging_config_data["directory"],
        filename=logging_config_data["filename"],
        format=logging_config_data["format"],
        when=logging_config_data["when"],
        interval=logging_config_data["interval"],
        backup_count=logging_config_data["backup_count"],
        log_to_console=logging_config_data.get("log_to_console", False),
    )
    return AppConfig(terminal=terminal, ui=ui, shortcuts=shortcuts, logging=logging_config)


CONFIG = load_config()
