"""Tests for FolderWatcher in app/services/monitoreo_carpetas/watcher.py."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from unittest import mock

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.watcher import FolderWatcher

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_result() -> ScanResult:
    """ScanResult with a few invoices for testing."""
    return ScanResult(
        facturas=[
            InvoiceRecord(
                filename="FEV001", facturador="Juan", full_path="/r/Juan/FEV001",
                status="Verificada", invoice_type="FEV", invoice_code="FEV001",
            ),
            InvoiceRecord(
                filename="FEV002", facturador="Juan", full_path="/r/Juan/FEV002",
                status="Verificada", invoice_type="FEV", invoice_code="FEV002",
            ),
            InvoiceRecord(
                filename="FEV003", facturador="Maria", full_path="/r/Maria/FEV003",
                status="Por corregir", invoice_type="FEV", invoice_code="FEV003",
            ),
        ],
        indicadores={
            "total_facturas": 3, "total_facturadores": 2,
            "total_vacias": 0, "total_duplicados": 0, "total_errores": 0,
        },
        duplicados=[],
        vacias=[],
        errores_scan=[],
        excel_path=None,
    )


# =============================================================================
# Task 2.1: Thread safety
# =============================================================================


class TestFolderWatcherThreadSafety:
    """Thread safety of FolderWatcher result accessors."""

    def test_set_and_get_result(self) -> None:
        """set_result and get_result work correctly under Lock."""
        watcher = FolderWatcher()
        watcher.reset()  # Clear snapshot loaded from disk
        result = ScanResult(facturas=[], indicadores={"total": 0})

        assert watcher.get_result() is None
        watcher.set_result(result)
        assert watcher.get_result() is result

    def test_concurrent_read_write_no_race(self, sample_result: ScanResult) -> None:
        """Multiple threads can read/write ScanResult without errors."""
        watcher = FolderWatcher()
        watcher.set_result(sample_result)
        errors: list[Exception] = []

        def reader() -> None:
            for _ in range(50):
                try:
                    r = watcher.get_result()
                    assert r is not None
                    _ = len(r.facturas)
                except Exception as e:
                    errors.append(e)

        def writer() -> None:
            for _ in range(50):
                try:
                    r = ScanResult(
                        facturas=list(sample_result.facturas),
                        indicadores=dict(sample_result.indicadores),
                    )
                    watcher.set_result(r)
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        threads += [threading.Thread(target=writer) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0, f"Errors during concurrent access: {errors}"


# =============================================================================
# Task 2.2: update_subtree
# =============================================================================


class TestFolderWatcherUpdateSubtree:
    """update_subtree merge logic."""

    def test_update_subtree_merge_logic(self, tmp_path: Path) -> None:
        """update_subtree merges full paths from a real subtree scan."""
        # Build a real tree
        juan = tmp_path / "Juan" / "company"
        juan.mkdir(parents=True)
        (juan / "FEV001").mkdir()
        (juan / "FEV001" / "dummy.txt").write_text("x")
        (juan / "FEV002").mkdir()
        (juan / "FEV002" / "dummy.txt").write_text("x")

        maria = tmp_path / "Maria" / "company"
        maria.mkdir(parents=True)
        (maria / "FEV003").mkdir()
        (maria / "FEV003" / "dummy.txt").write_text("x")

        # Initial ScanResult with all 3 invoices
        initial = ScanResult(
            facturas=[
                InvoiceRecord(
                    filename="FEV001", facturador="Juan",
                    full_path=str(juan / "FEV001").replace("\\", "/"),
                    status="Verificada", invoice_type="FEV", invoice_code="FEV001",
                ),
                InvoiceRecord(
                    filename="FEV002", facturador="Juan",
                    full_path=str(juan / "FEV002").replace("\\", "/"),
                    status="Verificada", invoice_type="FEV", invoice_code="FEV002",
                ),
                InvoiceRecord(
                    filename="FEV003", facturador="Maria",
                    full_path=str(maria / "FEV003").replace("\\", "/"),
                    status="Por corregir", invoice_type="FEV", invoice_code="FEV003",
                ),
            ],
            indicadores={"total_facturas": 3, "total_facturadores": 2,
                         "total_vacias": 0, "total_duplicados": 0, "total_errores": 0},
        )

        watcher = FolderWatcher()
        watcher._roots = [str(tmp_path)]
        watcher.set_result(initial)

        # Add a new invoice under Juan to simulate a file creation event
        (juan / "FEV999").mkdir()
        (juan / "FEV999" / "dummy.txt").write_text("x")

        # Call update_subtree on the Juan path
        watcher.update_subtree(str(juan))

        result = watcher.get_result()
        assert result is not None

        # Should now have 4 invoices: FEV001, FEV002, FEV999, FEV003
        filenames = {r.filename for r in result.facturas}
        assert "FEV001" in filenames
        assert "FEV002" in filenames
        assert "FEV999" in filenames
        assert "FEV003" in filenames
        assert len(result.facturas) == 4

        # Indicators should be recalculated
        assert result.indicadores["total_facturas"] == 4
        assert result.indicadores["total_facturadores"] == 2

    def test_update_subtree_recalculates_duplicates(self, tmp_path: Path) -> None:
        """update_subtree recalculates duplicados after merging."""
        # Tree: Juan has FEV001, Maria has FEV002 — no duplicates
        juan = tmp_path / "Juan" / "company"
        juan.mkdir(parents=True)
        (juan / "FEV001").mkdir()
        (juan / "FEV001" / "doc.txt").write_text("x")

        maria = tmp_path / "Maria" / "company"
        maria.mkdir(parents=True)
        (maria / "FEV002").mkdir()
        (maria / "FEV002" / "doc.txt").write_text("x")

        initial = ScanResult(
            facturas=[
                InvoiceRecord(
                    filename="FEV001", facturador="Juan",
                    full_path=str(juan / "FEV001").replace("\\", "/"),
                    status="Verificada", invoice_type="FEV", invoice_code="FEV001",
                ),
                InvoiceRecord(
                    filename="FEV002", facturador="Maria",
                    full_path=str(maria / "FEV002").replace("\\", "/"),
                    status="Verificada", invoice_type="FEV", invoice_code="FEV002",
                ),
            ],
            indicadores={"total_facturas": 2, "total_facturadores": 2,
                         "total_vacias": 0, "total_duplicados": 0, "total_errores": 0},
            duplicados=[],
        )

        watcher = FolderWatcher()
        watcher._roots = [str(tmp_path)]
        watcher.set_result(initial)

        # Now create FEV001 under Maria too → generates a duplicate with Juan
        (maria / "FEV001").mkdir()
        (maria / "FEV001" / "doc.txt").write_text("x")

        # update_subtree on Maria's company dir: removes FEV002, re-scans → finds FEV001 + FEV002
        watcher.update_subtree(str(maria))

        result = watcher.get_result()
        assert result is not None

        # FEV001 now appears in both Juan and Maria → duplicate detected
        assert len(result.duplicados) >= 1
        dup_filenames = [d["filename"] for d in result.duplicados]
        assert "FEV001" in dup_filenames

    def test_update_subtree_empty_subtree(self, tmp_path: Path) -> None:
        """update_subtree on a path with no invoices keeps existing entries."""
        watcher = FolderWatcher()
        watcher._roots = [str(tmp_path)]

        initial = ScanResult(facturas=[], indicadores={"total_facturas": 0})
        watcher.set_result(initial)

        # Create a subtree with no invoice folders
        empty_dir = tmp_path / "no_invoices"
        empty_dir.mkdir()
        (empty_dir / "readme.txt").write_text("hello")

        watcher.update_subtree(str(empty_dir))
        result = watcher.get_result()
        assert result is not None
        assert len(result.facturas) == 0


# =============================================================================
# Task 2.3: health_check
# =============================================================================


class TestFolderWatcherHealthCheck:
    """health_check behavior."""

    def test_health_check_observer_alive(self) -> None:
        """health_check returns monitoring status when observer is alive."""
        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]

        mock_observer = mock.Mock()
        mock_observer.is_alive.return_value = True
        watcher._observer = mock_observer
        watcher._result = ScanResult()

        with mock.patch.object(watcher, "_check_roots_accessible", return_value=[]):
            response = watcher.health_check()
        assert response["monitoring"] is True
        assert response["degraded_roots"] == []
        assert response["observer_alive"] is True
        assert "events_count" in response
        assert "last_event_at" in response
        assert "Sistema OK" in response["message"]

    def test_health_check_observer_alive_roots_ok_real_fs(self, tmp_path: Path) -> None:
        """Observer vivo + roots accesibles → monitoring True, sin mocks de FS."""
        watcher = FolderWatcher()
        watcher._roots = [str(tmp_path)]

        mock_observer = mock.Mock()
        mock_observer.is_alive.return_value = True
        watcher._observer = mock_observer
        watcher._result = ScanResult()

        response = watcher.health_check()
        assert response["monitoring"] is True
        assert response["degraded_roots"] == []
        assert response["observer_alive"] is True

    def test_health_check_root_inaccesible_reporta_degradado(self, tmp_path: Path) -> None:
        """Root inaccesible (SMB caído) → monitoring False + degraded_roots, SIN fallback."""
        missing = str(tmp_path / "no_existe")
        watcher = FolderWatcher()
        watcher._roots = [missing]

        mock_observer = mock.Mock()
        mock_observer.is_alive.return_value = True
        watcher._observer = mock_observer
        watcher._result = ScanResult()

        with mock.patch.object(
            watcher, "first_scan", side_effect=AssertionError("no debe hacer fallback")
        ):
            response = watcher.health_check()

        assert response["monitoring"] is False
        assert response["degraded_roots"] == [missing]
        assert response["observer_alive"] is True
        assert "no accesibles" in response["message"]
        assert "result" not in response  # sin fallback automático

    def test_last_event_at_se_actualiza_en_evento(self) -> None:
        """Los callbacks del handler actualizan last_event_at."""
        from app.services.monitoreo_carpetas.watcher import _SubtreeUpdateHandler

        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]
        assert watcher._last_event_at is None
        assert watcher._last_reconcile_at is None

        handler = _SubtreeUpdateHandler(watcher)
        event = mock.Mock()
        event.is_directory = True
        event.src_path = "/fake/root/X/company/FEV001"
        handler.on_created(event)  # sin result → update_subtree retorna temprano

        assert watcher._last_event_at is not None
        assert watcher._events_count == 1

    def test_health_check_observer_none_triggers_fallback(self) -> None:
        """health_check triggers fallback when observer is None."""
        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]

        # With roots but no observer and no result, health_check
        # should try to do a first_scan fallback
        with mock.patch.object(watcher, "first_scan") as mock_first_scan, \
                mock.patch.object(watcher, "_check_roots_accessible", return_value=[]):
            mock_first_scan.return_value = (ScanResult(), "test.xlsx")
            response = watcher.health_check()

            mock_first_scan.assert_called_once()
            assert response["monitoring"] is False
            assert "escaneo completo ejecutado" in response.get("message", "")

    def test_health_check_observer_dead_triggers_fallback(self) -> None:
        """health_check triggers fallback full scan when observer is dead."""
        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]

        mock_observer = mock.Mock()
        mock_observer.is_alive.return_value = False
        watcher._observer = mock_observer

        with mock.patch.object(watcher, "first_scan") as mock_first_scan, \
                mock.patch.object(watcher, "_check_roots_accessible", return_value=[]):
            mock_first_scan.return_value = (ScanResult(), "test.xlsx")
            response = watcher.health_check()

            mock_first_scan.assert_called_once_with(["/fake/root"])
            assert response["monitoring"] is False


# =============================================================================
# Task 1 (monitoreo-cache-resiliente): GET /data refleja salud real
# =============================================================================


class TestDataEndpointRealHealth:
    """GET /data deja de hardcodear monitoring=True; POST /scan expone salud."""

    def _authenticate(self, app_client) -> None:
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"
            sess["permisos"] = ["*"]

    def _scan_root(self, tmp_path: Path) -> Path:
        root = tmp_path / "scan_root"
        fact = root / "0 FACTURAS CAPITA OK - Test" / "company"
        fact.mkdir(parents=True)
        (fact / "FEV001").mkdir()
        (fact / "FEV001" / "dummy.txt").write_text("x")
        return root

    def test_data_reflects_healthy_monitoring(self, app_client, tmp_path: Path) -> None:
        """Roots accesibles + observer vivo -> monitoring True, degraded vacio."""
        self._authenticate(app_client)
        root = self._scan_root(tmp_path)
        os.environ["MONITOREO_CARPETAS_ROOTS"] = json.dumps([str(root)])
        try:
            scan_resp = app_client.post("/monitoreo-carpetas/scan")
            assert scan_resp.status_code == 200

            cached = app_client.post("/monitoreo-carpetas/scan").get_json()["data"]
            assert cached["monitoring"] is True
            assert cached["degraded_roots"] == []
            assert "last_event_at" in cached

            data = app_client.get("/monitoreo-carpetas/data").get_json()["data"]
            assert data["cached"] is True
            assert data["monitoring"] is True
            assert data["degraded_roots"] == []
            assert "last_event_at" in data
        finally:
            os.environ.pop("MONITOREO_CARPETAS_ROOTS", None)

    def test_data_reflects_degraded_roots(
        self, app_client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Root inaccesible -> GET /data con monitoring False + degraded_roots."""
        import app.routes.monitoreo_carpetas as route_mod

        self._authenticate(app_client)
        root = self._scan_root(tmp_path)
        os.environ["MONITOREO_CARPETAS_ROOTS"] = json.dumps([str(root)])
        try:
            scan_resp = app_client.post("/monitoreo-carpetas/scan")
            assert scan_resp.status_code == 200

            # Simular desconexion SMB: el probe reporta el root inaccesible
            monkeypatch.setattr(
                route_mod._watcher,
                "_check_roots_accessible",
                lambda: [str(root)],
            )

            data = app_client.get("/monitoreo-carpetas/data").get_json()["data"]
            assert data["cached"] is True
            assert data["monitoring"] is False
            assert data["degraded_roots"] == [str(root)]

            cached = app_client.post("/monitoreo-carpetas/scan").get_json()["data"]
            assert cached["monitoring"] is False
            assert cached["degraded_roots"] == [str(root)]
            assert "last_event_at" in cached
            assert len(cached["facturas"]) == 1
        finally:
            os.environ.pop("MONITOREO_CARPETAS_ROOTS", None)


