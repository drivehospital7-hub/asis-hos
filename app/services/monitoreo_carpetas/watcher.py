"""FolderWatcher — watchdog-based automatic monitoring of scanned folders.

Wraps a watchdog Observer in a daemon thread. First POST /scan triggers
a full scan + observer start. Subsequent calls perform health checks.
Filesystem events trigger incremental subtree re-scans.

Persists ScanResult to snapshot file so data survives server restarts.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.constants.monitoreo_carpetas import WATCHDOG_POLL_INTERVAL
from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.detect_all import detect_all, recalculate_indicators
from app.services.monitoreo_carpetas.duplicate_detector import find_duplicates
from app.services.monitoreo_carpetas.folder_scanner import scan_subtree
from app.services.monitoreo_carpetas.report_generator import generate_excel

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data"
_SNAPSHOT_FILE = _SNAPSHOT_DIR / "monitoreo_snapshot.json"


class _SubtreeUpdateHandler(FileSystemEventHandler):
    """Watchdog event handler that triggers incremental subtree updates."""

    def __init__(self, watcher: FolderWatcher) -> None:
        super().__init__()
        self._watcher = watcher

    def on_created(self, event) -> None:
        if event.is_directory:
            logger.info("Watchdog: created %s", event.src_path)
            self._watcher._events_count += 1
            self._watcher.update_subtree(event.src_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            logger.info("Watchdog: modified %s", event.src_path)
            self._watcher._events_count += 1
            self._watcher.update_subtree(event.src_path)

    def on_deleted(self, event) -> None:
        # NOTE: is_directory may be False for deleted dirs on Windows
        # because the path no longer exists. Always try to remove.
        logger.info("Watchdog: deleted %s", event.src_path)
        self._watcher._events_count += 1
        self._watcher.remove_subtree(event.src_path)

    def on_moved(self, event) -> None:
        # is_directory may be unreliable for moved source on Windows
        logger.info("Watchdog: moved %s -> %s", event.src_path, event.dest_path)
        self._watcher._events_count += 1
        self._watcher.remove_subtree(event.src_path)
        self._watcher.update_subtree(event.dest_path)


class FolderWatcher:
    """Caches ScanResult in memory and monitors roots via watchdog.

    Lifecycle: ``None`` (initial) → ``first_scan()`` called → result cached and
    observer daemon running → ``update_subtree()`` on each watchdog event →
    ``health_check()`` on subsequent requests.

    Thread safety: all ``ScanResult`` reads/writes are protected by
    ``threading.Lock``.
    """

    def __init__(self) -> None:
        self._result: ScanResult | None = None
        self._observer: Observer | None = None
        self._lock = threading.Lock()
        self._roots: list[str] = []
        self._events_count: int = 0  # For diagnostics
        self._load_snapshot()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def first_scan(self, roots: list[str]) -> tuple[ScanResult, str | None]:
        """Full scan + Excel generation + watchdog observer start.

        Args:
            roots: List of root directory paths to scan and monitor.

        Returns:
            Tuple of (ScanResult, excel_filename or None).
        """
        self._roots = roots

        # Full scan
        scan_result = detect_all(roots)
        excel_filename: str | None = None

        # Generate Excel report
        try:
            from datetime import datetime

            from app.utils.input_data import output_data_directory

            output_dir = output_data_directory(create=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = output_dir / f"monitoreo_{timestamp}.xlsx"
            generate_excel(scan_result, str(excel_path))
            scan_result.excel_path = str(excel_path)
            excel_filename = excel_path.name
        except Exception as exc:
            logger.exception("Error generating Excel during first_scan")
            excel_filename = None

        # Cache result
        self.set_result(scan_result)

        # Persist snapshot to disk (survives server restart)
        self._save_snapshot()

        # Start watchdog observer daemon
        self._start_observer(roots)

        return scan_result, excel_filename

    def health_check(self) -> dict[str, Any]:
        """Check watchdog health, fallback to full scan if dead.

        Returns:
            Dict with ``monitoring`` status and ``message``.
            If fallback ran, also includes ``result`` and ``excel_filename``.
        """
        if self._observer is not None and self._observer.is_alive():
            return {
                "monitoring": True,
                "message": "Sistema OK, monitoreando cambios en tiempo real",
                "events_count": self._events_count,
                "observer_alive": True,
            }

        # Observer not running but we have data (e.g., after server restart).
        # Restart the observer and return cached data.
        if self._roots and self._result is not None:
            try:
                self._start_observer(self._roots)
                logger.info("Observer restarted from snapshot for %s", self._roots)
                return {
                    "monitoring": True,
                    "message": "Sistema OK, monitoreando cambios en tiempo real (reconectado)",
                    "events_count": self._events_count,
                    "observer_alive": True,
                }
            except Exception as exc:
                logger.warning("Failed to restart observer: %s", exc)

        # Observer is dead or None — do fallback full scan
        logger.warning("Watchdog observer not alive, triggering fallback full scan")
        result, excel_filename = self.first_scan(self._roots)
        return {
            "monitoring": False,
            "message": "Watchdog caído, escaneo completo ejecutado",
            "result": result,
            "excel_filename": excel_filename,
        }

    def update_subtree(self, path: str) -> None:
        """Re-scan affected subtree and merge into ScanResult under lock.

        Scans the PARENT of the event path, not the path itself.
        This ensures FEV/CAP subfolders are found as children rather than
        the scanner looking inside them.

        Removes existing entries whose ``full_path`` starts with the parent
        path, appends freshly scanned entries, and recalculates indicators.

        Args:
            path: Filesystem path that changed (triggered by watchdog event).
        """
        with self._lock:
            if self._result is None:
                return

            invoices: list[InvoiceRecord] = []
            empty_folders: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []

            # Find the root that contains this path
            root = self._find_root(path)
            event = Path(path)
            root_p = Path(root)

            # Scan from the PARENT so FEV/CAP subdirs are found as children
            if event == root_p or event.parent == root_p:
                scan_dir = str(root_p)
                depth_offset = 0
            else:
                scan_dir = str(event.parent)
                try:
                    depth_offset = len(event.parent.relative_to(root_p).parts)
                except ValueError:
                    depth_offset = 0

            # Scan the affected parent (handle missing paths gracefully)
            try:
                scan_subtree(scan_dir, root, depth_offset, invoices, empty_folders, errors)
            except OSError as exc:
                logger.warning("Cannot scan %s: %s — treating as removal", path, exc)
                self._remove_entries(path)
                self._result.indicadores = recalculate_indicators(self._result)
                inv_by_fact: dict[str, list[InvoiceRecord]] = {}
                for inv in self._result.facturas:
                    inv_by_fact.setdefault(inv.facturador, []).append(inv)
                self._result.duplicados = find_duplicates(inv_by_fact)
                self._save_snapshot()
                return

            # Normalize scan_dir for prefix matching
            norm_path = scan_dir.replace("\\", "/")

            # Remove stale entries whose full_path starts with the scan_dir
            self._result.facturas = [
                inv for inv in self._result.facturas
                if not inv.full_path.replace("\\", "/").startswith(norm_path)
            ]
            self._result.vacias = [
                v for v in self._result.vacias
                if not v.get("folder", "").replace("\\", "/").startswith(norm_path)
            ]
            self._result.errores_scan = [
                e for e in self._result.errores_scan
                if not e.get("root", "").replace("\\", "/").startswith(norm_path)
            ]

            # Append fresh entries
            self._result.facturas.extend(invoices)
            self._result.vacias.extend(empty_folders)
            # Only include errors from the current scan, not stale ones
            self._result.errores_scan.extend(errors)

            # Recalculate indicators
            self._result.indicadores = recalculate_indicators(self._result)

            # Recalculate duplicates — full recompute from in-memory ScanResult
            invoices_by_facturador: dict[str, list[InvoiceRecord]] = {}
            for inv in self._result.facturas:
                invoices_by_facturador.setdefault(inv.facturador, []).append(inv)
            self._result.duplicados = find_duplicates(invoices_by_facturador)

            self._save_snapshot()

            logger.info(
                "Subtree updated: %s (from event %s, %d invoices, %d errors)",
                scan_dir,
                path,
                len(self._result.facturas),
                len(self._result.errores_scan),
            )

    def remove_subtree(self, path: str) -> None:
        """Remove all entries for a path from the ScanResult (used on delete/move-src).

        Unlike update_subtree, this does NOT attempt to scan — the path is
        already gone. Only removes entries and recalculates aggregates.

        Args:
            path: Filesystem path that was deleted or moved away.
        """
        with self._lock:
            if self._result is None:
                return
            self._remove_entries(path)
            self._result.indicadores = recalculate_indicators(self._result)
            invoices_by_facturador: dict[str, list[InvoiceRecord]] = {}
            for inv in self._result.facturas:
                invoices_by_facturador.setdefault(inv.facturador, []).append(inv)
            self._result.duplicados = find_duplicates(invoices_by_facturador)
            self._save_snapshot()
            logger.info(
                "Subtree removed: %s (%d invoices remaining)",
                path,
                len(self._result.facturas),
            )

    def reset(self) -> None:
        """Reset watcher state (stop observer, clear result).

        Intended for testing — allows tests to start fresh without
        server restart.
        """
        with self._lock:
            if self._observer is not None:
                try:
                    self._observer.stop()
                except Exception:
                    pass
                self._observer = None
            self._result = None
            self._roots = []
            self._events_count = 0
            # Delete stale snapshot so old data doesn't reload on restart
            try:
                _SNAPSHOT_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    def set_result(self, result: ScanResult) -> None:
        """Thread-safe setter for ScanResult."""
        with self._lock:
            self._result = result

    def get_result(self) -> ScanResult | None:
        """Thread-safe getter for ScanResult."""
        with self._lock:
            return self._result

    def get_roots(self) -> list[str]:
        """Returns the configured roots (thread-safe read)."""
        return list(self._roots)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_snapshot(self) -> None:
        """Persist ScanResult to disk so it survives server restarts."""
        if self._result is None or not self._roots:
            return
        try:
            data: dict[str, Any] = {
                "roots": self._roots,
                "result": {
                    "facturas": [
                        {
                            "filename": inv.filename,
                            "facturador": inv.facturador,
                            "full_path": inv.full_path,
                            "status": inv.status,
                            "invoice_type": inv.invoice_type,
                            "invoice_code": inv.invoice_code,
                        }
                        for inv in self._result.facturas
                    ],
                    "indicadores": dict(self._result.indicadores),
                    "duplicados": self._result.duplicados,
                    "vacias": self._result.vacias,
                    "errores_scan": self._result.errores_scan,
                    "excel_path": self._result.excel_path,
                },
            }
            _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            tmp_path = _SNAPSHOT_FILE.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
            tmp_path.replace(_SNAPSHOT_FILE)
        except Exception:
            logger.exception("Failed to save snapshot")

    def _load_snapshot(self) -> None:
        """Load ScanResult from disk snapshot if available."""
        if not _SNAPSHOT_FILE.exists():
            return
        try:
            data = json.loads(_SNAPSHOT_FILE.read_text(encoding="utf-8"))
            self._roots = data.get("roots", [])
            result_data = data.get("result", {})
            facturas = [
                InvoiceRecord(
                    filename=inv["filename"],
                    facturador=inv["facturador"],
                    full_path=inv["full_path"],
                    status=inv["status"],
                    invoice_type=inv["invoice_type"],
                    invoice_code=inv["invoice_code"],
                )
                for inv in result_data.get("facturas", [])
            ]
            self._result = ScanResult(
                facturas=facturas,
                indicadores=result_data.get("indicadores", {}),
                duplicados=result_data.get("duplicados", []),
                vacias=result_data.get("vacias", []),
                errores_scan=result_data.get("errores_scan", []),
                excel_path=result_data.get("excel_path"),
            )
            logger.info("Snapshot loaded: %d invoices, %d roots", len(facturas), len(self._roots))
        except Exception:
            logger.exception("Failed to load snapshot — starting fresh")

    def _remove_entries(self, path: str) -> None:
        """Remove all ScanResult entries whose path starts with the given prefix."""
        norm_path = path.replace("\\", "/")
        self._result.facturas = [
            inv for inv in self._result.facturas
            if not inv.full_path.replace("\\", "/").startswith(norm_path)
        ]
        self._result.vacias = [
            v for v in self._result.vacias
            if not v.get("folder", "").replace("\\", "/").startswith(norm_path)
        ]
        self._result.errores_scan = [
            e for e in self._result.errores_scan
            if not e.get("root", "").replace("\\", "/").startswith(norm_path)
        ]

    def _start_observer(self, roots: list[str]) -> None:
        """Start the watchdog Observer daemon for the given roots."""
        if self._observer is not None:
            try:
                self._observer.stop()
            except Exception:
                pass
            self._observer = None

        event_handler = _SubtreeUpdateHandler(self)
        self._observer = Observer(timeout=WATCHDOG_POLL_INTERVAL)

        for root in roots:
            self._observer.schedule(event_handler, root, recursive=True)
            logger.info("Watchdog monitoring: %s", root)

        self._observer.start()
        logger.info("Watchdog observer started")

    def _find_root(self, path: str) -> str:
        """Find which configured root contains the given path.

        Returns the matching root, or the first root as fallback.
        """
        norm_path = path.replace("\\", "/")
        for root in self._roots:
            norm_root = root.replace("\\", "/")
            if norm_path.startswith(norm_root):
                return root
        # Fallback: use the first root
        return self._roots[0] if self._roots else path
