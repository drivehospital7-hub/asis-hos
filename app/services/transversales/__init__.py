"""Reglas transversales aplicadas a todas las áreas."""

from app.services.transversales.tipo_documento_edad import detect_tipo_documento_edad
from app.services.transversales.decimales import detect_decimales
from app.services.transversales.estructura_excel import detectar_estructura_excel, get_filas_a_eliminar
from app.services.transversales.codigo_entidad import (
    detect_codigo_entidad_vs_entidad_afiliacion,
    detect_codigo_entidad_vs_entidad_afiliacion_simple,
)
from app.services.transversales.tipo_usuario import detect_tipo_usuario
from app.services.transversales.column_indices import get_column_indices
from app.services.transversales.doble_tipo_procedimiento import detect_doble_tipo_procedimiento
from app.services.transversales.ruta_duplicada import detect_ruta_duplicada
from app.services.transversales.cantidades_anomalas import detect_cantidades_anomalas
from app.services.transversales.tipo_identificacion_entidad import detect_tipo_identificacion_entidad
from app.services.transversales.normalize import normalize_invoice, normalize_header
from app.services.transversales.detect_copago_entidad import detect_copago_entidad_urgencias
from app.services.transversales.procedimiento_contratado import detect_cups_sin_contrato

__all__ = [
    "detect_tipo_documento_edad",
    "detect_decimales",
    "detectar_estructura_excel",
    "get_filas_a_eliminar",
    "detect_codigo_entidad_vs_entidad_afiliacion",
    "detect_codigo_entidad_vs_entidad_afiliacion_simple",
    "detect_tipo_usuario",
    "get_column_indices",
    "detect_doble_tipo_procedimiento",
    "detect_ruta_duplicada",
    "detect_cantidades_anomalas",
    "detect_tipo_identificacion_entidad",
    "normalize_invoice",
    "normalize_header",
    "detect_copago_entidad_urgencias",
    "detect_cups_sin_contrato",
]