"""Backend service del cruce producción vs carpetas (Task 1)."""

from __future__ import annotations

from app.services.cruce_produccion.exporter import (
    build_cruce_export_workbook,
    cache_cruce_result,
    get_cached_cruce_result,
)
from app.services.cruce_produccion.matcher import extract_code, find_faltantes
from app.services.cruce_produccion.reader import read_produccion

__all__: list[str] = [
    "read_produccion",
    "extract_code",
    "find_faltantes",
    "build_cruce_export_workbook",
    "cache_cruce_result",
    "get_cached_cruce_result",
]
