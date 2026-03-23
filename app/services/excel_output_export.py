from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.services.excel_column_headers import ALLOWED_EXCEL_SUFFIXES
from app.utils.input_data import (
    resolve_safe_excel_in_input,
    resolve_safe_excel_in_output,
)

logger = logging.getLogger(__name__)

CRUCE_FACTURAS_SHEET = "CruceFacturas"


def _validate_input_path(path: Path) -> str | None:
    if not path.is_file():
        return f"Archivo no encontrado: {path.name}"
    if path.suffix.lower() not in ALLOWED_EXCEL_SUFFIXES:
        return f"Formato no soportado: {path.suffix.lower()}"
    return None


def _get_or_create_sheet(workbook: Workbook, title: str) -> Worksheet:
    if title in workbook.sheetnames:
        return workbook[title]
    return workbook.create_sheet(title=title)


def _apply_cruce_facturas_headers(workbook: Workbook) -> dict[str, Any]:
    sheet = _get_or_create_sheet(workbook, CRUCE_FACTURAS_SHEET)
    headers = {
        "B1": "Facturas Ok",
        "D1": "Facturas Pendientes",
        "F1": "PDFs de Facturas",
    }
    for cell, value in headers.items():
        sheet[cell] = value
    return {"rule": "cruce_facturas_headers", "sheet": CRUCE_FACTURAS_SHEET, "cells": headers}


def _apply_rules(workbook: Workbook) -> list[dict[str, Any]]:
    rules = [_apply_cruce_facturas_headers]
    applied: list[dict[str, Any]] = []
    for rule in rules:
        applied.append(rule(workbook))
    return applied


def export_excel_with_cruce_facturas(*, filename: str) -> dict[str, Any]:
    logger.info("Iniciando exportación a output: %s", filename)
    source_path, source_error = resolve_safe_excel_in_input(filename)
    if source_error:
        return {"status": "error", "data": {}, "errors": [source_error]}
    assert source_path is not None

    validation_error = _validate_input_path(source_path)
    if validation_error:
        return {"status": "error", "data": {}, "errors": [validation_error]}

    output_path, output_error = resolve_safe_excel_in_output(source_path.name)
    if output_error:
        return {"status": "error", "data": {}, "errors": [output_error]}
    assert output_path is not None

    try:
        shutil.copy2(source_path, output_path)
        workbook = load_workbook(output_path)
        applied_rules = _apply_rules(workbook)
        workbook.save(output_path)
    except Exception as exc:
        logger.exception("Error exportando Excel a output")
        return {"status": "error", "data": {}, "errors": [str(exc)]}

    logger.info("Exportación completada: %s", output_path.name)
    return {
        "status": "success",
        "data": {
            "input_file": source_path.name,
            "output_file": output_path.name,
            "output_path": str(output_path),
            "sheet": CRUCE_FACTURAS_SHEET,
            "headers_written": ["B1", "D1", "F1"],
            "applied_rules": applied_rules,
        },
        "errors": [],
    }
