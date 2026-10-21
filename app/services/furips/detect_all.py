"""Orquestador de detección de problemas para FURIPS (reclamaciones SOAT).

Solo-engine, sin detectores legacy. Sin persistencia (S3 furips-fuente):
no escribe evidencias ni auditoría aunque el flag global esté activo.
Sin transversales: los campos FURIPS colisionarían con reglas de otras
fuentes (una transversal leyendo invoice.codigo mordería la columna 38).
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_FURIPS
from app.services.normalized_rows import build_normalized_rows

# FURIPS nunca persiste: decisión de diseño, no flag global.
_PERSIST = False
logger = logging.getLogger(__name__)


def detect_all_problems_furips(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    rows: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Detecta TODOS los problemas en un Excel FURIPS.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas (claves cNN_* + alias numero_factura)
        rows: RowStore precargado (fast path)

    Returns:
        (resultado_dict, responsables_map vacío)
    """
    from app.database import get_session
    from app.services.engine.domain_detection import (
        collect_field_warnings,
        detect_domain_rules,
        group_by_grupo,
    )

    batches: list = []
    grupos: dict = {}
    reglas_sin_datos: list = []
    session = get_session()
    try:
        batches = detect_domain_rules(
            session, AREA_FURIPS, data_sheet, indices,
            persist=_PERSIST, rows=rows,
            include_transversal=False,
        )
        grupos = group_by_grupo(batches)
        reglas_sin_datos = collect_field_warnings(batches)
    finally:
        session.close()

    normalized_rows = build_normalized_rows(
        error_groups=dict(grupos),
        responsables_map={},
        fec_factura_map={},
        fecha_cierre_vacia_map={},
    )

    resultado: dict[str, Any] = {
        "area": AREA_FURIPS,
        "problemas": {
            "normalizados": normalized_rows,
        },
        "totales": {
            "normalizados": len(normalized_rows),
        },
        "missing_columns": [],
        "reglas_sin_datos": reglas_sin_datos,
    }
    return resultado, {}
