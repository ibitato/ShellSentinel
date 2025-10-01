"""Módulo de soporte para localización e internacionalización."""

from __future__ import annotations

import json
import locale
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger("smart_ai_sys_admin.localization")

DEFAULT_LOCALE = "en"
LOCALE_ENV_VAR = "SMART_AI_SYS_ADMIN_LOCALE"
_PLACEHOLDER_PREFIX = "{{"
_PLACEHOLDER_SUFFIX = "}}"


_plugin_translations: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class Localizer:
    """Resuelve claves de traducción con fallback a un locale por defecto."""

    translations: dict[str, Any]
    active_locale: str
    fallback_locale: str

    def get(self, key: str, /, **kwargs: Any) -> str:
        """Devuelve el texto localizado para ``key``.

        Si la clave no existe se devuelve la propia clave para facilitar la
        detección de faltantes.
        """

        raw = self._lookup(key)
        if not isinstance(raw, str):
            _LOGGER.debug("Clave de localización '%s' no es una cadena (%r)", key, raw)
            return key
        if kwargs:
            try:
                return raw.format(**kwargs)
            except Exception:  # pragma: no cover - defensivo
                _LOGGER.warning(
                    "No se pudo formatear la clave '%s' con argumentos %s", key, kwargs
                )
                return raw
        return raw

    def section(self, key: str) -> dict[str, Any]:
        """Obtiene un subárbol de traducciones (usado para estructuras complejas)."""

        node = self._lookup(key)
        if isinstance(node, dict):
            return node
        raise KeyError(key)

    def format(self, key: str, *, default: str | None = None, **kwargs: Any) -> str:
        """Versión segura de :meth:`get` con valor por defecto opcional."""

        try:
            return self.get(key, **kwargs)
        except Exception:
            return default if default is not None else key

    def _lookup(self, key: str) -> Any:
        parts = key.split(".")
        node: Any = self.translations
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                _LOGGER.debug("Clave '%s' no encontrada en locale '%s'", key, self.active_locale)
                raise KeyError(key)
            node = node[part]
        return node


_cached_localizer: Localizer | None = None


def detect_locale() -> str:
    """Detecta el locale efectivo considerando variable de entorno y sistema."""

    override = os.environ.get(LOCALE_ENV_VAR)
    if override:
        return _normalize_locale(override)
    system_locale = locale.getdefaultlocale()[0] or locale.getlocale()[0]
    if system_locale:
        return _normalize_locale(system_locale)
    return DEFAULT_LOCALE


def get_localizer() -> Localizer:
    """Devuelve un ``Localizer`` singleton inicializado bajo demanda."""

    global _cached_localizer
    if _cached_localizer is None:
        locale_code = detect_locale()
        translations = _load_translations(locale_code)
        _cached_localizer = Localizer(
            translations=translations,
            active_locale=locale_code,
            fallback_locale=DEFAULT_LOCALE,
        )
        _LOGGER.info(
            "Localización activa: %s (fallback: %s)",
            locale_code,
            DEFAULT_LOCALE,
        )
    return _cached_localizer


def reset_localizer(locale_code: str | None = None) -> Localizer:
    """Permite restablecer el ``Localizer`` (principalmente para pruebas)."""

    global _cached_localizer
    _cached_localizer = None
    if locale_code is not None:
        os.environ[LOCALE_ENV_VAR] = locale_code
    return get_localizer()


def register_plugin_translations(locale_code: str, translations: Mapping[str, Any]) -> None:
    """Registra traducciones adicionales suministradas por un plugin."""

    normalized = _normalize_locale(locale_code)
    existing = _plugin_translations.get(normalized, {})
    _plugin_translations[normalized] = _merge_dicts(existing, dict(translations))
    _refresh_localizer()


def _refresh_localizer() -> None:
    global _cached_localizer
    if _cached_localizer is None:
        return
    active = _cached_localizer.active_locale
    fallback = _cached_localizer.fallback_locale
    _cached_localizer = Localizer(
        translations=_load_translations(active),
        active_locale=active,
        fallback_locale=fallback,
    )


def _(key: str, /, **kwargs: Any) -> str:
    """Alias corto estilo gettext para :meth:`Localizer.get`."""

    try:
        return get_localizer().get(key, **kwargs)
    except KeyError:
        return key


def localize_placeholders(payload: Any) -> Any:
    """Aplica localización a valores con sintaxis ``{{clave.de.traduccion}}``."""

    localizer = get_localizer()
    if isinstance(payload, dict):
        return {key: localize_placeholders(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [localize_placeholders(item) for item in payload]
    if isinstance(payload, str) and payload.startswith(_PLACEHOLDER_PREFIX) and payload.endswith(
        _PLACEHOLDER_SUFFIX
    ):
        key = payload[len(_PLACEHOLDER_PREFIX) : -len(_PLACEHOLDER_SUFFIX)].strip()
        try:
            return localizer.get(key)
        except KeyError:
            _LOGGER.warning("No se encontró traducción para la clave '%s'", key)
            return key
    return payload


def translations_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "conf" / "locales"


def _normalize_locale(raw: str) -> str:
    candidate = raw.strip().replace("_", "-")
    if not candidate:
        return DEFAULT_LOCALE
    segments = candidate.split("-")
    primary = segments[0].lower()
    if len(segments) == 1:
        return primary
    region = segments[1].upper()
    return f"{primary}-{region}"


def _load_translations(locale_code: str) -> dict[str, Any]:
    root = translations_directory()
    chain = _locale_chain(locale_code)
    merged: dict[str, Any] = {}
    for code in chain:
        file_path = root / code / "strings.json"
        if not file_path.is_file():
            _LOGGER.debug("Archivo de traducciones inexistente: %s", file_path)
            continue
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:  # pragma: no cover - defensivo
            _LOGGER.warning("No se pudo cargar %s: %s", file_path, exc)
            continue
        merged = _merge_dicts(merged, data)
    if not merged:
        _LOGGER.warning(
            "No se encontraron traducciones para '%s'; usando fallback '%s'",
            locale_code,
            DEFAULT_LOCALE,
        )
        fallback_path = root / DEFAULT_LOCALE / "strings.json"
        if fallback_path.is_file():
            with fallback_path.open("r", encoding="utf-8") as handle:
                merged = json.load(handle)
        else:
            merged = {}
    for code in chain:
        plugin_payload = _plugin_translations.get(code)
        if plugin_payload:
            merged = _merge_dicts(merged, plugin_payload)
    return merged


def _locale_chain(locale_code: str) -> list[str]:
    normalized = _normalize_locale(locale_code)
    chain: list[str] = [DEFAULT_LOCALE]
    if normalized == DEFAULT_LOCALE:
        return chain
    language = normalized.split("-")[0]
    if language and language not in chain:
        chain.append(language)
    if normalized not in chain:
        chain.append(normalized)
    return chain


def _merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


__all__ = [
    "Localizer",
    "DEFAULT_LOCALE",
    "detect_locale",
    "get_localizer",
    "localize_placeholders",
    "reset_localizer",
    "_",
]
