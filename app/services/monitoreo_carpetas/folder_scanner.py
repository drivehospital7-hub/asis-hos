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
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any

from app.constants.monitoreo_carpetas import (
    MAX_CONCURRENT_SCANS,
    ROOT_PROBE_TIMEOUT,
    SCAN_TIMEOUT_PER_FACTURADOR,
)
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


def scan_subtree(
    dir_path_str: str,
    root_str: str,
    depth: int,
    invoices: list[InvoiceRecord],
    empty_folders: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> None:
    """Recorrido controlado de un subárbol: para en carpetas FEV/CAP, no las abre.

    Escanea recursivamente el directorio dado (hasta _MAX_SCAN_DEPTH niveles)
    y recolecta facturas, carpetas vacías y errores en las listas provistas.

    Args:
        dir_path_str: Ruta del directorio a escanear.
        root_str: Ruta raíz del escaneo (para calcular rutas relativas).
        depth: Profundidad actual de recursión.
        invoices: Lista donde se agregan los InvoiceRecord encontrados.
        empty_folders: Lista donde se agregan las carpetas vacías detectadas.
        errors: Lista donde se agregan los errores de escaneo.
    """

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
            scan_subtree(path_str, root_str, depth + 1, invoices, empty_folders, errors)
            continue

        # May be an invoice folder → validate
        invoice_type, is_valid = validate_name(name)

        dir_rel = path_str[len(root_str):].lstrip(os.sep)
        path_parts = dir_rel.replace("\\", "/").split("/")
        facturador_name = path_parts[0] if path_parts else ""

        # Check empty (before validation — even invalid FEV*/CAP* should be flagged).
        # Single-entry scandir: only whether the folder has ANY child matters,
        # never the full listing (SMB folders can hold thousands of PDFs and
        # `os.listdir` would enumerate them all just to answer "is it empty?").
        try:
            is_empty = _is_empty_dir(path_str)
        except (OSError, PermissionError) as exc:
            errors.append({"root": path_str, "error": str(exc)})
            continue

        if is_empty:
            empty_folders.append({
                "facturador": facturador_name,
                "folder": path_str,
            })
            # Don't recurse into empty folders
            continue

        if not is_valid:
            # Non-empty but invalid → recurse for nested valid invoices
            scan_subtree(path_str, root_str, depth + 1, invoices, empty_folders, errors)
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


def _is_empty_dir(path_str: str) -> bool:
    """Return True if a directory has no entries (single-entry scandir).

    Only peeks at the FIRST entry instead of enumerating the whole folder
    like ``os.listdir`` would — critical on SMB where invoice folders can
    hold thousands of PDFs and a full listing just to test emptiness
    stalls the scan.
    """
    with os.scandir(path_str) as it:
        return next(it, None) is None


def _probe_root(root_str: str) -> bool:
    """Lightweight accessibility probe of one root, bounded by timeout.

    Same pattern as ``FolderWatcher._probe_root``: a single-entry
    ``os.scandir`` in a daemon thread joined with ``ROOT_PROBE_TIMEOUT``.
    A hung SMB share blocks inside ``scandir`` forever, so the probe —
    never the scan itself — absorbs that hang and reports the root as
    unreachable. Only ``OSError`` (missing/denied) or a timeout mark the
    root as bad; any other outcome counts as accessible.
    """
    outcome: dict[str, bool] = {}

    def _try() -> None:
        try:
            with os.scandir(root_str) as it:
                next(it, None)
            outcome["ok"] = True
        except OSError:
            outcome["ok"] = False

    thread = threading.Thread(target=_try, daemon=True)
    thread.start()
    thread.join(timeout=ROOT_PROBE_TIMEOUT)
    if thread.is_alive():
        logger.warning("Root probe timed out (SMB colgado?): %s", root_str)
        return False
    return outcome.get("ok", False)


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

    scan_subtree(root_str, root_str, 0, invoices, empty_folders, errors)

    return {
        "invoices": invoices,
        "errors": errors,
        "empty_folders": empty_folders,
    }


def scan_all(root_paths: list[str]) -> ScanResult:
    """Escanea todos los directorios raíz configurados en paralelo.

    Cada raíz se recorre con profundidad controlada (máx 6 niveles),
    parando en carpetas invoice (FEV/CAP) sin entrar en ellas.

    Anti-cuelgue SMB: cada root se pre-chequea con `_probe_root`
    (single-entry scandir acotado por `ROOT_PROBE_TIMEOUT`); un root
    inaccesible o colgado genera una entrada de error inmediata SIN
    entrar al executor. El executor nunca bloquea el response en hilos
    colgados dentro de `os.scandir`: tras recolectar con timeout por
    root se cierra con `shutdown(wait=False, cancel_futures=True)` para
    no esperar el join de hilos atascados en I/O de red.
    """

    all_invoices: list[InvoiceRecord] = []
    all_empty: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    invoices_by_facturador: dict[str, list[InvoiceRecord]] = {}

    if not root_paths:
        return ScanResult(errores_scan=[{"root": "", "error": "No root paths configured"}])

    # Pre-probe: filter out unreachable/hung roots BEFORE spending threads.
    # A hung UNC share blocks inside os.scandir forever; the bounded probe
    # absorbs that hang (~ROOT_PROBE_TIMEOUT per root) instead of the scan.
    scannable: list[str] = []
    for rp in root_paths:
        if _probe_root(rp):
            scannable.append(rp)
        else:
            logger.error("Root inaccesible, se saltea escaneo: %s", rp)
            all_errors.append({
                "root": rp,
                "error": f"Root inaccesible (probe timeout {ROOT_PROBE_TIMEOUT}s): {rp}",
            })

    if not scannable:
        return ScanResult(
            facturas=[],
            indicadores={
                "total_facturas": 0,
                "total_facturadores": 0,
                "total_vacias": 0,
                "total_errores": len(all_errors),
                "timestamp": datetime.now().isoformat(),
            },
            duplicados=[],
            vacias=[],
            errores_scan=all_errors,
            excel_path=None,
        )

    max_workers = min(MAX_CONCURRENT_SCANS, len(scannable))

    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_to_root = {
            executor.submit(_scan_root, Path(rp.replace("\\", "/"))): rp
            for rp in scannable
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
    finally:
        # Never block the response joining threads hung in SMB os.scandir:
        # `future.result(timeout)` above already bounded each root, and this
        # shutdown without join lets stragglers die with the daemon threads
        # instead of hanging the HTTP request on executor teardown.
        executor.shutdown(wait=False, cancel_futures=True)

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
