"""Configuración de logging para Almost Human Sys Admin."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from .config import LoggingConfig


def configure_logging(config: LoggingConfig) -> logging.Logger:
    """Configura el logging global según la configuración suministrada."""
    log_level = getattr(logging, config.level.upper(), logging.INFO)
    project_root = Path(__file__).resolve().parents[2]

    log_dir = Path(config.directory).expanduser()
    if not log_dir.is_absolute():
        log_dir = project_root / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    filename_path = Path(config.filename).expanduser()
    if filename_path.is_absolute():
        log_path = filename_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_path = log_dir / filename_path

    formatter = logging.Formatter(config.format)
    timed_handler = TimedRotatingFileHandler(
        log_path,
        when=config.when,
        interval=config.interval,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    timed_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(timed_handler)

    if config.log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    logger = logging.getLogger("smart_ai_sys_admin")
    logger.debug("Logging configurado en %s", log_path)
    return logger
