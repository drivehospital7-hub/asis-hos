"""Reglas transversales aplicadas a todas las áreas."""

from app.services.transversales.tipo_documento_edad import detect_tipo_documento_edad
from app.services.transversales.decimales import detect_decimales

__all__ = [
    "detect_tipo_documento_edad",
    "detect_decimales",
]