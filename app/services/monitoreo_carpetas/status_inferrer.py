"""Inferencia de estado de carpeta basada en nombre del folder padre.

Busca keywords configuradas en el nombre del folder para determinar
si las facturas están Verificadas, Por corregir, o En revisión.
"""

from __future__ import annotations

import logging

from app.constants.monitoreo_carpetas import (
    STATUS_EN_REVISION,
    STATUS_KEYWORDS,
)

logger = logging.getLogger(__name__)


def infer_status(folder_name: str) -> str:
    """Infiere el estado de una carpeta basado en keywords en su nombre.

    La función itera sobre STATUS_KEYWORDS buscando coincidencias
    case-insensitive. Si encuentra una keyword, retorna el status
    correspondiente. Si no encuentra ninguna, retorna STATUS_EN_REVISION.

    Args:
        folder_name: Nombre del folder padre del facturador.

    Returns:
        "Verificada", "Por corregir", o "En revisión".
    """
    if not folder_name:
        return STATUS_EN_REVISION

    folder_upper = folder_name.upper()

    for status, keywords in STATUS_KEYWORDS.items():
        if status == STATUS_EN_REVISION:
            continue  # default fallback
        for keyword in keywords:
            if keyword.upper() in folder_upper:
                return status

    return STATUS_EN_REVISION
