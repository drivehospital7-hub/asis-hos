"""Módulos de detección específicos de Intramural.

Actualmente solo usa detectores transversales — sin reglas de negocio propias.
"""

from app.services.intramural.detect_all import detect_all_problems_intramural

__all__ = [
    "detect_all_problems_intramural",
]
