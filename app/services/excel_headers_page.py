"""Contexto para la vista HTML de encabezados Excel en `data/input`."""

from __future__ import annotations

from typing import Any

from app.services.excel_column_headers import get_excel_column_headers
from app.utils.input_data import list_excel_filenames, resolve_safe_excel_in_input


def _parse_header_row(value: str | None) -> tuple[int | None, str | None]:
    if value is None or str(value).strip() == "":
        return 0, None
    try:
        row = int(str(value).strip())
    except ValueError:
        return None, "Fila de encabezado debe ser un número entero."
    if row < 0:
        return None, "Fila de encabezado no puede ser negativa."
    return row, None


def _parse_sheet_id(value: str | None) -> tuple[int | None, str | None]:
    if value is None or str(value).strip() == "":
        return None, None
    try:
        return int(str(value).strip()), None
    except ValueError:
        return None, "sheet_id debe ser un número entero."


def build_excel_headers_view_context(
    *,
    file: str,
    sheet_name: str | None,
    sheet_id_raw: str | None,
    header_row_raw: str | None,
) -> dict[str, Any]:
    """
    Datos para la plantilla: archivos disponibles, valores del formulario y
    resultado de lectura de cabeceras (o None si no hubo búsqueda).
    """
    available_files = list_excel_filenames()
    sheet_name_clean = (sheet_name or "").strip() or None
    sheet_id, sheet_id_err = _parse_sheet_id(sheet_id_raw)
    header_row, header_err = _parse_header_row(header_row_raw)

    if sheet_id_err:
        return {
            "available_files": available_files,
            "form": {
                "file": file.strip(),
                "sheet_name": sheet_name or "",
                "sheet_id": sheet_id_raw or "",
                "header_row": header_row_raw or "0",
            },
            "result": {
                "status": "error",
                "data": {},
                "errors": [sheet_id_err],
            },
        }

    if header_err:
        return {
            "available_files": available_files,
            "form": {
                "file": file.strip(),
                "sheet_name": sheet_name or "",
                "sheet_id": sheet_id_raw or "",
                "header_row": header_row_raw or "",
            },
            "result": {
                "status": "error",
                "data": {},
                "errors": [header_err],
            },
        }

    assert header_row is not None

    if not file.strip():
        return {
            "available_files": available_files,
            "form": {
                "file": "",
                "sheet_name": sheet_name or "",
                "sheet_id": sheet_id_raw or "",
                "header_row": str(header_row),
            },
            "result": None,
        }

    path, resolve_error = resolve_safe_excel_in_input(file)
    if resolve_error:
        return {
            "available_files": available_files,
            "form": {
                "file": file.strip(),
                "sheet_name": sheet_name or "",
                "sheet_id": sheet_id_raw or "",
                "header_row": str(header_row),
            },
            "result": {
                "status": "error",
                "data": {},
                "errors": [resolve_error],
            },
        }

    assert path is not None
    result = get_excel_column_headers(
        path,
        sheet_name=sheet_name_clean,
        sheet_id=sheet_id,
        header_row=header_row,
    )
    return {
        "available_files": available_files,
        "form": {
            "file": file.strip(),
            "sheet_name": sheet_name or "",
            "sheet_id": sheet_id_raw or "",
            "header_row": str(header_row),
        },
        "result": result,
    }
