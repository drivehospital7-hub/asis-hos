"""Tests for scan_subtree() public API in folder_scanner.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord
from app.services.monitoreo_carpetas.folder_scanner import scan_subtree


class TestScanSubtree:
    """Tests for scan_subtree()."""

    def test_scan_subtree_finds_all_invoices(self, temp_scan_root: Path) -> None:
        """scan_subtree finds invoice folders across the entire root."""
        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        scan_subtree(str(temp_scan_root), str(temp_scan_root), 0, invoices, empty_folders, errors)

        assert len(invoices) == 3  # FEV12345, CAP001_ABC002, FEV67890
        filenames = {r.filename for r in invoices}
        assert "FEV12345" in filenames
        assert "CAP001_ABC002" in filenames
        assert "FEV67890" in filenames

    def test_scan_subtree_scoped_to_subpath(self, temp_scan_root: Path) -> None:
        """scan_subtree when given a subpath returns only invoices under that path."""
        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        subpath = str(temp_scan_root / "0 FACTURAS CAPITA OK - Juan")
        scan_subtree(subpath, str(temp_scan_root), 0, invoices, empty_folders, errors)

        # Only Juan's facturador has invoices: FEV12345, CAP001_ABC002
        assert len(invoices) == 2
        filenames = {r.filename for r in invoices}
        assert "FEV12345" in filenames
        assert "CAP001_ABC002" in filenames
        assert "FEV67890" not in filenames

    def test_scan_subtree_empty_subpath_yields_no_invoices(self, temp_scan_root: Path) -> None:
        """scan_subtree on a path with no invoice folders returns empty."""
        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        # PENDIENTE - Luis has only HAU_02 (non-invoice) and FEV99999 (empty)
        subpath = str(temp_scan_root / "PENDIENTE - Luis")
        scan_subtree(subpath, str(temp_scan_root), 0, invoices, empty_folders, errors)

        assert len(invoices) == 0

    def test_scan_subtree_empty_check_without_listdir(
        self, temp_scan_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """El chequeo de vacías no enumera la carpeta completa (single-entry)."""
        import app.services.monitoreo_carpetas.folder_scanner as scanner_mod

        def _forbidden_listdir(_path):
            raise AssertionError("os.listdir no debe usarse para chequeo-vacío")

        monkeypatch.setattr(scanner_mod.os, "listdir", _forbidden_listdir)

        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        scan_subtree(str(temp_scan_root), str(temp_scan_root), 0, invoices, empty_folders, errors)

        assert len(invoices) == 3
        assert any(
            v.get("folder", "").endswith("FEV99999") for v in empty_folders
        )
        assert errors == []

    def test_scan_subtree_captura_mtime(self, temp_scan_root: Path) -> None:
        """Cada invoice válida trae el mtime de su carpeta (dir real)."""
        import os

        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        scan_subtree(str(temp_scan_root), str(temp_scan_root), 0, invoices, empty_folders, errors)

        assert len(invoices) == 3
        for inv in invoices:
            assert isinstance(inv.mtime, float)
            # Aproximado: el mtime del dir puede moverse ~ms entre el scan
            # (entry.stat) y esta lectura (os.stat).
            assert inv.mtime == pytest.approx(
                os.stat(inv.full_path).st_mtime, abs=5.0
            )

    def test_scan_subtree_stat_falla_mtime_none(
        self, temp_scan_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Si entry.stat falla (OSError), el invoice se registra con mtime None."""
        import os

        real_stat = os.DirEntry.stat

        def _failing_stat(self_entry, *args, **kwargs):
            if self_entry.name.upper().startswith(("FEV", "CAP")):
                raise OSError("stat simulado")
            return real_stat(self_entry, *args, **kwargs)

        monkeypatch.setattr(os.DirEntry, "stat", _failing_stat)

        invoices: list[InvoiceRecord] = []
        empty_folders: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        scan_subtree(str(temp_scan_root), str(temp_scan_root), 0, invoices, empty_folders, errors)

        assert len(invoices) == 3
        assert all(inv.mtime is None for inv in invoices)
