"""Tests for app/services/monitoreo_carpetas/empty_folder_detector.py."""

from __future__ import annotations

import pytest

from app.services.monitoreo_carpetas.empty_folder_detector import detect_empty


class TestDetectEmpty:
    """Tests for detect_empty()."""

    def test_truly_empty_folder(self) -> None:
        """detect_empty flags folders with no files at all."""
        result = detect_empty("Juan", "/path/LISTAS OK - Juan", [])
        assert len(result) == 1
        assert result[0]["facturador"] == "Juan"
        assert result[0]["folder"] == "/path/LISTAS OK - Juan"
        assert result[0]["reason"] == "empty"

    def test_non_invoice_files_only(self) -> None:
        """detect_empty flags folders with only non-invoice files."""
        # Only .txt files = no invoices
        result = detect_empty(
            "Carlos",
            "/path/CORREGIR - Carlos",
            ["notas.txt", "leeme.log", "datos.csv"],
        )
        assert len(result) == 1

    def test_folder_with_invoices_not_empty(self) -> None:
        """detect_empty does not flag folders with valid invoice files."""
        result = detect_empty(
            "Maria",
            "/path/CAP LISTAS - Maria",
            ["FEV12345.pdf", "CAP001_ABC002.pdf"],
        )
        assert len(result) == 0

    def test_folder_with_mixed_files_not_empty(self) -> None:
        """detect_empty does not flag folders with any invoice PDF."""
        result = detect_empty(
            "Juan",
            "/path/LISTAS OK - Juan",
            ["FEV12345.pdf", "notas.txt", "FEV67890.pdf"],
        )
        assert len(result) == 0

    def test_return_structure(self) -> None:
        """detect_empty returns list of dicts with expected keys."""
        result = detect_empty("Juan", "/path/empty", [])
        assert isinstance(result, list)
        assert len(result) > 0
        entry = result[0]
        assert "facturador" in entry
        assert "folder" in entry
        assert "reason" in entry

    def test_multiple_empty_folders(self) -> None:
        """detect_empty handles multiple empty folders."""
        all_facturadores = {
            "Juan": {"folder": "/path/Juan", "files": ["FEV123.pdf"]},
            "Carlos": {"folder": "/path/Carlos", "files": []},
            "Maria": {"folder": "/path/Maria", "files": ["notas.txt"]},
        }

        all_results: list[dict] = []
        for fact, info in all_facturadores.items():
            all_results.extend(detect_empty(fact, info["folder"], info["files"]))

        assert len(all_results) == 2  # Carlos empty + Maria non-invoice
        facturadores_vacios = {r["facturador"] for r in all_results}
        assert "Carlos" in facturadores_vacios
        assert "Maria" in facturadores_vacios
