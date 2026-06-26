"""Detección de facturas duplicadas entre facturadores.

Misma factura (mismo filename) apareciendo en 2+ carpetas de
facturadores se reporta como duplicado. El detector es filename-based
(no content-based), según la especificación.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.services.monitoreo_carpetas import InvoiceRecord

logger = logging.getLogger(__name__)


def find_duplicates(
    invoices_by_facturador: dict[str, list[InvoiceRecord]],
) -> list[dict[str, str | list[str]]]:
    """Detecta archivos de factura duplicados entre facturadores.

    Agrupa facturas por filename. Si un filename aparece en más de un
    facturador, se reporta como duplicado.

    Args:
        invoices_by_facturador: Dict con facturador como key y lista de
            InvoiceRecord como value.

    Returns:
        Lista de dicts, cada uno con:
        - filename: str — nombre del archivo duplicado
        - facturadores: list[str] — facturadores donde aparece
        - paths: list[str] — rutas completas del archivo
    """
    # Build filename → [(facturador, path)] mapping
    filename_map: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for facturador, records in invoices_by_facturador.items():
        seen_in_facturador: set[str] = set()
        for rec in records:
            if rec.filename not in seen_in_facturador:
                filename_map[rec.filename].append((facturador, rec.full_path))
                seen_in_facturador.add(rec.filename)

    # Find duplicates
    duplicates: list[dict[str, str | list[str]]] = []
    for filename, locations in filename_map.items():
        if len(locations) >= 2:
            duplicates.append({
                "filename": filename,
                "facturadores": [loc[0] for loc in locations],
                "paths": [loc[1] for loc in locations],
            })

    return duplicates
