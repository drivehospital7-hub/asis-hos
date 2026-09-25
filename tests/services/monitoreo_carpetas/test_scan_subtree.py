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
