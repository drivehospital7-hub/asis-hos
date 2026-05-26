"""Tests para app/services/odontologia/normalized_rows.py — fec_factura.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.odontologia.normalized_rows import build_odontologia_normalized_rows


class TestFecFacturaInNormalizedRows:
    """Spec R1 + R3: normalized rows MUST include fec_factura from mapping."""

    def test_fec_factura_present_in_decimales_row(self):
        """Given a fec_factura_map with a known factura,
        when build_odontologia_normalized_rows is called,
        then the row with that factura MUST have fec_factura set."""
        fec_factura_map = {"FAC-001": "2024-01-15"}
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 1
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_empty_when_factura_not_in_map(self):
        """Given a fec_factura_map that does NOT contain the row's factura,
        when the row is built,
        then fec_factura MUST be an empty string."""
        fec_factura_map = {"FAC-999": "2024-01-15"}
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_empty_with_empty_map(self):
        """Given an empty fec_factura_map,
        when any row is built,
        then fec_factura MUST be an empty string."""
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map={},
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_in_all_row_types(self):
        """Given fec_factura_map with multiple facturas,
        when multiple error types are built,
        then ALL rows MUST have fec_factura populated correctly."""
        fec_factura_map = {
            "FAC-001": "2024-01-15",
            "FAC-002": "2024-01-16",
        }
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[{"factura": "FAC-002", "tipos": "ODT, CON"}],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 2
        assert rows[0]["fec_factura"] == "2024-01-15"
        assert rows[1]["fec_factura"] == "2024-01-16"

    def test_fec_factura_key_exists_on_all_items(self):
        """Given any data,
        when rows are built,
        then EVERY row dict MUST have the 'fec_factura' key."""
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "100"}],
            doble_tipo=[{"factura": "FAC-002", "tipos": "ODT"}],
            ruta_dup=[{"identificacion": "ID-1", "facturas": "FAC-003", "cantidad": 2}],
            profesionales=[{"factura": "FAC-004", "codigo_profesional": "123", "procedimiento": "Test"}],
            cantidades=[{"factura": "FAC-005", "tipo_procedimiento": "ODT", "cantidad": "3"}],
            tipo_id_edad=[{"factura": "FAC-006", "tipo_actual": "CC", "tipo_deberia": "TI"}],
            centro_costo=[{"factura": "FAC-007", "centro_actual": "A", "centro_deberia": "B"}],
            ide_contrato=[{"factura": "FAC-008", "codigo": "C001"}],
            responsable_cierra={},
            fec_factura_map={},
        )
        assert len(rows) == 8
        for row in rows:
            assert "fec_factura" in row, f"Row missing fec_factura: {row}"
