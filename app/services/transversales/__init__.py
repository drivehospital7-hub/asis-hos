"""Reglas transversales aplicadas a todas las áreas."""

from app.services.transversales.tipo_documento_edad import detect_tipo_documento_edad
from app.services.transversales.decimales import detect_decimales
from app.services.transversales.estructura_excel import detectar_estructura_excel, get_filas_a_eliminar
from app.services.transversales.codigo_entidad import (
    detect_codigo_entidad_vs_entidad_afiliacion,
    detect_codigo_entidad_vs_entidad_afiliacion_simple,
)

__all__ = [
    "detect_tipo_documento_edad",
    "detect_decimales",
    "detectar_estructura_excel",
    "get_filas_a_eliminar",
    "detect_codigo_entidad_vs_entidad_afiliacion",
    "detect_codigo_entidad_vs_entidad_afiliacion_simple",
]