"""Tests for app/services/monitoreo_carpetas/duplicate_detector.py."""

from __future__ import annotations

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord
from app.services.monitoreo_carpetas.duplicate_detector import find_duplicates


class TestFindDuplicates:
    """Tests for find_duplicates()."""

    def test_no_duplicates(self) -> None:
        """find_duplicates returns empty list when no duplicates exist."""
        invoices = {
            "Juan": [
                InvoiceRecord(
                    filename="FEV123.pdf", facturador="Juan",
                    full_path="/a/FEV123.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV123",
                ),
            ],
            "Maria": [
                InvoiceRecord(
                    filename="FEV456.pdf", facturador="Maria",
                    full_path="/b/FEV456.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV456",
                ),
            ],
        }
        result = find_duplicates(invoices)
        assert result == []

    def test_two_way_duplicate(self) -> None:
        """find_duplicates detects same filename in two folders."""
        invoices = {
            "Carlos": [
                InvoiceRecord(
                    filename="FEV123.pdf", facturador="Carlos",
                    full_path="/a/FEV123.pdf", status="Corregir",
                    invoice_type="FEV", invoice_code="FEV123",
                ),
            ],
            "Maria": [
                InvoiceRecord(
                    filename="FEV123.pdf", facturador="Maria",
                    full_path="/b/FEV123.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV123",
                ),
            ],
        }
        result = find_duplicates(invoices)
        assert len(result) == 1
        dup = result[0]
        assert dup["filename"] == "FEV123.pdf"
        assert sorted(dup["facturadores"]) == ["Carlos", "Maria"]
        assert len(dup["paths"]) == 2

    def test_three_way_duplicate(self) -> None:
        """find_duplicates detects same filename in three folders."""
        invoices = {
            "A": [
                InvoiceRecord(
                    filename="FEV99.pdf", facturador="A",
                    full_path="/a/FEV99.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV99",
                ),
            ],
            "B": [
                InvoiceRecord(
                    filename="FEV99.pdf", facturador="B",
                    full_path="/b/FEV99.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV99",
                ),
            ],
            "C": [
                InvoiceRecord(
                    filename="FEV99.pdf", facturador="C",
                    full_path="/c/FEV99.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV99",
                ),
            ],
        }
        result = find_duplicates(invoices)
        assert len(result) == 1
        dup = result[0]
        assert dup["filename"] == "FEV99.pdf"
        assert sorted(dup["facturadores"]) == ["A", "B", "C"]
        assert len(dup["paths"]) == 3

    def test_multiple_duplicates(self) -> None:
        """find_duplicates detects multiple different duplicates."""
        invoices = {
            "Juan": [
                InvoiceRecord(
                    filename="FEV1.pdf", facturador="Juan",
                    full_path="/a/FEV1.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV1",
                ),
                InvoiceRecord(
                    filename="FEV2.pdf", facturador="Juan",
                    full_path="/a/FEV2.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV2",
                ),
            ],
            "Maria": [
                InvoiceRecord(
                    filename="FEV1.pdf", facturador="Maria",
                    full_path="/b/FEV1.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV1",
                ),
            ],
            "Carlos": [
                InvoiceRecord(
                    filename="FEV3.pdf", facturador="Carlos",
                    full_path="/c/FEV3.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="FEV3",
                ),
            ],
        }
        result = find_duplicates(invoices)
        assert len(result) == 1  # Only FEV1.pdf is duplicated
        assert result[0]["filename"] == "FEV1.pdf"

    def test_return_structure(self) -> None:
        """find_duplicates returns list of dicts with expected keys."""
        invoices = {
            "A": [
                InvoiceRecord(
                    filename="dup.pdf", facturador="A",
                    full_path="/a/dup.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="dup",
                ),
            ],
            "B": [
                InvoiceRecord(
                    filename="dup.pdf", facturador="B",
                    full_path="/b/dup.pdf", status="Verificada",
                    invoice_type="FEV", invoice_code="dup",
                ),
            ],
        }
        result = find_duplicates(invoices)
        assert len(result) == 1
        entry = result[0]
        assert "filename" in entry
        assert "facturadores" in entry
        assert "paths" in entry
        assert isinstance(entry["facturadores"], list)
        assert isinstance(entry["paths"], list)
