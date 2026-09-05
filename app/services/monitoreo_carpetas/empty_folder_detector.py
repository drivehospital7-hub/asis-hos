"""Detección de carpetas vacías (sin archivos de facturas válidos).

Una carpeta se considera "vacía" si no contiene ningún archivo con
extensiones de factura (.pdf, .PDF) o si solo contiene archivos no
relacionados con facturación (.txt, .log, .csv, etc.).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Extensiones consideradas como archivos de factura
_INVOICE_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".PDF"})


def detect_empty(
    facturador: str,
    folder_path: str,
    files_in_folder: list[str],
) -> list[dict[str, str]]:
    """Detecta si una carpeta de facturador está vacía o sin facturas.

    Revisa si la lista de archivos contiene algún archivo con extensión
    de factura. Si no hay ninguno, la carpeta se reporta como vacía.

    Args:
        facturador: Nombre del facturador.
        folder_path: Ruta completa de la carpeta.
        files_in_folder: Lista de nombres de archivo en la carpeta.

    Returns:
        Lista de dicts con facturador, folder y reason.
        Vacía si la carpeta tiene archivos de factura.
    """
    has_invoice = any(
        fname.endswith(tuple(_INVOICE_EXTENSIONS))
        for fname in files_in_folder
    )

    if has_invoice:
        return []

    return [
        {
            "facturador": facturador,
            "folder": folder_path,
            "reason": "empty",
        }
    ]
