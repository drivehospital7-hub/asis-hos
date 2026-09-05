"""Módulos de detección específicos de Odontología."""

from app.services.odontologia.profesionales import detect_profesionales_odontologia
from app.services.odontologia.centro_costo import detect_centro_costo_odontologia
from app.services.odontologia.ide_contrato import detect_ide_contrato_odontologia
from app.services.odontologia.detect_all import detect_all_problems_odontologia

__all__ = [
    "detect_profesionales_odontologia",
    "detect_centro_costo_odontologia",
    "detect_ide_contrato_odontologia",
    "detect_all_problems_odontologia",
]
