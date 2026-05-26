"""Tests for app/services/normalized_rows.py (shared, parametrized builder).

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.normalized_rows import build_normalized_rows


class TestBuildNormalizedRows:
    """Spec: parametrized build_normalized_rows(error_groups, ...) -> list[dict]."""

    def test_empty_error_groups_returns_empty_list(self):
        """Given empty error_groups, returns []."""
        rows = build_normalized_rows(
            error_groups={},
            responsables_map={},
        )
        assert rows == []

    def test_centros_de_costo_row_format(self):
        """Centros de Costo rows have correct tipo_error, descripcion, detalle."""
        error_groups = {
            "Centros de Costo": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "procedimiento": "Test Proc",
                    "centro_actual": "CENTRO_A",
                    "centro_deberia": "CENTRO_B",
                }
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
        )
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "Centros de Costo"
        assert r["factura"] == "FAC-001"
        assert r["descripcion"] == "Centro de costo debería ser CENTRO_B"
        assert r["detalle"] == "CENTRO_A"
        assert r["procedimiento"] == "C001 - Test Proc"

    def test_fec_factura_populated(self):
        """fec_factura_map populates fec_factura field in rows."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fec_factura_map={"FAC-001": "2024-01-15"},
        )
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_empty_when_not_in_map(self):
        """fec_factura is '' when factura not in map."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
        )
        assert rows[0]["fec_factura"] == ""

    def test_responsable_cierra_populated(self):
        """responsables_map populates responsable_cierra field."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={"FAC-001": "John Doe"},
        )
        assert rows[0]["responsable_cierra"] == "John Doe"

    def test_fecha_cierre_vacia_true(self):
        """fecha_cierre_vacia_map sets the boolean field."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fecha_cierre_vacia_map={"FAC-001": True},
        )
        assert rows[0]["fecha_cierre_vacia"] is True

    def test_ide_contrato_row_format(self):
        """IDE Contrato rows: correct tipo_error with ide_contrato description."""
        error_groups = {
            "IDE Contrato": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "procedimiento": "Test Proc",
                    "ide_contrato_actual": "IDE_OLD",
                    "ide_contrato_deberia": "IDE_NEW",
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "IDE Contrato"
        assert r["descripcion"] == "IDE Contrato debería ser IDE_NEW"
        assert r["detalle"] == "IDE_OLD"

    def test_ide_contrato_codigo_no_en_db(self):
        """IDE Contrato with 'Código no en DB' uses short description."""
        error_groups = {
            "IDE Contrato": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "ide_contrato_actual": "N/A",
                    "ide_contrato_deberia": "Código no en DB",
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert rows[0]["descripcion"] == "Código no en DB"

    def test_decimales_row_format(self):
        """Decimales: each factura string becomes a row."""
        error_groups = {
            "Decimales": ["FAC-001", "FAC-002"]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 2
        assert rows[0]["tipo_error"] == "Decimales"
        assert rows[0]["factura"] == "FAC-001"
        assert rows[0]["descripcion"] == "Valores con decimales"

    def test_multiple_error_groups_combined(self):
        """Multiple error groups produce combined rows."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P1", "centro_actual": "A", "centro_deberia": "B"}
            ],
            "IDE Contrato": [
                {"factura": "FAC-002", "codigo": "C002", "ide_contrato_actual": "X", "ide_contrato_deberia": "Y"}
            ],
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 2
        tipos = {r["tipo_error"] for r in rows}
        assert tipos == {"Centros de Costo", "IDE Contrato"}

    def test_unknown_error_type_skipped(self):
        """Unknown tipo_error key is gracefully skipped (design: known types only)."""
        error_groups = {
            "Custom Check": [
                {"factura": "FAC-001", "field_a": "val_a", "field_b": "val_b"}
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        # Unknown keys produce no rows — only known tipo_error labels are processed
        assert rows == []

    def test_none_fec_factura_map_handled(self):
        """None fec_factura_map defaults to empty dict."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fec_factura_map=None,
        )
        assert rows[0]["fec_factura"] == ""
