"""Formatted .xlsx export of cached /procesar rows (in-memory workbook).

Mirrors the control-novedades style precedent with its own HEADERS:
header 1B5E20 white-bold, zebra E8F5E9/FFFFFF, border A5D6A7 thin,
width 20, freeze A2, ``Fec. Factura`` as dd/mm/yyyy. Detection-only:
no detector, dedup or grouping logic lives here.
"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.constants.columnas import PROCESAR_CASING_MAP, PROCESAR_EXPORT_HEADERS
from app.services.transversales.normalize import normalize_invoice, normalize_text
from app.utils.formatting import to_title_case, to_upper_safe

logger = logging.getLogger(__name__)

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

COLUMN_WIDTH = 20
DATE_FORMAT = "DD/MM/YYYY"

HEADER_FILL = PatternFill("solid", fgColor="1B5E20")
HEADER_FONT = Font(bold=True, color="FFFFFF")

ROW_FILL_LIGHT = PatternFill("solid", fgColor="E8F5E9")
ROW_FILL_WHITE = PatternFill("solid", fgColor="FFFFFF")
DATA_FONT = Font(color="000000")

THIN_BORDER = Border(
    left=Side(style="thin", color="A5D6A7"),
    right=Side(style="thin", color="A5D6A7"),
    top=Side(style="thin", color="A5D6A7"),
    bottom=Side(style="thin", color="A5D6A7"),
)

#: Export header -> (deduped-row key, cell mode).
_COLUMN_MODES: dict[str, tuple[str, str]] = {
    "Fec. Factura": ("fec_factura", "date"),
    "Tipo de error": ("tipo_error", "raw"),
    "Número Factura": ("factura", "upper_invoice"),
    "Regla": ("regla", "raw"),
    "Responsable Cierra": ("responsable_cierra", "title"),
    "Descripción": ("descripcion", "upper_text"),
    "Procedimiento": ("procedimiento", "raw"),
    "Detalle": ("detalle", "upper_text"),
}

_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y")


def filename_procesar_export(now: datetime | None = None) -> str:
    """Build ``procesar-{Mon}-{YYYY}.xlsx`` for now (fallback: today)."""
    current = now or datetime.now()
    return f"procesar-{MESES[current.month - 1]}-{current.year}.xlsx"


def _sanitize_for_excel(value: Any) -> Any:
    """Prefix formula triggers (=,+,-,@) with a single quote."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _cell_fecha(value: Any) -> Any:
    """Parse to datetime when possible; otherwise raw string or empty."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return _sanitize_for_excel(text)


def _cell_text(value: Any, mode: str) -> Any:
    """Apply the per-column casing mode, null-safe."""
    if mode == "title":
        text = to_title_case(value if isinstance(value, str) else "")
    elif mode == "upper_invoice":
        text = to_upper_safe(normalize_invoice(value) or "")
    elif mode == "upper_text":
        text = to_upper_safe(normalize_text(value))
    elif value is None:
        text = ""
    else:
        text = value if isinstance(value, str) else value
    return _sanitize_for_excel(text)


def _row_cells(row: dict[str, Any]) -> list[Any]:
    """Map one deduped row to the 8 export cells in header order."""
    cells: list[Any] = []
    for header in PROCESAR_EXPORT_HEADERS:
        key, mode = _COLUMN_MODES[header]
        if mode == "date":
            cells.append(_cell_fecha(row.get(key)))
        else:
            cells.append(_cell_text(row.get(key), mode))
    return cells


def build_procesar_export_workbook(rows: list[dict[str, Any]]) -> BytesIO:
    """Build the styled .xlsx workbook for the cached full row list."""
    assert set(PROCESAR_CASING_MAP) == set(PROCESAR_EXPORT_HEADERS)
    wb = Workbook()
    ws = wb.active
    ws.title = "Procesar"

    ws.append(list(PROCESAR_EXPORT_HEADERS))
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = THIN_BORDER

    for idx in range(1, len(PROCESAR_EXPORT_HEADERS) + 1):
        ws.column_dimensions[get_column_letter(idx)].width = COLUMN_WIDTH

    for row_index, row in enumerate(rows):
        ws.append(_row_cells(row))
        excel_row = ws.max_row
        row_fill = ROW_FILL_LIGHT if row_index % 2 == 0 else ROW_FILL_WHITE
        for col in range(1, len(PROCESAR_EXPORT_HEADERS) + 1):
            cell = ws.cell(row=excel_row, column=col)
            cell.fill = row_fill
            cell.border = THIN_BORDER
            cell.font = DATA_FONT
            if col == 1 and isinstance(cell.value, datetime):
                cell.number_format = DATE_FORMAT

    ws.freeze_panes = "A2"
    logger.info("[BACK] Procesar export workbook built: %d rows", len(rows))
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
