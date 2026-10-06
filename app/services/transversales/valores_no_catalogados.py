"""Scan de valores no catalogados (S4, antiruido de volatilidad).

Compara los valores distintos de cada campo con semantica allowlist
(ver app.constants.valores) contra la union de sus catalogos.
Reporta {campo, valor, conteo} para lo no reconocido: es la alarma
temprana de "aparecio un centro nuevo / cambio una tilde" antes de
que contamine veredictos.

La normalizacion espeja al evaluador `in` del motor (NFC + strip +
upper): lo que el motor matchearia no se reporta.
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


def normalize_value(value: Any) -> str:
    """Normaliza un valor como el evaluador `in` del motor."""
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip().upper()


def find_unrecognized_values(
    rows: list[dict[str, Any]],
    catalog_values: dict[str, set[str]],
    *,
    max_per_field: int = 20,
) -> list[dict[str, Any]]:
    """Valores de `rows` no presentes en sus catalogos, con conteo.

    Args:
        rows: Filas ya mapeadas (claves = campos internos).
        catalog_values: {campo: set de valores reconocidos YA normalizados}.
        max_per_field: Tope de valores reportados por campo.

    Returns:
        Lista de {campo, valor, conteo} ordenada por campo y conteo desc.
        `valor` conserva el texto original de la primera aparicion.
    """
    counts: dict[str, dict[str, int]] = {}
    first_seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        for field, recognized in catalog_values.items():
            raw = row.get(field)
            norm = normalize_value(raw)
            if not norm or norm in recognized:
                continue
            counts.setdefault(field, {}).setdefault(norm, 0)
            counts[field][norm] += 1
            if norm not in first_seen.setdefault(field, {}):
                first_seen[field][norm] = raw

    report: list[dict[str, Any]] = []
    for field in sorted(counts):
        ordered = sorted(counts[field].items(), key=lambda kv: (-kv[1], kv[0]))
        for norm, count in ordered[:max_per_field]:
            report.append({
                "campo": field,
                "valor": first_seen[field][norm],
                "conteo": count,
            })
    if report:
        logger.warning(
            "Valores no catalogados: %d caso(s): %s",
            len(report),
            [(r["campo"], r["valor"], r["conteo"]) for r in report],
        )
    return report


def load_recognized_values(
    session: Any, field_catalogs: dict[str, tuple[str, ...]],
) -> dict[str, set[str]]:
    """Carga y normaliza los valores reconocidos por campo desde la DB.

    Best-effort por catalogo: un catalogo faltante o con otro formato
    se saltea con warning, nunca rompe el scan.
    """
    from app.services.reglas.catalogos_service import get_catalogo

    recognized: dict[str, set[str]] = {}
    for field, keys in field_catalogs.items():
        values: set[str] = set()
        for key in keys:
            try:
                cat = get_catalogo(session, key)
            except Exception:
                logger.exception("No se pudo leer catalogo %s", key)
                continue
            if not cat:
                logger.warning("Catalogo inexistente: %s", key)
                continue
            for val in cat.get("values", []) or []:
                norm = normalize_value(val)
                if norm:
                    values.add(norm)
        if values:
            recognized[field] = values
        else:
            logger.warning("Sin valores reconocidos para campo %s", field)
    return recognized
