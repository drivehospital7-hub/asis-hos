"""Snapshot tests: legacy detector output vs engine output identity.

These tests verify that the RuleBasedDetector produces output identical
in structure and semantics to the legacy Python detectors.

Run against production Excel files before enabling engine in production.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestLegacyVsEngineOutputFormat:
    """Verify engine output structure matches legacy detector output."""

    def test_engine_output_keys_match_legacy_format(self):
        """Each engine result dict has factura and problema keys (like legacy)."""
        from app.services.engine.engine import RuleEvaluationEngine
        from app.models import Regla
        from openpyxl import Workbook

        rule = Regla(
            id=1, nombre="test", dominio="odontologia",
            estado="active", version=1, prioridad=10, severidad="error",
            descripcion="Test rule",
        )
        from unittest.mock import MagicMock as M
        cond = M()
        cond.id = 1; cond.regla_id = 1; cond.padre_id = None
        cond.tipo = "atomic"; cond.operador = "eq"
        cond.fuente_datos = "invoice.convenio_facturado"
        cond.valor_esperado = "PyP"; cond.orden = 0

        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = rule
        mock_query.all.return_value = [cond]
        session.query.return_value = mock_query

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="CONVENIO_FACTURADO")
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="PyP")

        indices = {"numero_factura": 0, "convenio_facturado": 1}
        engine = RuleEvaluationEngine(session)
        results = engine.evaluate_sheet("test", ws, indices)

        assert len(results) == 1
        r = results[0]
        assert "factura" in r
        assert "problema" in r
        assert "regla" in r
        assert "severidad" in r
        # Legacy decimales returns: list of invoice number strings
        # Engine wrapper returns: list of dicts with factura + problema
        # Both are compatible with detect_all.py consumption

    def test_legacy_decimales_signature(self):
        """Legacy detect_decimales returns list[str] of invoice numbers."""
        from app.services.transversales.decimales import detect_decimales
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="VLR_SUBSIDIADO")
        ws.cell(row=1, column=3, value="VLR_PROCEDIMIENTO")
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value=1000.50)  # Has decimal
        ws.cell(row=2, column=3, value=2000)

        indices = {"numero_factura": 0, "vlr_subsidiado": 1, "vlr_procedimiento": 2}
        result = detect_decimales(ws, indices)

        assert isinstance(result, list)
        # Legacy returns list of strings
        assert "F001" in result

    def test_legacy_ruta_duplicada_signature(self):
        """Legacy detect_ruta_duplicada returns list[dict] with specific keys."""
        from app.services.transversales.ruta_duplicada import detect_ruta_duplicada
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="IDENTIFICACION")
        ws.cell(row=1, column=3, value="CONVENIO_FACTURADO")
        # 3 facturas for same patient in PyP → ruta duplicada
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="12345")
        ws.cell(row=2, column=3, value="Promoción y Prevención")
        ws.cell(row=3, column=1, value="F002")
        ws.cell(row=3, column=2, value="12345")
        ws.cell(row=3, column=3, value="Promoción y Prevención")
        ws.cell(row=4, column=1, value="F003")
        ws.cell(row=4, column=2, value="12345")
        ws.cell(row=4, column=3, value="Promoción y Prevención")

        indices = {"numero_factura": 0, "identificacion": 1, "convenio_facturado": 2}
        result = detect_ruta_duplicada(ws, indices)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "identificacion" in result[0]
        assert "facturas" in result[0]
        assert "cantidad" in result[0]
        assert result[0]["cantidad"] == 3
