"""Tests para app/services/intramural/detect_all.py.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

import pytest
from openpyxl import Workbook

from app.constants import AREA_INTRAMURAL


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

    @staticmethod
    def _make_indices(
        extra: dict[str, int | None] | None = None,
    ) -> dict[str, int | None]:
        """Construye un dict de índices con todas las claves esperadas."""
        base: dict[str, int | None] = {
            "numero_factura": None,
            "vlr_subsidiado": None,
            "vlr_procedimiento": None,
            "tipo_identificacion": None,
            "fec_nacimiento": None,
            "codigo_entidad_cobrar": None,
            "entidad_afiliacion": None,
            "tipo_usuario": None,
            "responsable_cierra": None,
            "fec_factura": None,
        }
        if extra:
            base.update(extra)
        return base

    def _run(self, ws, indices):
        """Helper que corre el detector y retorna solo el dict resultado."""
        from app.services.intramural.detect_all import (
            detect_all_problems_intramural,
        )

        result, _ = detect_all_problems_intramural(ws, indices)
        return result

    def test_retorna_dict_con_key_problemas(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe contener key 'problemas'."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert "problemas" in result
        assert isinstance(result["problemas"], dict)

    def test_retorna_dict_con_key_totales(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe contener key 'totales'."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert "totales" in result
        assert isinstance(result["totales"], dict)

    def test_retorna_area_intramural(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe contener 'area' = 'intramural'."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert result.get("area") == AREA_INTRAMURAL

    def test_resultado_incluye_normalizados(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe incluir 'normalizados' en problemas."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert "normalizados" in result["problemas"]
        assert isinstance(result["problemas"]["normalizados"], list)

    def test_resultado_incluye_missing_columns(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe contener 'missing_columns'."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert "missing_columns" in result
        assert isinstance(result["missing_columns"], list)

    def test_incluye_solo_transversales(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado incluye solo detectores transversales (decimales,
        tipo_identificacion_edad, codigo_entidad_vs_afiliacion, tipo_usuario)
        y NINGUN detector de area."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        problemas = result["problemas"]
        transversales_keys = {
            "normalizados",
            "decimales",
            "tipo_identificacion_edad",
            "codigo_entidad_vs_afiliacion",
            "tipo_usuario",
        }
        for key in transversales_keys:
            assert key in problemas, (
                f"Key transversal '{key}' debe estar presente"
            )

        area_keys = {
            "centros_de_costos",
            "ide_contrato",
            "cups_equivalentes",
            "profesionales",
            "mal_capitado",
            "cantidades_urgencias",
            "cantidades_soat_urgencias",
            "cantidades_hospitalizacion",
            "cantidades_soat_hospitalizacion",
            "copago_entidad",
            "duplicados_farmacia",
            "revision_entidad_86",
            "revision_cantidad",
        }
        for key in area_keys:
            assert key not in problemas, (
                f"Key de area '{key}' NO debe estar presente en intramural"
            )

    def test_resultado_incluye_totales_por_tipo(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado debe incluir 'totales_por_tipo' en problemas."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")

        indices = self._make_indices({"numero_factura": 0})
        result = self._run(ws, indices)

        assert "totales_por_tipo" in result["problemas"]
        assert isinstance(result["problemas"]["totales_por_tipo"], dict)

    def test_normalizados_incluyen_fec_factura(
        self, workbook_minimal: Workbook
    ) -> None:
        """Resultado normalizados MUST include 'fec_factura' in every row."""
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        ws.cell(row=2, column=2, value="2024-01-15")
        ws.cell(row=1, column=2, value="Fec. Factura")

        indices = self._make_indices({"numero_factura": 0, "fec_factura": 1})
        result = self._run(ws, indices)
        norm = result["problemas"]["normalizados"]
        for row in norm:
            assert "fec_factura" in row
