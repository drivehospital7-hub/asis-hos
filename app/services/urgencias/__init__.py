"""Módulos de detección específicos de Urgencias / Hospitalización."""

from app.services.urgencias.cantidades_urgencias import detect_cantidades_urgencias
from app.services.urgencias.cantidades_soat_urgencias import (
    detect_cantidades_soat_urgencias,
)
from app.services.urgencias.cantidades_soat_hospitalizacion import (
    detect_cantidades_soat_hospitalizacion,
)
from app.services.urgencias.centro_costo_urgencias import detect_centro_costo_urgencias
from app.services.urgencias.cups_equivalentes import detect_cups_equivalentes
from app.services.urgencias.hospitalizacion import (
    detect_cantidades_hospitalizacion,
    detect_hospitalizacion_codes,
)
from app.services.urgencias.ide_contrato_urgencias import detect_ide_contrato_urgencias
from app.services.urgencias.sala_observacion import detect_sala_observacion

__all__ = [
    "detect_cantidades_urgencias",
    "detect_cantidades_soat_urgencias",
    "detect_cantidades_soat_hospitalizacion",
    "detect_cantidades_hospitalizacion",
    "detect_centro_costo_urgencias",
    "detect_cups_equivalentes",
    "detect_hospitalizacion_codes",
    "detect_ide_contrato_urgencias",
    "detect_sala_observacion",
]
