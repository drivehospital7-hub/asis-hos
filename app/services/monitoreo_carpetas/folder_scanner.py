"""Escáner de directorios de red para facturas médicas.

Recorre árboles de red con recorrido controlado por profundidad
(máx 6 niveles). Al encontrar una carpeta invoice (FEV/CAP) la
procesa sin entrar. Esto evita visitar los miles de directorios
que `os.walk()` recorrería innecesariamente en SMB.

Escaneo paralelo de raíces con ThreadPoolExecutor.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any

from app.constants.monitoreo_carpetas import MAX_CONCURRENT_SCANS, SCAN_TIMEOUT_PER_FACTURADOR
from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.name_validator import validate_name
from app.services.monitoreo_carpetas.status_inferrer import infer_status

logger = logging.getLogger(__name__)

_MAX_SCAN_DEPTH = 6


def _infer_status_from_parts(parts: list[str]) -> str:
    for part in parts:
        status = infer_status(part)
        if status != "En revisión":
            return status
    return "En revisión"


def _scan_dir_controlled(
    dir_path_str: str,
    root_str: str,
    depth: int,
    invoices: list[InvoiceRecord],
    empty_folders: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    """Recorrido controlado: para en carpetas FEV/CAP, no las abre."""

    if depth > _MAX_SCAN_DEPTH:
        return

    try:
        with os.scandir(dir_path_str) as it:
            entries = list(it)
    except (OSError, PermissionError) as exc:
        errors.append({"root": dir_path_str, "error": str(exc)})
        return

    for entry in entries:
        if not entry.is_dir(follow_symlinks=False):
            continue

        name = entry.name
        path_str = entry.path

        # Pre-filter: skip folders that can't possibly be invoices
        if not name.upper().startswith(("FEV", "CAP")):
            _scan_dir_controlled(path_str, root_str, depth + 1, invoices, empty_folders, errors)
            continue

        # May be an invoice folder → validate
        invoice_type, is_valid = validate_name(name)

        dir_rel = path_str[len(root_str):].lstrip(os.sep)
        path_parts = dir_rel.replace("\\", "/").split("/")
        facturador_name = path_parts[0] if path_parts else ""

        # Check empty (before validation — even invalid FEV*/CAP* should be flagged)
        try:
            contents = os.listdir(path_str)
        except (OSError, PermissionError) as exc:
            errors.append({"root": path_str, "error": str(exc)})
            continue

        if len(contents) == 0:
            empty_folders.append({
                "facturador": facturador_name,
                "folder": path_str,
            })
            # Don't recurse into empty folders
            continue

        if not is_valid:
            # Non-empty but invalid → recurse for nested valid invoices
            _scan_dir_controlled(path_str, root_str, depth + 1, invoices, empty_folders, errors)
            continue

        # Valid, non-empty invoice folder → register but DON'T recurse
        status = _infer_status_from_parts(path_parts)

        invoices.append(InvoiceRecord(
            filename=name,
            facturador=facturador_name,
            full_path=path_str,
            status=status,
            invoice_type=invoice_type,
            invoice_code=name,
        ))


def _scan_root(root_path: Path) -> dict[str, Any]:
    """Escanea una raíz con recorrido controlado por profundidad."""

    if not root_path.exists():
        return {
            "invoices": [], "errors": [
                {"root": str(root_path), "error": f"Ruta no existe: {root_path}"}
            ], "empty_folders": [],
        }
    if not root_path.is_dir():
        return {
            "invoices": [], "errors": [
                {"root": str(root_path), "error": f"No es un directorio: {root_path}"}
            ], "empty_folders": [],
        }

    root_str = str(root_path)
    invoices: list[InvoiceRecord] = []
    empty_folders: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    _scan_dir_controlled(root_str, root_str, 0, invoices, empty_folders, errors)

    return {
        "invoices": invoices,
        "errors": errors,
        "empty_folders": empty_folders,
    }


def scan_all(root_paths: list[str]) -> ScanResult:
    """Escanea todos los directorios raíz configurados en paralelo.

    Cada raíz se recorre con profundidad controlada (máx 6 niveles),
    parando en carpetas invoice (FEV/CAP) sin entrar en ellas.
    """

    all_invoices: list[InvoiceRecord] = []
    all_empty: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    invoices_by_facturador: dict[str, list[InvoiceRecord]] = {}

    max_workers = min(MAX_CONCURRENT_SCANS, len(root_paths))

    if max_workers == 0:
        return ScanResult(errores_scan=[{"root": "", "error": "No root paths configured"}])

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_root = {
            executor.submit(_scan_root, Path(rp.replace("\\", "/"))): rp
            for rp in root_paths
        }

        for future in future_to_root:
            root_str = future_to_root[future]
            try:
                result = future.result(timeout=SCAN_TIMEOUT_PER_FACTURADOR)
            except FutureTimeoutError:
                logger.error("Timeout scanning root: %s", root_str)
                all_errors.append({
                    "root": root_str,
                    "error": f"Timeout after {SCAN_TIMEOUT_PER_FACTURADOR}s",
                })
                continue
            except Exception as exc:
                logger.exception("Error scanning root: %s", root_str)
                all_errors.append({"root": root_str, "error": str(exc)})
                continue

            all_invoices.extend(result["invoices"])
            all_empty.extend(result["empty_folders"])
            all_errors.extend(result["errors"])
            for inv in result["invoices"]:
                invoices_by_facturador.setdefault(inv.facturador, []).append(inv)

    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for inv in all_invoices:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1
        type_counts[inv.invoice_type] = type_counts.get(inv.invoice_type, 0) + 1

    return ScanResult(
        facturas=all_invoices,
        indicadores={
            "total_facturas": len(all_invoices),
            "total_facturadores": len(invoices_by_facturador),
            "total_vacias": len(all_empty),
            "total_errores": len(all_errors),
            "timestamp": datetime.now().isoformat(),
            **{f"status_{k}": v for k, v in status_counts.items()},
            **{f"type_{k}": v for k, v in type_counts.items()},
        },
        duplicados=[],
        vacias=all_empty,
        errores_scan=all_errors,
        excel_path=None,
    )