# =============================================================================
# Tasks 2-3 (monitoreo-cache-resiliente): Excel fresco throttled
# =============================================================================


class TestExcelFreshness:
    """excel_stale flag + ensure_fresh_excel throttled regen."""

    def _watcher_with_result(self, tmp_path: Path) -> FolderWatcher:
        juan = tmp_path / "Juan" / "company"
        juan.mkdir(parents=True)
        (juan / "FEV001").mkdir()
        (juan / "FEV001" / "dummy.txt").write_text("x")
        initial = ScanResult(
            facturas=[
                InvoiceRecord(
                    filename="FEV001", facturador="Juan",
                    full_path=str(juan / "FEV001").replace("\\", "/"),
                    status="Verificada", invoice_type="FEV", invoice_code="FEV001",
                ),
            ],
            indicadores={"total_facturas": 1},
        )
        watcher = FolderWatcher()
        watcher._roots = [str(tmp_path)]
        watcher.set_result(initial)
        watcher._excel_stale = False
        watcher._excel_generated_at = None
        return watcher

    def test_update_subtree_marks_excel_stale(self, tmp_path: Path) -> None:
        """update_subtree que cambia datos marca excel_stale=True."""
        watcher = self._watcher_with_result(tmp_path)
        assert watcher.excel_stale is False
        watcher.update_subtree(str(tmp_path / "Juan"))
        assert watcher.excel_stale is True

    def test_remove_subtree_marks_excel_stale(self, tmp_path: Path) -> None:
        """remove_subtree marca excel_stale=True."""
        watcher = self._watcher_with_result(tmp_path)
        assert watcher.excel_stale is False
        watcher.remove_subtree(str(tmp_path / "Juan" / "company" / "FEV001"))
        assert watcher.excel_stale is True

    def test_ensure_fresh_excel_regenerates_when_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stale + throttle vencido -> regenera, limpia flag, actualiza path."""
        import app.utils.input_data as input_data_mod

        watcher = self._watcher_with_result(tmp_path)
        watcher._excel_stale = True
        watcher._excel_generated_at = None
        monkeypatch.setattr(
            input_data_mod, "output_data_directory", lambda create=True: tmp_path
        )
        assert watcher.ensure_fresh_excel(throttle_secs=0) is True
        assert watcher.excel_stale is False
        assert watcher.excel_generated_at is not None
        assert watcher.get_excel_filename() is not None
        assert watcher.get_excel_filename().endswith(".xlsx")

    def test_ensure_fresh_excel_respects_throttle(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Segunda llamada dentro del throttle -> no regenera."""
        import time

        import app.utils.input_data as input_data_mod

        watcher = self._watcher_with_result(tmp_path)
        watcher._excel_stale = True
        watcher._excel_generated_at = None
        monkeypatch.setattr(
            input_data_mod, "output_data_directory", lambda create=True: tmp_path
        )
        assert watcher.ensure_fresh_excel(throttle_secs=0) is True
        first_name = watcher.get_excel_filename()
        # Marcar stale de nuevo pero sin dejar pasar el throttle
        watcher._excel_stale = True
        assert watcher.ensure_fresh_excel(throttle_secs=3600) is False
        assert watcher.get_excel_filename() == first_name
        assert watcher.excel_stale is True
        _ = time.time  # throttle usa epoch s

    def test_ensure_fresh_excel_noop_when_clean(self, tmp_path: Path) -> None:
        """Sin stale -> no hace nada aunque pase el throttle."""
        watcher = self._watcher_with_result(tmp_path)
        watcher._excel_stale = False
        assert watcher.ensure_fresh_excel(throttle_secs=0) is False


