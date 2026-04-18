"""Funções utilitárias compartilhadas pelos blueprints."""

from __future__ import annotations

from typing import Any

from flask import jsonify


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def success_response(data: Any, status_code: int = 200):
    """Retorna uma resposta JSON de sucesso no envelope padrão."""

    return jsonify({"data": data, "error": None}), status_code


def error_response(message: str, status_code: int = 400):
    """Retorna uma resposta JSON de erro no envelope padrão."""

    return jsonify({"data": None, "error": message}), status_code


def parse_bool(value: str | None, default: bool = True) -> bool:
    """Converte uma string de query param para booleano."""

    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return default


def normalize_text(value: Any) -> str | None:
    """Converte textos vazios em None e remove espaços laterais."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def is_valid_hex_color(color_hex: str) -> bool:
    """Valida uma string hexadecimal no formato #RRGGBB."""

    if len(color_hex) != 7 or not color_hex.startswith("#"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in color_hex[1:])
