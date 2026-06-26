"""Tests for app/services/monitoreo_carpetas/detect_all.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.monitoreo_carpetas import ScanResult
from app.services.monitoreo_carpetas.detect_all import detect_all


class TestDetectAll:
    """Tests for detect_all()."""

    def test_detect_all_returns_scanresult(self, temp_scan_root: Path) -> None:
        """detect_all returns a ScanResult instance."""
        result = detect_all([str(temp_scan_root)])
        assert isinstance(result, ScanResult)

    def test_detect_all_finds_invoices(self, temp_scan_root: Path) -> None:
        """detect_all finds invoice folders from the temp tree."""
        result = detect_all([str(temp_scan_root)])
        assert len(result.facturas) >= 2
        filenames = {r.filename for r in result.facturas}
        assert "FEV12345" in filenames
        assert "CAP001_ABC002" in filenames
        assert "FEV67890" in filenames

    def test_detect_all_detects_empty_folders(self, temp_scan_root: Path) -> None:
        """detect_all flags empty invoice folder FEV99999."""
        result = detect_all([str(temp_scan_root)])
        empty_folders = [v["folder"] for v in result.vacias]
        assert any("FEV99999" in f for f in empty_folders)

    def test_detect_all_handles_missing_root(self) -> None:
        """detect_all handles missing root without crashing."""
        result = detect_all([r"\\nonexistent\share"])
        assert isinstance(result, ScanResult)
        assert len(result.errores_scan) >= 1

    def test_detect_all_indicadores_include_counts(self, temp_scan_root: Path) -> None:
        """detect_all populates indicadores with expected keys."""
        result = detect_all([str(temp_scan_root)])
        assert "total_facturas" in result.indicadores
        assert "total_facturadores" in result.indicadores
        assert "total_vacias" in result.indicadores
        assert result.indicadores["total_facturas"] >= 3

    def test_detect_all_no_duplicates_in_single_root(self, temp_scan_root: Path) -> None:
        """detect_all finds no duplicates in a single root without overlap."""
        result = detect_all([str(temp_scan_root)])
        assert len(result.duplicados) == 0

    def test_detect_all_detects_duplicates(self, temp_scan_root: Path) -> None:
        """detect_all detects duplicates when same folder name appears in multiple branches."""
        # Create a second FEV12345 folder under Luis to produce a duplicate
        luis_company = temp_scan_root / "PENDIENTE - Luis" / "company_C"
        dup_folder = luis_company / "FEV12345"
        dup_folder.mkdir()
        (dup_folder / "dummy.txt").write_text("dup")

        result = detect_all([str(temp_scan_root)])
        dup_filenames = [d["filename"] for d in result.duplicados]
        assert "FEV12345" in dup_filenames

    def test_detect_all_excel_path_is_none_initially(self, temp_scan_root: Path) -> None:
        """detect_all returns excel_path as None before report generation."""
        result = detect_all([str(temp_scan_root)])
        assert result.excel_path is None
