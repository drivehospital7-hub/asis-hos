"""Detector de duplicados en facturas tipo Farmacia.

Thin wrapper que delega en :func:`detect_duplicados_generico` con
``tipo_factura="Farmacia"``. Sin filtros de tarifario ni
``codigo_tipo_procedimiento``.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.services.transversales.detect_duplicados_base import detect_duplicados_generico

logger = logging.getLogger(__name__)


def detect_duplicados_farmacia_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta duplicados en facturas tipo Farmacia.

    Agrupa por factura. Si todos los pares (codigo, cantidad) aparecen
    al menos 2 veces, la factura completa se marca. Sin filtros de
    tarifario ni ``codigo_tipo_procedimiento``.

    Args:
        data_sheet: Hoja de Excel con los datos.
        indices: Índices de columnas.

    Returns:
        Lista de dicts con keys: ``factura``, ``pares_duplicados``,
        ``total_pares``. (No incluye ``codigo_tipo_procedimiento``)
    """
    logger.debug("detect_duplicados_farmacia_farmacia delegando a detect_duplicados_generico")
    return detect_duplicados_generico(
        data_sheet, indices,
        tipo_factura="Farmacia",
    )
