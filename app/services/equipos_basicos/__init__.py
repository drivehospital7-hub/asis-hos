"""Módulos de detección específicos de Equipos Básicos."""

from app.services.equipos_basicos.profesionales import detect_profesionales_equipos_basicos
from app.services.equipos_basicos.detect_all import detect_all_problems_equipos_basicos

__all__ = [
    "detect_profesionales_equipos_basicos",
    "detect_all_problems_equipos_basicos",
]
