"""Validación de nombres de facturas contra patrones FEV y CAP.

Los patrones regex se definen en app/constants/monitoreo_carpetas.py.
El validador toma un filename (con o sin extensión), lo normaliza,
y devuelve una tupla (invoice_type, is_valid).
"""

from __future__ import annotations

import logging
import re

from app.constants.monitoreo_carpetas import CAP_REGEX, FEV_REGEX

logger = logging.getLogger(__name__)

_INVOICE_TYPE_FEV = "FEV"
_INVOICE_TYPE_CAP = "CAP"
_INVOICE_TYPE_UNKNOWN = "Unknown"

# Compiled regex patterns (case-insensitive)
_FEV_PATTERN = re.compile(FEV_REGEX, re.IGNORECASE)
_CAP_PATTERN = re.compile(CAP_REGEX, re.IGNORECASE)

# Prefix stripping: INV_ prefix is common and should not affect validity
_INV_PREFIX = re.compile(r"^INV_", re.IGNORECASE)

# Patterns to detect the type prefix even if the full name is invalid
_FEV_PREFIX = re.compile(r"FEV", re.IGNORECASE)
_CAP_PREFIX = re.compile(r"CAP", re.IGNORECASE)


def _strip_prefix(name: str) -> str:
    """Removes known prefixes (e.g. INV_) from the filename."""
    return _INV_PREFIX.sub("", name)


def validate_name(filename: str) -> tuple[str, bool]:
    """Valida un nombre de archivo contra patrones FEV y CAP.

    Extrae el nombre base sin extensión, intenta matchear FEV o CAP.
    Si el filename (sin extensión) es exactamente el patrón completo,
    el tipo es válido. Si el filename contiene el prefijo pero no
    matchea el patrón completo, el tipo se identifica pero como inválido.

    The INV_ prefix is stripped before matching (per spec: INV_FEV789 → valid FEV).

    Args:
        filename: Nombre del archivo (ej: "FEV12345.pdf" o "FEV12345").

    Returns:
        Tupla (tipo, es_válido) donde tipo es "FEV", "CAP", o "Unknown".
    """
    if not filename:
        return _INVOICE_TYPE_UNKNOWN, False

    # Strip extension
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    name = name.strip()

    if not name:
        return _INVOICE_TYPE_UNKNOWN, False

    # Strip known prefixes (like INV_) for matching
    stripped = _strip_prefix(name)

    # Try FEV full match on stripped name
    if _FEV_PATTERN.fullmatch(stripped):
        return _INVOICE_TYPE_FEV, True

    # Try CAP full match on stripped name
    if _CAP_PATTERN.fullmatch(stripped):
        return _INVOICE_TYPE_CAP, True

    # Has FEV prefix but didn't match fully -> invalid FEV
    if _FEV_PREFIX.search(stripped):
        return _INVOICE_TYPE_FEV, False

    # Has CAP prefix but didn't match fully -> invalid CAP
    if _CAP_PREFIX.search(stripped):
        return _INVOICE_TYPE_CAP, False

    return _INVOICE_TYPE_UNKNOWN, False
