"""Export de Control de Errores a Excel (.xlsx) en memoria."""

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from app.utils.errores_storage import listar_imagenes

logger = logging.getLogger(__name__)

HEADERS = [
    "Validador",
    "Factura",
    "Creado",
    "Categoría",
    "Descripción",
    "Responsable",
    "Observación del Facturador",
    "Estado",
    "Adjunto 1",
    "Adjunto 2",
    "Adjunto 3",
]

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

COLUMN_WIDTHS = [20, 16, 12, 16, 50, 25, 30, 12, 40, 40, 40]

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb"}


def filename_export(mes: str | None) -> str:
    """Deriva el nombre del archivo de exportación desde ``mes`` (YYYY-MM).

    Si ``mes`` falta o no es válido, usa la fecha actual.
    """
    if mes and len(mes) == 7 and mes[:4].isdigit() and mes[5:7].isdigit():
        try:
            month_name = MESES[int(mes[5:7]) - 1]
        except IndexError:
            month_name = MESES[datetime.now().month - 1]
        year = mes[:4]
    else:
        now = datetime.now()
        month_name = MESES[now.month - 1]
        year = str(now.year)
    return f"control-errores-{month_name}-{year}.xlsx"


def _formatear_fecha(creado_en: str | None) -> str:
    """Formatea ``creado_en`` ISO como dd/mm/yyyy; si falla, devuelve el raw."""
    try:
        return datetime.fromisoformat(creado_en).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return creado_en or ""


def _label_adjunto(filename: str) -> str:
    """Etiqueta amigable para un adjunto según su extensión."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return "Abrir PDF"
    if ext in EXCEL_EXTENSIONS:
        return "Abrir Excel"
    return "Abrir imagen"


def _adjunto_url(base_url: str, error_id: str, filename: str) -> str:
    """URL absoluta para descargar un adjunto sin token ni sesión.

    La ruta de servicio es pública a propósito: los links del Excel deben
    seguir abriendo indefinidamente. El error_id (UUID) hace la URL difícil
    de adivinar y la ruta valida que el archivo pertenezca al registro.
    """
    return f"{base_url}api/control-errores/{error_id}/imagenes/{quote(filename)}"


def build_errores_export_workbook(errores: list[dict], base_url: str) -> BytesIO:
    """Construye un workbook .xlsx en memoria con los errores dados."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Novedades"

    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for idx, width in enumerate(COLUMN_WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    for error in errores:
        error_id = error.get("id", "")
        ws.append([
            error.get("validador", ""),
            error.get("factura", ""),
            _formatear_fecha(error.get("creado_en", "")),
            error.get("tipo_error", ""),
            error.get("observacion", ""),
            error.get("responsable", ""),
            error.get("observacion_facturador", ""),
            _label_estado(error.get("estado", "")),
        ])

        row_idx = ws.max_row
        adjuntos = listar_imagenes(error_id)
        for i in range(3):
            cell = ws.cell(row=row_idx, column=9 + i)
            if i < len(adjuntos):
                filename = adjuntos[i]
                cell.value = _label_adjunto(filename)
                cell.hyperlink = _adjunto_url(base_url, error_id, filename)
                cell.style = "Hyperlink"
                cell.alignment = Alignment(wrap_text=True)
            else:
                cell.value = ""

        for col in (5, 9, 10, 11):
            ws.cell(row=row_idx, column=col).alignment = Alignment(wrap_text=True)

    ws.freeze_panes = "A2"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _label_estado(estado: str) -> str:
    """Traduce el código de estado a etiqueta legible."""
    if estado == "S":
        return "Pendiente"
    if estado == "N":
        return "Resuelto"
    return estado