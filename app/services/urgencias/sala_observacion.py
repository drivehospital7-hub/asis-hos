"""Detector de sala de observación en Urgencias.

PENDIENTE: La lógica de sala de observación está actualmente inline en
_detect_centro_costo_urgencias (revision_sheet.py). Se extraerá en Fase 5b
cuando se module ese detector de alto riesgo (~1800 líneas).

Esta función cubre:
- Estancia en sala de observación según entidad y horas
- Códigos obligatorios (890701, 890601) cuando hay sala
- Reglas SOAT de sala de observación
- Códigos prohibidos por entidad
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


# TODO: Extraer en Fase 5b desde _detect_centro_costo_urgencias
def detect_sala_observacion(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """
    Detecta problemas de sala de observación en facturas de Urgencias.

    NOTA: Aún no implementado. La lógica reside en
    _detect_centro_costo_urgencias y se extraerá en Fase 5b.

    Returns:
        Lista vacía hasta que se implemente la extracción.
    """
    logger.warning(
        "detect_sala_observacion aún no implementado - "
        "la lógica está en _detect_centro_costo_urgencias (Fase 5b)"
    )
    return []
