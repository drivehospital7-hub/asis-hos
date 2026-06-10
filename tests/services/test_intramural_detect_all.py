"""Tests for app/services/intramural/detect_all.py.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

import pytest
from openpyxl import Workbook

from app.services.intramural.detect_all import detect_all_problems_intramural


@pytest.fixture
def workbook_minimal() -> Workbook:
    """Crea un workbook con headers mínimos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.cell(row=1, column=1, value="Número Factura")
    return wb


class TestDetectAllProblemsIntramural:
    """Tests para detect_all_problems_intramural."""

    def _run(self, ws, indices):
        result, _ = detect_all_problems_intramural(ws, indices)
        return result

    def test_retorna_dict_con_key_problemas(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "problemas" in result

    def test_retorna_area_intramural(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert result.get("area") == "intramural"

    def test_resultado_incluye_normalizados(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "normalizados" in result["problemas"]
        assert isinstance(result["problemas"]["normalizados"], list)

    def test_missing_columns_present(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "missing_columns" in result

    def test_revision_cantidad_in_resultado(self) -> None:
        """resultado['problemas'] debe incluir 'revision_cantidad'."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        headers = ["Número Factura", "Cód. Equivalente CUPS", "Procedimiento",
                    "Cantidad", "Código Tipo Procedimiento", "Laboratorio"]
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=1, column=col_idx, value=header)
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="X001")
        ws.cell(row=2, column=3, value="Proc A")
        ws.cell(row=2, column=4, value=3)
        ws.cell(row=2, column=5, value="06")
        ws.cell(row=2, column=6, value="Si")

        indices = {
            "numero_factura": 0,
            "codigo": 1,
            "procedimiento": 2,
            "cantidad": 3,
            "codigo_tipo_procedimiento": 4,
            "laboratorio": 5,
        }
        result = self._run(ws, indices)
        assert "revision_cantidad" in result["problemas"]
        assert len(result["problemas"]["revision_cantidad"]) == 1

    def test_revision_cantidad_in_totales(self) -> None:
        """resultado['totales'] debe incluir 'revision_cantidad'."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        headers = ["Número Factura", "Cód. Equivalente CUPS", "Procedimiento",
                    "Cantidad", "Código Tipo Procedimiento", "Laboratorio"]
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=1, column=col_idx, value=header)
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="X001")
        ws.cell(row=2, column=3, value="Proc A")
        ws.cell(row=2, column=4, value=3)
        ws.cell(row=2, column=5, value="06")
        ws.cell(row=2, column=6, value="Si")

        indices = {
            "numero_factura": 0,
            "codigo": 1,
            "procedimiento": 2,
            "cantidad": 3,
            "codigo_tipo_procedimiento": 4,
            "laboratorio": 5,
        }
        result = self._run(ws, indices)
        assert "revision_cantidad" in result["totales"]
        assert result["totales"]["revision_cantidad"] == 1

    def test_revision_cantidad_in_normalized_rows(self) -> None:
        """revision_cantidad items aparecen en normalizados como ⚠️ Revisión."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        headers = ["Número Factura", "Cód. Equivalente CUPS", "Procedimiento",
                    "Cantidad", "Código Tipo Procedimiento", "Laboratorio"]
        for col_idx, header in enumerate(headers, start=1):
            ws.cell(row=1, column=col_idx, value=header)
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="X001")
        ws.cell(row=2, column=3, value="Proc A")
        ws.cell(row=2, column=4, value=3)
        ws.cell(row=2, column=5, value="06")
        ws.cell(row=2, column=6, value="Si")

        indices = {
            "numero_factura": 0,
            "codigo": 1,
            "procedimiento": 2,
            "cantidad": 3,
            "codigo_tipo_procedimiento": 4,
            "laboratorio": 5,
        }
        result = self._run(ws, indices)
        normalizados = result["problemas"]["normalizados"]
        revision_rows = [
            r for r in normalizados if r["tipo_error"] == "⚠️ Revisión Necesaria"
        ]
        assert len(revision_rows) == 1
        assert revision_rows[0]["factura"] == "F001"
        assert "Cant:" in revision_rows[0]["detalle"]

