"""Lee el Excel de producción para el cruce vs carpetas.

Producción = mismo archivo que /procesar: columnas `Número Factura`
+ `Responsable Cierra Facturar`. Solo lectura, sin lógica de negocio.

Igual que /procesar (exporter.py), los headers pueden venir con filas de
título encima: se auto-detecta la fila de encabezados por best-match en
las primeras 5 filas.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from openpyxl import load_workbook

from app.services.transversales.column_indices import get_column_indices

logger = logging.getLogger(__name__)

REQUIRED_HEADERS: dict[str, str] = {
    "numero_factura": "Número Factura",
    "responsable": "Responsable Cierra Facturar",
    "fec_factura": "Fec. Factura",
}

MAX_HEADER_SCAN_ROWS = 5
"""Filas iniciales a escanear buscando los encabezados (igual que /procesar)."""


def _clean(value: Any) -> str | None:
    """Normaliza una celda a str con strip; None/vacío -> None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_fecha(value: Any) -> str | None:
    """Normaliza la fecha de factura a ISO; date/datetime -> isoformat."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return _clean(value)


def _detect_header_row(ws: Any) -> tuple[int, dict[str, int | None], list[str]]:
    """Detecta la fila de headers por best-match (mayor coincidencia).

    Escanea las primeras MAX_HEADER_SCAN_ROWS filas y se queda con la de
    mayor coincidencia con los headers requeridos. Empates → primera fila.

    Returns:
        (header_row_1based, indices, missing).
    """
    best_row = 1
    best_indices: dict[str, int | None] = {k: None for k in REQUIRED_HEADERS}
    best_missing: list[str] = list(REQUIRED_HEADERS.values())
    best_score = -1
    for row_num, row in enumerate(
        ws.iter_rows(min_row=1, max_row=MAX_HEADER_SCAN_ROWS, values_only=True),
        start=1,
    ):
        indices, missing = get_column_indices(list(row), REQUIRED_HEADERS)
        score = len(REQUIRED_HEADERS) - len(missing)
        if score > best_score:
            best_score = score
            best_row = row_num
            best_indices = indices
            best_missing = missing
    logger.info(
        "Headers best-match en fila %d (%d/%d coincidencias)",
        best_row, best_score, len(REQUIRED_HEADERS),
    )
    return best_row, best_indices, best_missing


def _read_rows(
    ws: Any, header_row: int, indices: dict[str, int | None]
) -> list[dict[str, str | None]]:
    """Lee filas debajo del header como dicts numero_factura/responsable/fec.

    Saltea filas totalmente vacías (colas de formato del Excel) para que
    no inflen producción ni caigan en Revisar en blanco.
    """
    idx_fact = indices["numero_factura"]
    idx_resp = indices["responsable"]
    idx_fec = indices["fec_factura"]
    assert idx_fact is not None and idx_resp is not None and idx_fec is not None
    rows: list[dict[str, str | None]] = []
    for excel_row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        numero = _clean(excel_row[idx_fact])
        responsable = _clean(excel_row[idx_resp])
        fec_factura = _clean_fecha(excel_row[idx_fec])
        if numero is None and responsable is None and fec_factura is None:
            continue
        rows.append({"numero_factura": numero, "responsable": responsable, "fec_factura": fec_factura})
    return rows


def read_produccion(path: str | Any) -> tuple[list[dict[str, str | None]], list[str]]:
    """Abre el Excel de producción en modo read-only.

    Returns:
        (rows, missing): rows = [{"numero_factura", "responsable",
        "fec_factura"}];
        missing = headers exactos no encontrados (para error envelope).
    """
    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        ws = wb.active
        header_row, indices, missing = _detect_header_row(ws)
        if missing:
            logger.warning("Producción con columnas faltantes: %s", missing)
            return [], missing
        rows = _read_rows(ws, header_row, indices)
        logger.info("Producción leída: %d filas (headers en fila %d)", len(rows), header_row)
        return rows, []
    finally:
        wb.close()