# =============================================================================
# Task 4 (monitoreo-cache-resiliente): reconciliador background + SMB
# =============================================================================


class TestReconciler:
    """reconcile_once: barato (solo nombre/ruta), merge sin borrar degradados."""

    def _tree(self, root: Path, *names: str) -> Path:
        fact = root / "0 FACTURAS CAPITA OK - Test" / "company"
        fact.mkdir(parents=True, exist_ok=True)
        for name in names:
            d = fact / name
            d.mkdir(exist_ok=True)
            (d / "dummy.txt").write_text("x")
        return root

    def _watcher_with_cache(self, root: Path) -> FolderWatcher:
        from app.services.monitoreo_carpetas.detect_all import detect_all

        watcher = FolderWatcher()
        watcher._roots = [str(root)]
        watcher.set_result(detect_all([str(root)]))
        watcher._excel_stale = False
        return watcher

    def test_reconcile_sin_resultado_salteado(self) -> None:
        """Sin cache -> skip, sin timestamp."""
        watcher = FolderWatcher()
        watcher._roots = []
        assert watcher.reconcile_once() is False
        assert watcher._last_reconcile_at is None

    def test_reconcile_detecta_factura_nueva(self, tmp_path: Path) -> None:
        """Factura nueva en FS -> diff True, cache actualizado, excel stale."""
        root = self._tree(tmp_path / "root", "FEV001")
        watcher = self._watcher_with_cache(root)
        assert watcher.get_result() is not None
        assert len(watcher.get_result().facturas) == 1

        # Nueva factura aparece en disco (watchdog la perdió: SMB)
        fact = root / "0 FACTURAS CAPITA OK - Test" / "company"
        (fact / "FEV002").mkdir()
        (fact / "FEV002" / "dummy.txt").write_text("x")

        assert watcher.reconcile_once() is True
        result = watcher.get_result()
        assert result is not None
        assert {i.filename for i in result.facturas} == {"FEV001", "FEV002"}
        assert result.indicadores["total_facturas"] == 2
        assert watcher.excel_stale is True
        assert watcher._last_reconcile_at is not None

    def test_reconcile_sin_diff_no_actualiza(self, tmp_path: Path) -> None:
        """FS sin cambios -> False pero igual registra last_reconcile_at."""
        root = self._tree(tmp_path / "root", "FEV001")
        watcher = self._watcher_with_cache(root)
        assert watcher.reconcile_once() is False
        assert watcher._last_reconcile_at is not None
        assert watcher.excel_stale is False

    def test_reconcile_degradados_no_borran_cache(self, tmp_path: Path) -> None:
        """Root caído: sus datos se conservan, accesibles se mergean."""
        good = self._tree(tmp_path / "good", "FEV001")
        missing = str(tmp_path / "no_existe_smb")
        watcher = self._watcher_with_cache(good)
        # Entrada cacheada de un root que luego se cae (SMB)
        watcher.get_result().facturas.append(
            InvoiceRecord(
                filename="FEV777", facturador="Caido",
                full_path=missing + "/Caido/FEV777",
                status="En revisión", invoice_type="FEV", invoice_code="FEV777",
            )
        )
        watcher._roots = [str(good), missing]

        # Nueva factura en el root accesible
        fact = good / "0 FACTURAS CAPITA OK - Test" / "company"
        (fact / "FEV002").mkdir()
        (fact / "FEV002" / "dummy.txt").write_text("x")

        assert watcher.reconcile_once() is True
        filenames = {i.filename for i in watcher.get_result().facturas}
        assert "FEV777" in filenames  # degradado preservado
        assert "FEV002" in filenames  # accesible mergeado
        assert "FEV001" in filenames

    def test_health_snapshot_expone_last_reconcile_at(self, tmp_path: Path) -> None:
        """get_health_snapshot incluye last_reconcile_at tras reconciliar."""
        root = self._tree(tmp_path / "root", "FEV001")
        watcher = self._watcher_with_cache(root)
        assert watcher.get_health_snapshot()["last_reconcile_at"] is None
        watcher.reconcile_once()
        snapshot = watcher.get_health_snapshot()
        assert snapshot["last_reconcile_at"] is not None

    def test_reconciler_lifecycle_daemon(self) -> None:
        """start crea thread daemon; stop lo detiene (idempotentes)."""
        watcher = FolderWatcher()
        watcher.start_reconciler()
        watcher.start_reconciler()  # idempotente
        assert watcher._reconciler_thread is not None
        assert watcher._reconciler_thread.daemon is True
        assert watcher._reconciler_thread.is_alive()
        watcher.stop_reconciler()
        watcher.stop_reconciler()  # idempotente
        assert watcher._reconciler_thread is None
        watcher.reset()


