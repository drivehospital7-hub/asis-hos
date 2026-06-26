"""Orquestador de detección para Monitoreo de Carpetas.

Coordina el escaneo de carpetas, validación de nombres, detección de
duplicados y carpetas vacías, y retorna un ScanResult completo.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.duplicate_detector import find_duplicates
from app.services.monitoreo_carpetas.folder_scanner import scan_all

logger = logging.getLogger(__name__)


def detect_all(root_paths: list[str]) -> ScanResult:
    """Ejecuta el pipeline completo de detección.

    Args:
        root_paths: Lista de rutas de directorios raíz a escanear.

    Returns:
        ScanResult con todas las facturas, duplicados, vacías, errores
        e indicadores agregados.
    """
    # Step 1: Scan folders
    scan_result = scan_all(root_paths)

    # Step 2: Group invoices by facturador for duplicate detection
    invoices_by_facturador: dict[str, list[InvoiceRecord]] = defaultdict(list)
    for inv in scan_result.facturas:
        invoices_by_facturador[inv.facturador].append(inv)

    # Step 3: Detect duplicates
    duplicados = find_duplicates(dict(invoices_by_facturador))

    # Step 4: Calculate enhanced indicators
    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for inv in scan_result.facturas:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1
        type_counts[inv.invoice_type] = type_counts.get(inv.invoice_type, 0) + 1

    indicadores: dict[str, int | float] = {
        "total_facturas": len(scan_result.facturas),
        "total_facturadores": len(invoices_by_facturador),
        "total_vacias": len(scan_result.vacias),
        "total_duplicados": len(duplicados),
        "total_errores": len(scan_result.errores_scan),
        **{f"status_{k}": v for k, v in status_counts.items()},
        **{f"type_{k}": v for k, v in type_counts.items()},
    }

    return ScanResult(
        facturas=scan_result.facturas,
        indicadores=indicadores,
        duplicados=duplicados,
        vacias=scan_result.vacias,
        errores_scan=scan_result.errores_scan,
        excel_path=None,
    )
