"""Tests for app/services/monitoreo_carpetas/__init__.py dataclasses."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult


class TestInvoiceRecord:
    """InvoiceRecord dataclass tests."""

    def test_create_invoice_record_minimal(self) -> None:
        """Create InvoiceRecord with required fields."""
        record = InvoiceRecord(
            filename="FEV12345.pdf",
            facturador="Juan",
            full_path=r"\\server\root\LISTAS OK - Juan\FEV12345.pdf",
            status="Verificada",
            invoice_type="FEV",
            invoice_code="FEV12345",
        )
        assert record.filename == "FEV12345.pdf"
        assert record.facturador == "Juan"
        assert record.status == "Verificada"
        assert record.invoice_type == "FEV"
        assert record.invoice_code == "FEV12345"

    def test_invoice_record_has_no_doc_fields(self) -> None:
        """InvoiceRecord must NOT have doc_type/doc_number fields."""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(InvoiceRecord)}
        assert "doc_type" not in fields, "doc_type must not be a field"
        assert "doc_number" not in fields, "doc_number must not be a field"

    def test_invoice_record_is_dataclass(self) -> None:
        """InvoiceRecord should be a dataclass with defined fields."""
        import dataclasses
        assert dataclasses.is_dataclass(InvoiceRecord)
        fields = {f.name for f in dataclasses.fields(InvoiceRecord)}
        assert "filename" in fields
        assert "facturador" in fields
        assert "full_path" in fields
        assert "status" in fields
        assert "invoice_type" in fields
        assert "invoice_code" in fields


class TestScanResult:
    """ScanResult dataclass tests."""

    def test_create_scan_result_empty(self) -> None:
        """Create ScanResult with empty lists."""
        result = ScanResult()
        assert result.facturas == []
        assert result.indicadores == {}
        assert result.duplicados == []
        assert result.vacias == []
        assert result.errores_scan == []
        assert result.excel_path is None

    def test_create_scan_result_with_data(self) -> None:
        """Create ScanResult with populated fields."""
        factura = InvoiceRecord(
            filename="FEV123.pdf",
            facturador="Juan",
            full_path=r"\\server\root\FEV123.pdf",
            status="Verificada",
            invoice_type="FEV",
            invoice_code="FEV123",
        )
        result = ScanResult(
            facturas=[factura],
            indicadores={"total": 1, "verificadas": 1},
            duplicados=[{"filename": "FEV123.pdf", "facturadores": ["Juan", "Maria"]}],
            vacias=[{"facturador": "Carlos", "folder": "CORREGIR - Carlos"}],
            errores_scan=[{"facturador": "server2", "error": "Timeout"}],
            excel_path="output/monitoreo_20260623_153000.xlsx",
        )
        assert len(result.facturas) == 1
        assert result.indicadores["total"] == 1
        assert len(result.duplicados) == 1
        assert len(result.vacias) == 1
        assert len(result.errores_scan) == 1
        assert result.excel_path == "output/monitoreo_20260623_153000.xlsx"

    def test_scan_result_is_dataclass(self) -> None:
        """ScanResult should be a dataclass with defined fields."""
        import dataclasses
        assert dataclasses.is_dataclass(ScanResult)
        fields = {f.name for f in dataclasses.fields(ScanResult)}
        assert "facturas" in fields
        assert "indicadores" in fields
        assert "duplicados" in fields
        assert "vacias" in fields
        assert "errores_scan" in fields
        assert "excel_path" in fields
