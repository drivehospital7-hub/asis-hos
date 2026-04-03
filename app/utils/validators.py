"""Validadores para archivos Excel."""

from __future__ import annotations

from pathlib import Path

from app.constants import ALLOWED_EXCEL_SUFFIXES


def validate_excel_path(path: Path) -> str | None:
    """
    Valida que el path sea un archivo Excel válido.
    
    Returns:
        None si es válido, mensaje de error si no.
    """
    if not path.is_file():
        return f"Archivo no encontrado: {path.name}"
    if path.suffix.lower() not in ALLOWED_EXCEL_SUFFIXES:
        return f"Formato no soportado: {path.suffix.lower()}"
    return None
