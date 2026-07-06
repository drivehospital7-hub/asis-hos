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


def recalculate_indicators(result: ScanResult) -> dict[str, int | float | str]:
    """Recalcula los indicadores agregados a partir de un ScanResult.

    Procesa facturas, vacías, duplicados y errores para producir
    métricas como totales, conteos por estado y conteos por tipo.

    Args:
        result: ScanResult con las facturas, vacías, duplicados y errores.

    Returns:
        Dict con indicadores: total_facturas, total_facturadores,
        total_vacias, total_duplicados, total_errores, status_* y type_*.
    """
    invoices_by_facturador: dict[str, list[InvoiceRecord]] = defaultdict(list)
    for inv in result.facturas:
        invoices_by_facturador[inv.facturador].append(inv)

    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for inv in result.facturas:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1
        type_counts[inv.invoice_type] = type_counts.get(inv.invoice_type, 0) + 1

    return {
        "total_facturas": len(result.facturas),
        "total_facturadores": len(invoices_by_facturador),
        "total_vacias": len(result.vacias),
        "total_duplicados": len(result.duplicados),
        "total_errores": len(result.errores_scan),
        **{f"status_{k}": v for k, v in status_counts.items()},
        **{f"type_{k}": v for k, v in type_counts.items()},
    }


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

    # Step 4: Build final ScanResult with recalculated indicators
    result = ScanResult(
        facturas=scan_result.facturas,
        indicadores={},
        duplicados=duplicados,
        vacias=scan_result.vacias,
        errores_scan=scan_result.errores_scan,
        excel_path=None,
    )
    result.indicadores = recalculate_indicators(result)

    return result
