"""Mapeo de nombres de columna a índices.

Extraído de revision_sheet.py._get_column_indices.
Función parametrizada que acepta cualquier conjunto de headers requeridos.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_column_indices(
    headers: list[Any],
    required_headers: dict[str, str],
) -> tuple[dict[str, int | None], list[str]]:
    """
    Mapea nombres de columna a sus índices (0-based).

    REQUIERE COINCIDENCIA EXACTA - NO infiere nombres similares.
    Si una columna no coincide exactamente, retorna None y la reporta en la lista de errores.

    Args:
        headers: Lista de nombres de columna del Excel.
        required_headers: Diccionario {clave_interna: nombre_exacto_en_excel}.

    Returns:
        Tuple de (dict con clave_interna -> índice 0-based o None,
                  lista de nombres EXACTOS no encontrados).
    """
    indices: dict[str, int | None] = {k: None for k in required_headers}

    # Normalizar headers del Excel para comparación EXACTA
    excel_headers_normalized: dict[str, int] = {}
    for i, header in enumerate(headers):
        if header is not None:
            normalized = str(header).strip()
            excel_headers_normalized[normalized] = i

    # Buscar coincidencia EXACTA para cada columna requerida
    missing_columns: list[str] = []
    for key, required_name in required_headers.items():
        if required_name in excel_headers_normalized:
            indices[key] = excel_headers_normalized[required_name]
            logger.info(
                "COLUMNA MAPEADA: '%s' -> clave '%s' (índice %d)",
                required_name,
                key,
                excel_headers_normalized[required_name],
            )
        else:
            missing_columns.append(required_name)
            logger.warning(
                "COLUMNA FALTANTE: '%s' (clave '%s')", required_name, key
            )

    found_columns = [k for k, v in indices.items() if v is not None]
    if missing_columns:
        logger.error(
            "Columnas FALTANTES (no hay coincidencia exacta): %s",
            missing_columns,
        )

    logger.info(
        "Indices detectados (coincidencia exacta): %d/%d",
        len(found_columns),
        len(indices),
    )

    return indices, missing_columns