# =============================================================================
# Task 7 (follow-up modo programado 15 min): scheduler = fuente de verdad,
# observer apagado por defecto, last_scan_at/next_scan_at (ISO)
# =============================================================================


class TestScheduledMode:
    """Scheduler programado cada 15 min como fuente de verdad."""

    def _tree(self, root: Path, *names: str) -> Path:
        fact = root / "0 FACTURAS CAPITA OK - Test" / "company"
        fact.mkdir(parents=True, exist_ok=True)
        for name in names:
            d = fact / name
            d.mkdir(exist_ok=True)
            (d / "dummy.txt").write_text("x")
        return root

    def _iso_diff_secs(self, last_iso: str, next_iso: str) -> float:
        from datetime import datetime

        last = datetime.fromisoformat(last_iso)
        nxt = datetime.fromisoformat(next_iso)
        return (nxt - last).total_seconds()

    def test_first_scan_no_arranca_observer_por_defecto(
        self, tmp_path: Path
    ) -> None:
        """first_scan NO arranca el Observer (flag apagado por defecto)."""
        import app.constants.monitoreo_carpetas as mc

        assert mc.ENABLE_WATCHDOG_OBSERVER is False
        assert mc.RECONCILE_INTERVAL_SECS == 900.0

        root = self._tree(tmp_path / "root", "FEV001")
        watcher = FolderWatcher()
        watcher.reset()
        try:
            scan_result, _excel = watcher.first_scan([str(root)])
            assert len(scan_result.facturas) == 1
            assert watcher._observer is None
            assert watcher._last_scan_at is not None

            snapshot = watcher.get_health_snapshot()
            assert snapshot["monitoring"] is True
            assert snapshot["observer_alive"] is False
            assert snapshot["last_scan_at"] is not None
            assert snapshot["next_scan_at"] is not None
            assert self._iso_diff_secs(
                snapshot["last_scan_at"], snapshot["next_scan_at"]
            ) == 900.0
        finally:
            watcher.reset()

    def test_reconcile_actualiza_last_y_next_scan(self, tmp_path: Path) -> None:
        """El ciclo programado actualiza last/next_scan_at y marca stale."""
        from app.services.monitoreo_carpetas.detect_all import detect_all

        root = self._tree(tmp_path / "root", "FEV001")
        watcher = FolderWatcher()
        watcher.reset()
        try:
            watcher._roots = [str(root)]
            watcher.set_result(detect_all([str(root)]))
            assert watcher.get_health_snapshot()["last_scan_at"] is None

            fact = root / "0 FACTURAS CAPITA OK - Test" / "company"
            (fact / "FEV002").mkdir()
            (fact / "FEV002" / "dummy.txt").write_text("x")

            assert watcher.reconcile_once() is True
            snapshot = watcher.get_health_snapshot()
            assert snapshot["last_scan_at"] is not None
            assert snapshot["next_scan_at"] is not None
            assert snapshot["last_reconcile_at"] is not None
            assert self._iso_diff_secs(
                snapshot["last_scan_at"], snapshot["next_scan_at"]
            ) == 900.0
            assert watcher.excel_stale is True
        finally:
            watcher.reset()

    def test_health_con_cache_no_hace_fallback_sin_observer(self) -> None:
        """Con cache y sin Observer: reporta, nunca full scan automático."""
        watcher = FolderWatcher()
        watcher.reset()
        try:
            watcher._roots = ["/fake/root"]
            watcher._result = ScanResult()
            assert watcher._observer is None
            with mock.patch.object(
                watcher, "_check_roots_accessible", return_value=[]
            ), mock.patch.object(
                watcher,
                "first_scan",
                side_effect=AssertionError("no debe hacer fallback"),
            ):
                response = watcher.health_check()
            assert response["monitoring"] is True
            assert "result" not in response
            assert response["last_scan_at"] is None
            assert response["next_scan_at"] is None
        finally:
            watcher.reset()


