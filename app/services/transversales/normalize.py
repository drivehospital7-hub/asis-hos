"""Funciones de normalización compartidas entre módulos transversales."""

from __future__ import annotations

from typing import Any


def normalize_header(value: Any) -> str:
    """Normaliza un header a minúsculas sin espacios extra."""
    return str(value).strip().lower() if value is not None else ""


def normalize_invoice(value: Any) -> str | None:
    """Normaliza un número de factura a string."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        return str(int(value))
    return str(value).strip() or None
