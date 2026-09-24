"""Shared /procesar-shaped response builder (used by /procesar and simulator).

Pure shaping: normalized rows -> display items -> display dedup ->
grouped ``errores`` payload. Disk caching (export_store) stays in the
routes; this module never touches the filesystem.
"""

from __future__ import annotations

import logging
from itertools import groupby
from typing import Any

from app.services.procesar_dedup import dedup_procesar_items

logger = logging.getLogger(__name__)

#: Live detail keys forwarded dynamically from normalized_rows.
#: Engine/DB-driven values (detalle_a/b_campo, grupo_error, prioridad,
#: severidad, estancia_*) travel here when present; "" fallback otherwise
#: so future DB details are never dropped by a fixed allow-list.
LIVE_DETAIL_DEFAULTS: dict[str, object] = {
    "estancia_str": "",
    "estancia_horas": "",
    "detalle_a_campo": "",
    "detalle_b_campo": "",
    "grupo_error": "",
    "prioridad": "",
    "severidad": "",
}

#: Display cap per tipo_error group (same as /procesar).
MAX_POR_TIPO = 50

#: Column headers shown in the /procesar table.
COLUMNAS_PROCESAR: list[str] = [
    "Fec. Factura",
    "Tipo de error",
    "Número Factura",
    "Regla",
    "Responsable Cierra",
    "Descripción",
    "Procedimiento",
    "Detalle",
]


def build_display_items(normalized_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map normalized rows to /procesar display items (live details included)."""
    all_items = []
    for row in normalized_rows:
        item = {
            "tipo_error": row.get("tipo_error", ""),
            "tipo_factura": row.get("tipo_factura", "Sin tipo"),
            "factura": row.get("factura", ""),
            "fec_factura": row.get("fec_factura", ""),
            "responsable_cierra": row.get("responsable_cierra", ""),
            "descripcion": row.get("descripcion", ""),
            "procedimiento": row.get("procedimiento", ""),
            "detalle": row.get("detalle", ""),
            "fecha_cierre_vacia": row.get("fecha_cierre_vacia", False),
            "regla": row.get("regla", ""),
        }
        for live_key, live_default in LIVE_DETAIL_DEFAULTS.items():
            live_value = row.get(live_key, live_default)
            item[live_key] = live_default if live_value is None else live_value
        all_items.append(item)

    estancia_forwarded = sum(1 for item in all_items if item.get("estancia_str"))
    logger.info(
        "Procesar live details forwarded: %d/%d with estancia",
        estancia_forwarded,
        len(all_items),
    )
    return all_items


def build_procesar_response_data(
    *,
    normalized_rows: list[dict[str, Any]],
    problemas_data: dict[str, Any],
    tipos_procesados_fallback: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build the /procesar JSON payload (without ``export_id``).

    Applies the same display-only dedup (1 row per factura+tipo_error,
    lowest prioridad wins) and groups by tipo_factura/tipo_error with
    ``MAX_POR_TIPO`` items per group.

    Returns:
        (response_data, deduped_items) — the caller persists ``deduped_items``
        in export_store and adds ``export_id`` to ``response_data``.
    """
    all_items = build_display_items(normalized_rows)

    # Dedup display-only: 1 fila por (factura, grupo_error), gana menor
    # prioridad. Excel/evidencia/auditoría intactos (normalized_rows previo).
    deduped_items = dedup_procesar_items(all_items)
    logger.info(
        "Procesar display dedup: %d -> %d filas", len(all_items), len(deduped_items)
    )

    sorted_by_factura = sorted(
        deduped_items, key=lambda r: (r["tipo_factura"], r["tipo_error"])
    )
    errores = []
    for tipo_factura, factura_group in groupby(
        sorted_by_factura, key=lambda r: r["tipo_factura"]
    ):
        factura_items = list(factura_group)
        tipos = []
        total_factura = 0
        for tipo_error, error_group in groupby(
            factura_items, key=lambda r: r["tipo_error"]
        ):
            items = list(error_group)
            tipos.append({
                "tipo": tipo_error,
                "tipo_key": "norm_" + tipo_error.lower().replace(" ", "_"),
                "cantidad": len(items),
                "cantidad_mostradas": min(len(items), MAX_POR_TIPO),
                "facturas": items[:MAX_POR_TIPO],
            })
            total_factura += len(items)
        errores.append({
            "tipo_factura": tipo_factura,
            "total": total_factura,
            "tipos": tipos,
        })

    response_data: dict[str, Any] = {
        "errores": errores,
        "total_errores": sum(
            sum(t["cantidad"] for t in f["tipos"]) for f in errores
        ),
        "tipos_procesados": problemas_data.get(
            "tipos_procesados",
            tipos_procesados_fallback or [],
        ),
        "columnas": list(COLUMNAS_PROCESAR),
    }
    return response_data, deduped_items