class TestSchedulerNoOverlap:
    """Regresión: el scheduler nunca apila ciclos solapados (SMB lento)."""

    def test_reconcile_skips_overlapping_cycle(self, tmp_path: Path) -> None:
        """Ciclo en curso + segundo ciclo → skip inmediato con log."""
        import threading
        import time

        import app.services.monitoreo_carpetas.watcher as watcher_mod

        watcher = FolderWatcher()
        watcher.reset()
        try:
            watcher._roots = [str(tmp_path)]
            watcher.set_result(
                ScanResult(facturas=[], vacias=[], errores_scan=[], indicadores={})
            )

            entered = threading.Event()
            release = threading.Event()
            calls: list[list[str]] = []

            def _blocking_detect_all(roots: list[str]):
                calls.append(list(roots))
                entered.set()
                assert release.wait(timeout=10), "el ciclo se quedó colgado"
                return ScanResult(
                    facturas=[], vacias=[], errores_scan=[], indicadores={}
                )

            watcher_done: list[bool] = []

            def _run_first() -> None:
                watcher_done.append(watcher.reconcile_once())

            with mock.patch.object(
                watcher_mod, "detect_all", side_effect=_blocking_detect_all
            ):
                first = threading.Thread(target=_run_first, daemon=True)
                first.start()
                assert entered.wait(timeout=10), "el primer ciclo no arrancó"

                start = time.time()
                skipped = watcher.reconcile_once()
                elapsed = time.time() - start

                assert skipped is False, "el ciclo solapado debe saltearse"
                assert elapsed < 2, f"el skip debe ser inmediato ({elapsed:.1f}s)"
                assert len(calls) == 1, "no debe lanzar un segundo detect_all"

                release.set()
                first.join(timeout=10)
                assert watcher_done == [False]  # sin diff → False, pero sin error

                # Lock liberado: el próximo ciclo corre normal.
                assert watcher.reconcile_once() is False
                assert len(calls) == 2
        finally:
            watcher.reset()
