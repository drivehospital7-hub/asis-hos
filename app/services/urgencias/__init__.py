"""Módulos de detección específicos de Urgencias / Hospitalización."""

from app.services.urgencias.cantidades_urgencias import detect_cantidades_urgencias
from app.services.urgencias.cantidades_soat_urgencias import (
    detect_cantidades_soat_urgencias,
)
from app.services.urgencias.cantidades_soat_hospitalizacion import (
    detect_cantidades_soat_hospitalizacion,
)
from app.services.urgencias.hospitalizacion import detect_cantidades_hospitalizacion

__all__ = [
    "detect_cantidades_urgencias",
    "detect_cantidades_soat_urgencias",
    "detect_cantidades_soat_hospitalizacion",
    "detect_cantidades_hospitalizacion",
]
