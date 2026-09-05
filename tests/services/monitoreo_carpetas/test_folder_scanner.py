"""Tests for app/services/monitoreo_carpetas/folder_scanner.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.monitoreo_carpetas.folder_scanner import scan_all


class TestScanAll:
    """Tests for scan_all()."""

    def test_scan_single_root_with_facturadores(self, temp_scan_root: Path) -> None:
        """scan_all returns InvoiceRecords from a single root with facturadores."""
        result = scan_all([str(temp_scan_root)])
        assert len(result.facturas) == 3  # FEV12345, CAP001_ABC002, FEV67890
        assert len(result.errores_scan) == 0

    def test_scan_folder_names_as_filenames(self, temp_scan_root: Path) -> None:
        """filename = folder name (no .pdf extension)."""
        result = scan_all([str(temp_scan_root)])
        filenames = {r.filename for r in result.facturas}
        assert "FEV12345" in filenames
        assert "CAP001_ABC002" in filenames
        assert "FEV67890" in filenames
        # Verify no .pdf extensions
        for fname in filenames:
            assert not fname.endswith(".pdf")

    def test_scan_captures_facturador_names(self, temp_scan_root: Path) -> None:
        """scan_all captures facturador folder names."""
        result = scan_all([str(temp_scan_root)])
        facturadores = {r.facturador for r in result.facturas}
        assert "0 FACTURAS CAPITA OK - Juan" in facturadores
        assert "CORREGIR - Carlos" in facturadores

    def test_scan_infers_status(self, temp_scan_root: Path) -> None:
        """scan_all infers status from folder name."""
        result = scan_all([str(temp_scan_root)])
        for rec in result.facturas:
            if "FACTURAS CAPITA OK" in rec.facturador:
                assert rec.status == "Verificada"
            elif "CORREGIR" in rec.facturador:
                assert rec.status == "Por corregir"

    def test_scan_infers_invoice_type(self, temp_scan_root: Path) -> None:
        """scan_all infers invoice type from folder name."""
        result = scan_all([str(temp_scan_root)])
        for rec in result.facturas:
            if rec.invoice_code.startswith("FEV"):
                assert rec.invoice_type == "FEV"
                assert rec.invoice_code is not None
            elif rec.invoice_code.startswith("CAP"):
                assert rec.invoice_type == "CAP"
                assert rec.invoice_code is not None

    def test_scan_non_existent_root_logs_error(self) -> None:
        """scan_all logs error for non-existent root but doesn't crash."""
        result = scan_all([r"\\nonexistent\share"])
        assert len(result.errores_scan) >= 1
        assert result.facturas == []

    def test_scan_multiple_roots_parallel(self, temp_scan_root: Path) -> None:
        """scan_all handles multiple roots in parallel."""
        result = scan_all([str(temp_scan_root), str(temp_scan_root)])
        # Same tree scanned twice — 3 invoices × 2 = 6
        assert len(result.facturas) == 6

    def test_scan_result_shape(self, temp_scan_root: Path) -> None:
        """scan_all returns ScanResult with expected structure."""
        result = scan_all([str(temp_scan_root)])
        assert hasattr(result, "facturas")
        assert hasattr(result, "errores_scan")
        assert hasattr(result, "duplicados")
        assert hasattr(result, "vacias")

    def test_scan_full_path_is_folder(self, temp_scan_root: Path) -> None:
        """full_path = invoice folder path (not individual file path)."""
        result = scan_all([str(temp_scan_root)])
        for rec in result.facturas:
            assert rec.full_path.startswith(str(temp_scan_root))
            assert rec.filename in rec.full_path
            # Path should end with folder name, not with a file name
            assert rec.full_path.endswith(rec.filename)

    def test_prefilter_excludes_non_fev_cap(self, temp_scan_root: Path) -> None:
        """startswith pre-filter excludes CRC_/HAU_ folders."""
        result = scan_all([str(temp_scan_root)])
        filenames = {r.filename for r in result.facturas}
        # CRC_01 and HAU_02 should NOT appear
        for fname in filenames:
            assert not fname.upper().startswith("CRC")
            assert not fname.upper().startswith("HAU")

    def test_empty_invoice_folder_skipped(self, temp_scan_root: Path) -> None:
        """Empty FEV/CAP folder is flagged as empty, not an invoice."""
        result = scan_all([str(temp_scan_root)])
        # FEV99999 is empty — should be in vacias, not in facturas
        found_empty = any(
            v.get("folder", "").endswith("FEV99999")
            for v in result.vacias
        )
        assert found_empty, "Empty invoice folder FEV99999 should be in vacias"

    def test_invoice_code_is_folder_name(self, temp_scan_root: Path) -> None:
        """invoice_code equals the folder name (not derived from PDF)."""
        result = scan_all([str(temp_scan_root)])
        for rec in result.facturas:
            assert rec.invoice_code == rec.filename
