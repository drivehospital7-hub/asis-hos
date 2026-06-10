"""Detector de duplicados en facturas de farmacia para Urgencias.

Thin wrapper que delega en :func:`detect_duplicados_generico` con los
parámetros de Urgencias: ``tipo_factura="Urgencias"``,
``tarifario=VALOR_TARIFARIO_FARMACIA`` y
``codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12``.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants.urgencias import (
    CODIGOS_TIPO_PROC_09_12,
    VALOR_TARIFARIO_FARMACIA,
)
from app.services.transversales.detect_duplicados_base import detect_duplicados_generico

logger = logging.getLogger(__name__)


def detect_duplicados_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta grupos de farmacia donde todos los pares están duplicados.

    Delega en :func:`detect_duplicados_generico` con
    ``tipo_factura="Urgencias"``,
    ``tarifario_val=VALOR_TARIFARIO_FARMACIA`` y
    ``codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12``.

    Args:
        data_sheet: Hoja de Excel con los datos.
        indices: Índices de columnas.

    Returns:
        Lista de dicts con keys: ``factura``, ``codigo_tipo_procedimiento``,
        ``pares_duplicados``, ``total_pares``.
    """
    logger.debug("detect_duplicados_farmacia (Urgencias) delegando a detect_duplicados_generico")
    return detect_duplicados_generico(
        data_sheet, indices,
        tipo_factura="Urgencias",
        tarifario_val=VALOR_TARIFARIO_FARMACIA,
        codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12,
    )
