"""Tests for FolderWatcher in app/services/monitoreo_carpetas/watcher.py."""

from __future__ import annotations

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

        response = watcher.health_check()
        assert response["monitoring"] is True
        assert "Sistema OK" in response["message"]

    def test_health_check_observer_none_triggers_fallback(self) -> None:
        """health_check triggers fallback when observer is None."""
        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]

        # With roots but no observer and no result, health_check
        # should try to do a first_scan fallback
        with mock.patch.object(watcher, "first_scan") as mock_first_scan:
            mock_first_scan.return_value = (ScanResult(), "test.xlsx")
            response = watcher.health_check()

            mock_first_scan.assert_called_once()
            assert response["monitoring"] is False
            assert "Watchdog caído" in response.get("message", "")

    def test_health_check_observer_dead_triggers_fallback(self) -> None:
        """health_check triggers fallback full scan when observer is dead."""
        watcher = FolderWatcher()
        watcher._roots = ["/fake/root"]

        mock_observer = mock.Mock()
        mock_observer.is_alive.return_value = False
        watcher._observer = mock_observer

        with mock.patch.object(watcher, "first_scan") as mock_first_scan:
            mock_first_scan.return_value = (ScanResult(), "test.xlsx")
            response = watcher.health_check()

            mock_first_scan.assert_called_once_with(["/fake/root"])
            assert response["monitoring"] is False
