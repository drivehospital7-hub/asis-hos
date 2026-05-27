"""Módulos de detección específicos de Intramural.

Actualmente solo usa detectores transversales — sin reglas de negocio propias.
"""

from app.services.intramural.detect_all import detect_all_problems_intramural
from app.services.intramural.ide_contrato_intramural import (
    detect_ide_contrato_intramural,
)

__all__ = [
    "detect_all_problems_intramural",
    "detect_ide_contrato_intramural",
]
