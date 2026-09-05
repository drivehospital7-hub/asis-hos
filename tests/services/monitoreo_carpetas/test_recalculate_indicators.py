"""Tests for recalculate_indicators() in detect_all.py."""

from __future__ import annotations

from typing import Any

from app.services.monitoreo_carpetas import InvoiceRecord, ScanResult
from app.services.monitoreo_carpetas.detect_all import recalculate_indicators


class TestRecalculateIndicators:
    """Tests for recalculate_indicators()."""

    def test_recalculate_indicators_empty_result(self) -> None:
        """recalculate_indicators on empty ScanResult returns all zeros."""
        result = ScanResult()
        indicadores = recalculate_indicators(result)

        assert indicadores["total_facturas"] == 0
        assert indicadores["total_facturadores"] == 0
        assert indicadores["total_vacias"] == 0
        assert indicadores["total_duplicados"] == 0
        assert indicadores["total_errores"] == 0

    def test_recalculate_indicators_with_invoices(self) -> None:
        """recalculate_indicators counts invoices, facturadores, statuses and types."""
        facturas = [
            InvoiceRecord(
                filename="FEV001", facturador="Juan", full_path="/r/1",
                status="Verificada", invoice_type="FEV", invoice_code="FEV001",
            ),
            InvoiceRecord(
                filename="FEV002", facturador="Juan", full_path="/r/2",
                status="Verificada", invoice_type="FEV", invoice_code="FEV002",
            ),
            InvoiceRecord(
                filename="CAP001_A", facturador="Maria", full_path="/r/3",
                status="Por corregir", invoice_type="CAP", invoice_code="CAP001_A",
            ),
        ]
        result = ScanResult(
            facturas=facturas,
            vacias=[{"facturador": "Pedro", "folder": "/r/vacia"}],
            duplicados=[{"filename": "FEV001"}],
            errores_scan=[{"root": "/r", "error": "timeout"}],
        )
        indicadores = recalculate_indicators(result)

        assert indicadores["total_facturas"] == 3
        assert indicadores["total_facturadores"] == 2  # Juan, Maria
        assert indicadores["total_vacias"] == 1
        assert indicadores["total_duplicados"] == 1
        assert indicadores["total_errores"] == 1
        assert indicadores["status_Verificada"] == 2
        assert indicadores["status_Por corregir"] == 1
        assert indicadores["type_FEV"] == 2
        assert indicadores["type_CAP"] == 1

    def test_recalculate_indicators_multiple_facturadores(self) -> None:
        """recalculate_indicators correctly counts unique facturadores."""
        facturas = [
            InvoiceRecord(
                filename="FEV001", facturador="A", full_path="/r/1",
                status="Verificada", invoice_type="FEV", invoice_code="FEV001",
            ),
            InvoiceRecord(
                filename="FEV002", facturador="B", full_path="/r/2",
                status="Verificada", invoice_type="FEV", invoice_code="FEV002",
            ),
            InvoiceRecord(
                filename="FEV003", facturador="A", full_path="/r/3",
                status="Verificada", invoice_type="FEV", invoice_code="FEV003",
            ),
        ]
        result = ScanResult(facturas=facturas)
        indicadores = recalculate_indicators(result)

        assert indicadores["total_facturadores"] == 2  # A, B
        assert indicadores["total_facturas"] == 3
