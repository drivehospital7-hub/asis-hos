from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import polars as pl

logger = logging.getLogger(__name__)

ALLOWED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})


def get_excel_column_headers(
    file_path: str | Path,
    *,
    sheet_name: str | None = None,
    sheet_id: int | None = None,
    header_row: int = 0,
) -> dict[str, Any]:
    """
    Lee solo la fila de cabecera del Excel (motor calamine / fastexcel).
    No escribe el archivo; `n_rows=0` evita cargar filas de datos.
    """
    path = Path(file_path).expanduser().resolve()
    logger.info("Leyendo cabeceras Excel: %s", path.name)

    if sheet_name is not None and sheet_id is not None:
        return {
            "status": "error",
            "data": {},
            "errors": ["Indica solo uno: sheet_name o sheet_id."],
        }

    if not path.is_file():
        return {
            "status": "error",
            "data": {},
            "errors": [f"Archivo no encontrado: {path}"],
        }

    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        return {
            "status": "error",
            "data": {},
            "errors": [f"Formato no soportado: {suffix}"],
        }

    read_opts: dict[str, Any] = {"n_rows": 0, "header_row": header_row}
    read_kwargs: dict[str, Any] = {
        "source": str(path),
        "engine": "calamine",
        "read_options": read_opts,
        "infer_schema_length": 0,
        "drop_empty_rows": False,
        "drop_empty_cols": False,
        "raise_if_empty": False,
    }
    if sheet_name is not None:
        read_kwargs["sheet_name"] = sheet_name
    elif sheet_id is not None:
        read_kwargs["sheet_id"] = sheet_id

    try:
        df = pl.read_excel(**read_kwargs)
    except Exception as exc:
        logger.exception("Error al leer Excel")
        return {
            "status": "error",
            "data": {},
            "errors": [str(exc)],
        }

    if df.width == 0:
        return {
            "status": "error",
            "data": {},
            "errors": ["La hoja no tiene columnas reconocibles."],
        }

    columns: list[str] = []
    for name in df.columns:
        if isinstance(name, str):
            columns.append(name.strip())
        else:
            columns.append(str(name).strip())

    data: dict[str, Any] = {
        "columns": columns,
        "header_row": header_row,
    }
    if sheet_name is not None:
        data["sheet"] = sheet_name
    elif sheet_id is not None:
        data["sheet_id"] = sheet_id

    logger.info(
        "Cabeceras leídas: %d columnas (fila encabezado índice %d)",
        len(columns),
        header_row,
    )
    return {"status": "success", "data": data, "errors": []}
