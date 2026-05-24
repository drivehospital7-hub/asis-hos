"""Mapeo de nombres de columna a índices.

Extraído de revision_sheet.py._get_column_indices.
Función parametrizada que acepta cualquier conjunto de headers requeridos.
"""

from __future__ import annotations

import logging
import unicodedata
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

    # Normalizar headers del Excel: NFC + limpiar espacios no separables
    excel_headers_normalized: dict[str, int] = {}
    for i, header in enumerate(headers):
        if header is not None:
            normalized = (
                unicodedata.normalize("NFC", str(header))
                .strip()
                .replace("\u00a0", " ")
            )
            excel_headers_normalized[normalized] = i

    # Buscar coincidencia EXACTA (con normalización NFC en ambos lados)
    missing_columns: list[str] = []
    for key, required_name in required_headers.items():
        required_norm = (
            unicodedata.normalize("NFC", required_name)
            .strip()
            .replace("\u00a0", " ")
        )
        if required_norm in excel_headers_normalized:
            indices[key] = excel_headers_normalized[required_norm]
            logger.info(
                "COLUMNA MAPEADA: '%s' -> clave '%s' (índice %d)",
                required_name,
                key,
                excel_headers_normalized[required_norm],
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
