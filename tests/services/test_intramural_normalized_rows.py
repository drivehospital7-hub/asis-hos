"""Tests para app/services/intramural/normalized_rows.py.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.intramural.normalized_rows import (
    build_intramural_normalized_rows,
)


class TestBuildIntramuralNormalizedRows:
    """Tests para build_intramural_normalized_rows."""

    def test_empty_result_when_no_problems(self) -> None:
        """Sin problemas, retorna lista vacía."""
        rows = build_intramural_normalized_rows(responsables_map={})
        assert rows == []

    def test_decimales_row_format(self) -> None:
        """Decimales genera fila con tipo_error 'Decimales'."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            decimales=["FAC-001"],
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo_error"] == "Decimales"
        assert row["factura"] == "FAC-001"
        assert row["descripcion"] == "Valores con decimales"

    def test_tipo_identificacion_edad_row_format(self) -> None:
        """tipo_identificacion_edad genera fila con formato correcto."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            tipo_identificacion_edad=[{
                "factura": "FAC-001",
                "numero_identificacion": "12345",
                "edad_anios": "25",
                "edad_meses": "3",
                "tipo_actual": "CC",
                "tipo_deberia": "TI",
            }],
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo_error"] == "Tipo Identificación / Edad"
        assert row["factura"] == "FAC-001"
        assert "CC" in row["descripcion"]
        assert "TI" in row["descripcion"]
        assert row["procedimiento"] == "12345"
        assert "25" in row["detalle"]

    def test_codigo_entidad_vs_afiliacion_row_format(self) -> None:
        """entidad_afiliacion_comparison genera fila con formato correcto."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            entidad_afiliacion_comparison=[{
                "factura": "FAC-001",
                "codigo_entidad_cobrar": "ESS118",
                "entidad_cobrar_nombre": "ESS118",
                "problema": "Código entidad no coincide con afiliación",
                "entidad_afiliacion": "OTRA EPS",
            }],
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo_error"] == "Código Entidad vs Afiliación"
        assert "ESS118" in row["procedimiento"]
        assert "OTRA EPS" in row["detalle"]

    def test_tipo_usuario_row_format(self) -> None:
        """tipo_usuario genera fila con formato correcto."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            tipo_usuario=[{
                "factura": "FAC-001",
                "tipo_actual": "SUBSIDIADO",
            }],
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["tipo_error"] == "Tipo Usuario"
        assert row["detalle"] == "SUBSIDIADO"
        assert row["procedimiento"] == ""

    def test_multiples_tipos_agrupados(self) -> None:
        """Múltiples tipos de error se agregan todos."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            decimales=["FAC-001"],
            tipo_identificacion_edad=[{
                "factura": "FAC-002",
                "numero_identificacion": "67890",
                "edad_anios": "30",
                "edad_meses": "0",
                "tipo_actual": "CC",
                "tipo_deberia": "CC",
            }],
            tipo_usuario=[{
                "factura": "FAC-003",
                "tipo_actual": "CONTRIBUTIVO",
            }],
            entidad_afiliacion_comparison=[{
                "factura": "FAC-004",
                "codigo_entidad_cobrar": "ESS118",
                "entidad_cobrar_nombre": "ESS118",
                "problema": "No coincide",
                "entidad_afiliacion": "OTRA",
            }],
        )
        assert len(rows) == 4
        tipos = [r["tipo_error"] for r in rows]
        assert "Decimales" in tipos
        assert "Tipo Identificación / Edad" in tipos
        assert "Tipo Usuario" in tipos
        assert "Código Entidad vs Afiliación" in tipos

    def test_responsable_mapeado(self) -> None:
        """Responsable se mapea correctamente desde responsables_map."""
        rows = build_intramural_normalized_rows(
            responsables_map={"FAC-001": "Juan Perez"},
            decimales=["FAC-001"],
        )
        assert rows[0]["responsable_cierra"] == "Juan Perez"

    def test_fec_factura_mapeado(self) -> None:
        """Fecha de factura se mapea desde fec_factura_map."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            decimales=["FAC-001"],
            fec_factura_map={"FAC-001": "2024-01-15"},
        )
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_vacio_si_no_en_map(self) -> None:
        """fec_factura vacío si la factura no está en el map."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            decimales=["FAC-999"],
            fec_factura_map={"FAC-001": "2024-01-15"},
        )
        assert rows[0]["fec_factura"] == ""

    def test_todas_las_filas_tienen_6_columnas(self) -> None:
        """Cada fila tiene: tipo_error, factura, fec_factura,
        responsable_cierra, descripcion, procedimiento, detalle."""
        rows = build_intramural_normalized_rows(
            responsables_map={},
            decimales=["FAC-001"],
            tipo_usuario=[{"factura": "FAC-002", "tipo_actual": "SUBSIDIADO"}],
        )
        expected_keys = {
            "tipo_error",
            "factura",
            "fec_factura",
            "responsable_cierra",
            "descripcion",
            "procedimiento",
            "detalle",
        }
        for row in rows:
            assert set(row.keys()) == expected_keys, (
                f"Row has incorrect keys: {set(row.keys())}"
            )
