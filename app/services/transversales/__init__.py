"""Reglas transversales aplicadas a todas las áreas."""

from app.services.transversales.estructura_excel import detectar_estructura_excel, get_filas_a_eliminar
from app.services.transversales.tipo_usuario import detect_tipo_usuario
from app.services.transversales.column_indices import get_column_indices
from app.services.transversales.normalize import normalize_invoice, normalize_header

__all__ = [
    "detectar_estructura_excel",
    "get_filas_a_eliminar",
    "detect_tipo_usuario",
    "get_column_indices",
    "normalize_invoice",
    "normalize_header",
]