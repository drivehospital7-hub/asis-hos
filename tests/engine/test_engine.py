"""Unit tests for RuleEvaluationEngine — orchestrates full evaluation flow."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_condition_dict(cond_dict: dict) -> MagicMock:
    """Convert a condition dict to a MagicMock with attribute access."""
    m = MagicMock()
    for key, value in cond_dict.items():
        setattr(m, key, value)
    return m


def _mock_session_with_rule(rule, conditions=None):
    """Create a mock session that returns a specific rule and its conditions."""
    session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.first.return_value = rule

    # For condition queries, return mock objects with proper attributes
    if conditions:
        cond_mocks = [_make_condition_dict(c) for c in conditions]
        mock_query.all.return_value = cond_mocks
    else:
        mock_query.all.return_value = []

    session.query.return_value = mock_query
    return session


class TestRuleEvaluationEngine:
    """Tests for RuleEvaluationEngine — orchestrator."""

    def test_import_exists(self):
        from app.services.engine.engine import RuleEvaluationEngine
        assert RuleEvaluationEngine is not None

    def test_evaluate_sheet_returns_list(self):
        from app.services.engine.engine import RuleEvaluationEngine
        from app.models import Regla, Condicion
        from openpyxl import Workbook

        # Build a simple rule
        rule = Regla(
            id=1, nombre="test_rule", dominio="odontologia",
            estado="active", version=1, prioridad=10, severidad="error",
        )
        # Condition: eq(convenio, "PyP")
        root_cond = {
            "id": 1, "regla_id": 1, "padre_id": None,
            "tipo": "atomic", "operador": "eq",
            "fuente_datos": "invoice.convenio_facturado",
            "valor_esperado": "PyP", "orden": 0,
        }
        session = _mock_session_with_rule(rule, [root_cond])

        # Create a test worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Test"
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="CONVENIO_FACTURADO")
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="PyP")
        ws.cell(row=3, column=1, value="F002")
        ws.cell(row=3, column=2, value="Asistencial")

        indices = {"numero_factura": 0, "convenio_facturado": 1}

        engine = RuleEvaluationEngine(session)
        results = engine.evaluate_sheet("test_rule", ws, indices)
        assert isinstance(results, list)

    def test_evaluate_sheet_returns_legacy_format(self):
        from app.services.engine.engine import RuleEvaluationEngine
        from app.models import Regla
        from openpyxl import Workbook

        rule = Regla(
            id=1, nombre="test_rule", dominio="odontologia",
            estado="active", version=1, prioridad=10, severidad="error",
        )
        root_cond = {
            "id": 1, "regla_id": 1, "padre_id": None,
            "tipo": "atomic", "operador": "eq",
            "fuente_datos": "invoice.convenio_facturado",
            "valor_esperado": "PyP", "orden": 0,
        }
        session = _mock_session_with_rule(rule, [root_cond])

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="CONVENIO_FACTURADO")
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="PyP")

        indices = {"numero_factura": 0, "convenio_facturado": 1}

        engine = RuleEvaluationEngine(session)
        results = engine.evaluate_sheet("test_rule", ws, indices)

        # Each result should have factura and problema keys
        for r in results:
            assert "factura" in r
            assert "problema" in r

    def test_build_row_context_extracts_cell_values(self):
        from app.services.engine.engine import RuleEvaluationEngine
        from app.models import Regla
        from openpyxl import Workbook

        rule = Regla(
            id=1, nombre="test_rule", dominio="odontologia",
            estado="active", version=1, prioridad=10, severidad="error",
        )
        session = _mock_session_with_rule(rule, [])

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="NUMERO_FACTURA")
        ws.cell(row=1, column=2, value="CONVENIO_FACTURADO")
        ws.cell(row=2, column=1, value="F001")
        ws.cell(row=2, column=2, value="PyP")

        indices = {"numero_factura": 0, "convenio_facturado": 1}

        engine = RuleEvaluationEngine(session)
        row_data, factura = engine._build_row_context(ws, 2, indices)
        assert factura == "F001"
        assert row_data["numero_factura"] == "F001"
        assert row_data["convenio_facturado"] == "PyP"
