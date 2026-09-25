"""FolderWatcher — watchdog-based automatic monitoring of scanned folders.

Wraps a watchdog Observer in a daemon thread. First POST /scan triggers
a full scan + observer start. Subsequent calls perform health checks.
Filesystem events trigger incremental subtree re-scans.

Persists ScanResult to snapshot file so data survives server restarts.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.constants.monitoreo_carpetas import (
    EXCEL_REGEN_THROTTLE_SECS,
    ROOT_PROBE_TIMEOUT,
    WATCHDOG_POLL_INTERVAL,
)
from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.detect_all import detect_all, recalculate_indicators
from app.services.monitoreo_carpetas.duplicate_detector import find_duplicates
from app.services.monitoreo_carpetas.folder_scanner import scan_subtree
from app.services.monitoreo_carpetas.report_generator import generate_excel

logger = logging.getLogger(__name__)

_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "data"
_SNAPSHOT_FILE = _SNAPSHOT_DIR / "monitoreo_snapshot.json"


def _epoch_to_iso(ts: float | None) -> str | None:
    """Epoch seconds → ISO-8601 UTC string (or None when unknown)."""
    if ts is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class _SubtreeUpdateHandler(FileSystemEventHandler):
    """Watchdog event handler that triggers incremental subtree updates."""

    def __init__(self, watcher: FolderWatcher) -> None:
        super().__init__()
        self._watcher = watcher

    def on_created(self, event) -> None:
        if event.is_directory:
            logger.info("Watchdog: created %s", event.src_path)
            self._watcher._touch_event()
            self._watcher.update_subtree(event.src_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            logger.info("Watchdog: modified %s", event.src_path)
            self._watcher._touch_event()
            self._watcher.update_subtree(event.src_path)

    def on_deleted(self, event) -> None:
        # NOTE: is_directory may be False for deleted dirs on Windows
        # because the path no longer exists. Always try to remove.
        logger.info("Watchdog: deleted %s", event.src_path)
        self._watcher._touch_event()
        self._watcher.remove_subtree(event.src_path)

    def on_moved(self, event) -> None:
        # is_directory may be unreliable for moved source on Windows
        logger.info("Watchdog: moved %s -> %s", event.src_path, event.dest_path)
        self._watcher._touch_event()
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
        self._last_event_at: float | None = None  # epoch s of last watchdog event
        self._last_reconcile_at: float | None = None  # epoch s of last scheduler run
        self._last_scan_at: float | None = None  # epoch s of last full/scheduler scan
        self._reconciler_thread: threading.Thread | None = None
        self._reconciler_stop = threading.Event()
        self._excel_stale: bool = False  # True si el Excel no refleja el ScanResult
        self._excel_generated_at: float | None = None  # epoch s última generación Excel
        self._load_snapshot()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def first_scan(self, roots: list[str]) -> tuple[ScanResult, str | None]:
        """Full scan + Excel generation (+ watchdog observer only if enabled).

        El escaneo programado (scheduler) es la fuente de verdad; el
        Observer solo arranca si ``ENABLE_WATCHDOG_OBSERVER`` es True
        (apagado por defecto por volatilidad en SMB). Fija
        ``last_scan_at`` al momento del escaneo.

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
            with self._lock:
                self._excel_stale = False
                self._excel_generated_at = time.time()
        except Exception as exc:
            logger.exception("Error generating Excel during first_scan")
            excel_filename = None
            with self._lock:
                self._excel_stale = True

        # Cache result + timestamp del escaneo (fuente de verdad programada)
        self.set_result(scan_result)
        with self._lock:
            self._last_scan_at = time.time()

        # Persist snapshot to disk (survives server restart)
        self._save_snapshot()

        # Watchdog Observer: solo best-effort si está habilitado
        # (apagado por defecto — el scheduler es la fuente de verdad).
        from app.constants import monitoreo_carpetas as mc

        if mc.ENABLE_WATCHDOG_OBSERVER:
            self._start_observer(roots)

        # Start background scheduler (fuente de verdad programada)
        self.start_reconciler()

        return scan_result, excel_filename

    def health_check(self) -> dict[str, Any]:
        """Check monitoring health (scheduler is the source of truth).

        El escaneo programado es la fuente de verdad; el Observer NO
gatea la salud (apagado por defecto). Con datos en cache, nunca
dispara un fallback full scan automático aquí — solo reporta.
El fallback full scan solo ocurre cuando NO hay datos en cache
(primera carga tras restart sin snapshot útil).

        Returns:
            Dict with ``monitoring`` status, ``degraded_roots`` list,
            ``events_count``, ``observer_alive``, ``last_event_at``,
            ``last_scan_at``/``next_scan_at`` (ISO) y ``message``.
            Si hubo fallback, también incluye ``result`` y
            ``excel_filename``. Roots degradados (SMB desconectado) se
            REPORTAN, nunca disparan un fallback full scan automático.
        """
        from app.constants import monitoreo_carpetas as mc

        snapshot = self.get_health_snapshot()

        # Degraded roots — report only, no automatic full-scan fallback.
        if snapshot["degraded_roots"]:
            logger.warning(
                "Roots inaccesibles: %s — reportando degradado",
                snapshot["degraded_roots"],
            )
            return snapshot

        if snapshot["monitoring"]:
            return snapshot

        # Hay datos en cache: el scheduler es la fuente de verdad.
        # Solo re-arrancar el Observer si está habilitado (best-effort).
        if self._result is not None:
            if mc.ENABLE_WATCHDOG_OBSERVER and self._roots:
                try:
                    self._start_observer(self._roots)
                    logger.info("Observer restarted from snapshot for %s", self._roots)
                    snapshot = self.get_health_snapshot()
                    return snapshot
                except Exception as exc:
                    logger.warning("Failed to restart observer: %s", exc)
            return snapshot

        # Sin datos en cache (ni snapshot útil) — fallback full scan.
        logger.warning("Sin datos en cache, triggering fallback full scan")
        result, excel_filename = self.first_scan(self._roots)
        snapshot = self.get_health_snapshot()
        snapshot["monitoring"] = False
        snapshot["message"] = "Sin cache, escaneo completo ejecutado"
        snapshot["result"] = result
        snapshot["excel_filename"] = excel_filename
        return snapshot

    def get_health_snapshot(self) -> dict[str, Any]:
        """Lightweight health snapshot WITHOUT side effects.

        Unlike :meth:`health_check`, never restarts the observer nor runs
        a fallback full scan. Safe to call from ``GET /data`` on every
        page reload / frontend poll.

        La fuente de verdad es el escaneo programado cada
        ``RECONCILE_INTERVAL_SECS``: ``monitoring`` es True cuando hay
datos en cache y ningún root degradado (el Observer, apagado por
defecto, no gatea la salud salvo que ``ENABLE_WATCHDOG_OBSERVER``
esté activo).

        Returns:
            Dict with ``monitoring``, ``degraded_roots``, ``events_count``,
            ``observer_alive``, ``last_event_at``, ``last_reconcile_at``,
            ``last_scan_at``/``next_scan_at`` (ISO) and ``message``.
        """
        from app.constants import monitoreo_carpetas as mc

        observer = self._observer
        observer_alive = observer is not None and observer.is_alive()
        degraded_roots = self._check_roots_accessible()
        with self._lock:
            events_count = self._events_count
            last_event_at = self._last_event_at
            last_reconcile_at = self._last_reconcile_at
            last_scan_at_ts = self._last_scan_at
            has_result = self._result is not None
        last_scan_at = _epoch_to_iso(last_scan_at_ts)
        if last_scan_at_ts is not None:
            next_scan_at = _epoch_to_iso(
                last_scan_at_ts + float(mc.RECONCILE_INTERVAL_SECS)
            )
        else:
            next_scan_at = None
        if mc.ENABLE_WATCHDOG_OBSERVER:
            monitoring = observer_alive and has_result and not degraded_roots
        else:
            monitoring = has_result and not degraded_roots
        if degraded_roots:
            message = (
                "Carpetas no accesibles (SMB desconectado?): "
                + ", ".join(degraded_roots)
            )
        elif has_result:
            message = "Sistema OK, escaneo programado cada 15 min"
        else:
            message = "Sin datos: ejecutá un escaneo"
        return {
            "monitoring": monitoring,
            "degraded_roots": degraded_roots,
            "events_count": events_count,
            "observer_alive": observer_alive,
            "last_event_at": last_event_at,
            "last_reconcile_at": last_reconcile_at,
            "last_scan_at": last_scan_at,
            "next_scan_at": next_scan_at,
            "message": message,
        }

    # ------------------------------------------------------------------
    # Background reconciler (SMB event-loss safety net)
    # ------------------------------------------------------------------

    def start_reconciler(self) -> None:
        """Start the background reconciler daemon thread (idempotent).

        The thread runs :meth:`reconcile_once` every
        ``RECONCILE_INTERVAL_SECS`` (15 min, fuente de verdad programada).
        Cheap by design: only folder names/paths (never FEV/CAP content)
        via the existing ``detect_all``. The watchdog Observer is NOT
        started here (apagado por defecto; ver ``ENABLE_WATCHDOG_OBSERVER``).
        """
        if self._reconciler_thread is not None and self._reconciler_thread.is_alive():
            return
        self._reconciler_stop = threading.Event()
        thread = threading.Thread(
            target=self._reconcile_loop,
            name="monitoreo-reconciler",
            daemon=True,
        )
        self._reconciler_thread = thread
        thread.start()
        logger.info("Reconciliador background iniciado")

    def stop_reconciler(self) -> None:
        """Stop the background reconciler thread (idempotent)."""
        thread = self._reconciler_thread
        self._reconciler_thread = None
        try:
            self._reconciler_stop.set()
        except Exception:
            pass
        if thread is not None and thread is not threading.current_thread():
            try:
                thread.join(timeout=5)
            except Exception:
                pass

    def reconcile_once(self) -> bool:
        """Run a single scheduler cycle against accessible roots.

        Fuente de verdad programada: `detect_all` completo de los roots
accesibles (solo nombre/ruta FEV/CAP, nunca contenido interno).
Cuando algún root está degradado, solo se escanean los accesibles
(nunca se fuerzan los caídos) y los datos cacheados de los
degradados se preservan (merge, no reemplazo total). Cada ciclo
que escanea actualiza ``last_scan_at`` y ``last_reconcile_at``; con
diff, además marca ``excel_stale`` y persiste el snapshot.

        Returns:
            True if the cache was updated, False otherwise.
        """
        from app.constants import monitoreo_carpetas as mc

        with self._lock:
            if self._result is None:
                return False
            roots = list(self._roots)

        degraded_set = set(self._check_roots_accessible())
        now = time.time()
        if degraded_set and not mc.RECONCILE_ON_DEGRADED:
            with self._lock:
                self._last_reconcile_at = now
            return False
        accessible = [r for r in roots if r not in degraded_set]
        if not accessible:
            with self._lock:
                self._last_reconcile_at = now
            return False

        try:
            fresh = detect_all(accessible)
        except Exception:
            logger.exception("Reconciliador: error escaneando roots accesibles")
            with self._lock:
                self._last_reconcile_at = now
            return False

        with self._lock:
            if self._result is None:
                return False
            cached = self._result
            cached_acc_paths = {
                inv.full_path
                for inv in cached.facturas
                if self._owner_root(inv.full_path, roots) not in degraded_set
            }
            fresh_paths = {inv.full_path for inv in fresh.facturas}
            cached_acc_vacias = {
                v.get("folder", "")
                for v in cached.vacias
                if self._owner_root(v.get("folder", ""), roots) not in degraded_set
            }
            fresh_vacias = {v.get("folder", "") for v in fresh.vacias}
            cached_acc_errors = {
                (e.get("root", ""), e.get("error", ""))
                for e in cached.errores_scan
                if self._owner_root(e.get("root", ""), roots) not in degraded_set
            }
            fresh_errors = {
                (e.get("root", ""), e.get("error", "")) for e in fresh.errores_scan
            }
            if (
                cached_acc_paths == fresh_paths
                and cached_acc_vacias == fresh_vacias
                and cached_acc_errors == fresh_errors
            ):
                self._last_reconcile_at = now
                self._last_scan_at = now
                self._save_snapshot()
                return False

            # Merge: keep degraded-root entries, replace accessible partition.
            cached.facturas = [
                inv for inv in cached.facturas
                if self._owner_root(inv.full_path, roots) in degraded_set
            ] + list(fresh.facturas)
            cached.vacias = [
                v for v in cached.vacias
                if self._owner_root(v.get("folder", ""), roots) in degraded_set
            ] + list(fresh.vacias)
            cached.errores_scan = [
                e for e in cached.errores_scan
                if self._owner_root(e.get("root", ""), roots) in degraded_set
            ] + list(fresh.errores_scan)

            invoices_by_facturador: dict[str, list[InvoiceRecord]] = {}
            for inv in cached.facturas:
                invoices_by_facturador.setdefault(inv.facturador, []).append(inv)
            cached.duplicados = find_duplicates(invoices_by_facturador)
            cached.indicadores = recalculate_indicators(cached)

            self._excel_stale = True
            self._last_reconcile_at = now
            self._last_scan_at = now
            self._save_snapshot()
            logger.info(
                "Reconciliador: cache actualizado (%d facturas, %d degradados)",
                len(cached.facturas),
                len(degraded_set),
            )
            return True

    def _reconcile_loop(self) -> None:
        """Daemon loop: ``reconcile_once`` every ``RECONCILE_INTERVAL_SECS``.

        Este scheduler programado es la fuente de verdad (15 min)."""
        from app.constants import monitoreo_carpetas as mc

        while not self._reconciler_stop.wait(timeout=float(mc.RECONCILE_INTERVAL_SECS)):
            try:
                self.reconcile_once()
            except Exception:
                logger.exception("Reconciliador: ciclo falló (best-effort)")

    @staticmethod
    def _owner_root(path: str, roots: list[str]) -> str | None:
        """Return the configured root that owns ``path`` (prefix match)."""
        norm_path = path.replace("\\", "/")
        for root in roots:
            norm_root = root.replace("\\", "/")
            if norm_path.startswith(norm_root):
                return root
        return None

    def _check_roots_accessible(self) -> list[str]:
        """Return the subset of configured roots that are NOT accessible.

        Lightweight probe: a single-entry ``os.scandir`` per root — only
        the folder name/path matters (never enters FEV/CAP content).
        Each probe is bounded by ``ROOT_PROBE_TIMEOUT``; timeouts and
        ``OSError`` mark the root as degraded.
        """
        degraded: list[str] = []
        for root in self._roots:
            if not self._probe_root(root):
                degraded.append(root)
        return degraded

    @staticmethod
    def _probe_root(root: str) -> bool:
        """Single-entry scandir probe of one root, bounded by timeout."""
        outcome: dict[str, bool] = {}

        def _try() -> None:
            try:
                with os.scandir(root) as it:
                    next(it, None)
                outcome["ok"] = True
            except OSError:
                outcome["ok"] = False

        thread = threading.Thread(target=_try, daemon=True)
        thread.start()
        thread.join(timeout=ROOT_PROBE_TIMEOUT)
        if thread.is_alive():
            logger.warning("Root probe timed out: %s", root)
            return False
        return outcome.get("ok", False)

    def _touch_event(self) -> None:
        """Record a watchdog event (count + timestamp, thread-safe)."""
        with self._lock:
            self._events_count += 1
            self._last_event_at = time.time()

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
                self._excel_stale = True
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

            self._excel_stale = True
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
            self._excel_stale = True
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
        # NOTE: stop/join OUTSIDE the lock — watchdog dispatches handler
        # callbacks (update_subtree) in the observer thread, which needs
        # this same lock. Joining while holding it would deadlock.
        with self._lock:
            observer = self._observer
            self._observer = None
        if observer is not None:
            try:
                observer.stop()
            except Exception:
                pass
            try:
                observer.join(timeout=5)
            except Exception:
                pass
        self.stop_reconciler()
        with self._lock:
            self._result = None
            self._roots = []
            self._events_count = 0
            self._last_event_at = None
            self._last_reconcile_at = None
            self._last_scan_at = None
            self._excel_stale = False
            self._excel_generated_at = None
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

    @property
    def excel_stale(self) -> bool:
        """Thread-safe read of the Excel-stale flag."""
        with self._lock:
            return self._excel_stale

    @property
    def excel_generated_at(self) -> float | None:
        """Thread-safe read of the last Excel generation timestamp."""
        with self._lock:
            return self._excel_generated_at

    def get_excel_filename(self) -> str | None:
        """Thread-safe read of the current Excel filename (or None)."""
        with self._lock:
            if self._result is None or not self._result.excel_path:
                return None
            return Path(self._result.excel_path).name

    def ensure_fresh_excel(
        self, throttle_secs: float = EXCEL_REGEN_THROTTLE_SECS
    ) -> bool:
        """Regenerate the Excel report if stale AND throttle elapsed.

        Cheap by design: only folder names/paths (never FEV/CAP content)
        feed `generate_excel`. Best-effort — callers wrap in try/except
        so an Excel failure never breaks the API response.

        Args:
            throttle_secs: minimum seconds since last generation.

        Returns:
            True if the Excel was regenerated, False otherwise.
        """
        with self._lock:
            if self._result is None or not self._excel_stale:
                return False
            now = time.time()
            if (
                self._excel_generated_at is not None
                and (now - self._excel_generated_at) < throttle_secs
            ):
                return False
            result = self._result
        # Generate OUTSIDE the lock (file I/O) using the snapshot reference.
        from datetime import datetime

        from app.utils.input_data import output_data_directory

        output_dir = output_data_directory(create=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = output_dir / f"monitoreo_{timestamp}.xlsx"
        generate_excel(result, str(excel_path))
        with self._lock:
            if self._result is not None:
                self._result.excel_path = str(excel_path)
            self._excel_stale = False
            self._excel_generated_at = time.time()
            self._save_snapshot()
        logger.info("Excel fresco regenerado: %s", excel_path.name)
        return True

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
                "excel_stale": self._excel_stale,
                "excel_generated_at": self._excel_generated_at,
                "last_reconcile_at": self._last_reconcile_at,
                "last_scan_at": self._last_scan_at,
            }
            _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            tmp_path = _SNAPSHOT_FILE.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
            tmp_path.replace(_SNAPSHOT_FILE)
        except Exception:
            logger.exception("Failed to save snapshot")

    def _load_snapshot(self) -> None:
        """Load roots from disk snapshot (NOT the old scan data).

        On server restart after an outage, the cached scan result is stale —
        files may have been added/removed while the server was down.
        We keep the roots so they don't get lost, but discard the ScanResult
        to force a full scan on next POST /scan.
        """
        if not _SNAPSHOT_FILE.exists():
            return
        try:
            data = json.loads(_SNAPSHOT_FILE.read_text(encoding="utf-8"))
            self._roots = data.get("roots", [])
            self._excel_stale = bool(data.get("excel_stale", False))
            self._excel_generated_at = data.get("excel_generated_at")
            self._last_reconcile_at = data.get("last_reconcile_at")
            self._last_scan_at = data.get("last_scan_at")
            # Intentionally NOT loading result data — see docstring
            logger.info("Snapshot roots loaded (%d roots). Scan data discarded — will full-scan on next request.", len(self._roots))
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
                self._observer.join(timeout=5)
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
