"""Tests para app/services/urgencias/normalized_rows.py — fec_factura.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.normalized_rows import build_urgencias_normalized_rows


class TestFecFacturaInUrgenciasNormalizedRows:
    """Spec R1 + R3: urgencias normalized rows MUST include fec_factura."""

    def test_fec_factura_present_in_centro_costo_row(self):
        """Given fec_factura_map with a known factura,
        when build_urgencias_normalized_rows is called,
        then the row MUST have fec_factura set."""
        fec_factura_map = {"FAC-001": "2024-01-15"}
        rows = build_urgencias_normalized_rows(
            problemas_centros=[{"factura": "FAC-001", "codigo": "C001", "procedimiento": "Proc", "centro_actual": "A", "centro_deberia": "B"}],
            problemas_ide_contrato=[],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[],
            cantidades_soat_urgencias=[],
            cantidades_hospitalizacion=[],
            cantidades_soat_hospitalizacion=[],
            responsables_map={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 1
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_empty_when_not_in_map(self):
        """Given fec_factura_map without the row's factura,
        when the row is built,
        then fec_factura MUST be empty string."""
        rows = build_urgencias_normalized_rows(
            problemas_centros=[{"factura": "FAC-001", "codigo": "C001", "procedimiento": "Proc", "centro_actual": "A", "centro_deberia": "B"}],
            problemas_ide_contrato=[],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[],
            cantidades_soat_urgencias=[],
            cantidades_hospitalizacion=[],
            cantidades_soat_hospitalizacion=[],
            responsables_map={},
            fec_factura_map={"FAC-999": "2024-02-01"},
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_empty_with_empty_map(self):
        """Given empty fec_factura_map,
        when row is built,
        then fec_factura MUST be empty string."""
        rows = build_urgencias_normalized_rows(
            problemas_centros=[{"factura": "FAC-001", "codigo": "C001", "procedimiento": "Proc", "centro_actual": "A", "centro_deberia": "B"}],
            problemas_ide_contrato=[],
            problemas_cups_equivalentes=[],
            mal_capitado=[],
            cantidades_urgencias=[],
            cantidades_soat_urgencias=[],
            cantidades_hospitalizacion=[],
            cantidades_soat_hospitalizacion=[],
            responsables_map={},
            fec_factura_map={},
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_key_exists_on_all_row_types(self):
        """Given multiple error types,
        when rows are built,
        then EVERY row MUST have the 'fec_factura' key."""
        fec_factura_map = {"FAC-001": "2024-01-15"}
        rows = build_urgencias_normalized_rows(
            problemas_centros=[{"factura": "FAC-001", "codigo": "C001", "procedimiento": "Proc", "centro_actual": "A", "centro_deberia": "B"}],
            problemas_ide_contrato=[{"factura": "FAC-001", "codigo": "C002", "ide_contrato_actual": "X", "ide_contrato_deberia": "Y"}],
            problemas_cups_equivalentes=[{"factura": "FAC-001", "codigo": "C003", "accion": "Revisar"}],
            mal_capitado=[{"factura": "FAC-001", "codigo": "C004", "observacion": "Mal"}],
            cantidades_urgencias=[{"factura": "FAC-001", "codigo": "C005", "cantidad": "2"}],
            cantidades_soat_urgencias=[{"factura": "FAC-001", "codigo": "C006", "cantidad": "2"}],
            cantidades_hospitalizacion=[{"factura": "FAC-001", "codigo": "C007", "cantidad": "2", "cantidad_esperada": "1"}],
            cantidades_soat_hospitalizacion=[{"factura": "FAC-001", "codigo": "C008", "cantidad": "2", "cantidad_esperada": "1"}],
            responsables_map={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 8
        for row in rows:
            assert "fec_factura" in row, f"Row missing fec_factura: {row}"
            assert row["fec_factura"] == "2024-01-15"
