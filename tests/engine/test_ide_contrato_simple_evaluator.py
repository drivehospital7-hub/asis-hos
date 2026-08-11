"""Tests for IdeContratoSimpleEvaluator — operator 'ide_simple_check'.

Replaces the simple exact-match part of detect_ide_contrato_intramural():
- Pre-loads a dict[(codigo_normalized, entidad_normalized) → expected_ide]
- Each evaluate: builds key from (row_value=codigo, context entidad) → lookup → eq check
- Excludes PYM_INTRAMURAL codes in NUEVA_EPS_NO_CAPITA

Tests use a pre-loaded dict instead of DB for isolation.
"""

from __future__ import annotations

import pytest

from app.services.engine.context import EvaluationContext


class TestIdeContratoSimpleEvaluator:
    """IdeContratoSimpleEvaluator — pre-loaded rules, row-by-row evaluation."""

    @pytest.fixture
    def evaluator(self):
        from app.services.engine.evaluators import IdeContratoSimpleEvaluator
        ev = IdeContratoSimpleEvaluator()
        # Pre-load with a subset of rules
        ev.load_rules({
            ("906340", "EPSS41"): "957",
            ("906127", "EPSS41"): "958",
            ("906340", "EPS037"): "960",
            ("906127", "EPS037"): "961",
            ("906340", "EPSI05"): "986",
            ("906340", "ESS118"): "839",
            ("861801", "EPSS41"): "958",
            ("906340", "ESSC18"): "842",
        })
        return ev

    def test_operator_name(self):
        """Operator name should be 'ide_simple_check'."""
        from app.services.engine.evaluators import IdeContratoSimpleEvaluator
        assert IdeContratoSimpleEvaluator.operator == "ide_simple_check"

    def test_match_exact(self, evaluator):
        """Code+Entity matches a rule with correct IDE → True."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = evaluator.evaluate({}, "906340", "957", context=ctx)
        assert result is True

    def test_no_match_wrong_ide(self, evaluator):
        """Code+Entity matches a rule but IDE is wrong → False."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = evaluator.evaluate({}, "906340", "999", context=ctx)
        assert result is False

    def test_no_rule_for_pair(self, evaluator):
        """Code+Entity without a matching rule → True (skip, no validation)."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "UNKNOWN"})
        result = evaluator.evaluate({}, "906340", "999", context=ctx)
        assert result is True

    def test_normalized_entidad_upper(self, evaluator):
        """Entidad should be normalized to uppercase."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "epss41"})
        result = evaluator.evaluate({}, "906340", "957", context=ctx)
        assert result is True

    def test_normalized_codigo_strip(self, evaluator):
        """Codigo should be stripped of whitespace."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = evaluator.evaluate({}, "  906340  ", "957", context=ctx)
        assert result is True

    def test_no_context_returns_false(self, evaluator):
        """No context → cannot validate, returns False."""
        result = evaluator.evaluate({}, "906340", "957", context=None)
        assert result is False

    def test_none_row_value(self, evaluator):
        """None row_value → returns True (skip)."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = evaluator.evaluate({}, None, "957", context=ctx)
        assert result is True

    def test_empty_entidad(self, evaluator):
        """Empty entidad → returns True (skip)."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": ""})
        result = evaluator.evaluate({}, "906340", "957", context=ctx)
        assert result is True

    def test_invoice_data_none(self, evaluator):
        """invoice_data is None → cannot get entidad → False."""
        ctx = EvaluationContext(invoice_data=None)
        result = evaluator.evaluate({}, "906340", "957", context=ctx)
        assert result is False

    def test_int_ide_values(self, evaluator):
        """IDE values should work as strings even if passed as int."""
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = evaluator.evaluate({}, "906340", 957, context=ctx)
        assert result is True

    def test_register_in_registry(self):
        """Should be auto-registered in EVALUATOR_REGISTRY."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        assert "ide_simple_check" in EVALUATOR_REGISTRY

    def test_evaluate_via_registry(self, evaluator):
        """Evaluate through registry should work."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        reg_ev = EVALUATOR_REGISTRY["ide_simple_check"]
        ctx = EvaluationContext(invoice_data={"codigo_entidad_cobrar": "EPSS41"})
        result = reg_ev.evaluate({}, "906340", "957", context=ctx)
        assert result is True
