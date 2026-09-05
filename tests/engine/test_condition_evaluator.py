"""Unit tests for ConditionEvaluator — recursive AND/OR/NOT tree with short-circuit."""

from __future__ import annotations

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_ctx(**invoice_data):
    """Build an EvaluationContext with given invoice data."""
    from app.services.engine.context import EvaluationContext
    return EvaluationContext(invoice_data=invoice_data)


def _atomic(tipo="atomic", operador="eq", fuente_datos=None, valor_esperado=None):
    """Build an atomic condition dict."""
    return {
        "tipo": tipo,
        "operador": operador,
        "fuente_datos": fuente_datos,
        "valor_esperado": valor_esperado,
    }


def _composite(tipo="composite", operador="AND", children=None):
    """Build a composite condition dict with children."""
    return {
        "tipo": tipo,
        "operador": operador,
        "_children": children or [],
    }


def _leaf_eq(path, expected):
    """Shorthand: atomic eq condition."""
    return _atomic(operador="eq", fuente_datos=path, valor_esperado=expected)


class TestConditionEvaluator:
    """Core tree evaluation tests."""

    def test_import_exists(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        assert ConditionEvaluator is not None

    # ── Atomic evaluation ────────────────────────────────────────────────

    def test_atomic_eq_match(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A")
        result = evaluator.evaluate(
            _leaf_eq("invoice.convenio", "A"), ctx
        )
        assert result["outcome"] is True

    def test_atomic_eq_no_match(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="B")
        result = evaluator.evaluate(
            _leaf_eq("invoice.convenio", "A"), ctx
        )
        assert result["outcome"] is False

    def test_atomic_gt_match(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(valor=1500)
        result = evaluator.evaluate(
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
            ctx,
        )
        assert result["outcome"] is True

    def test_atomic_gt_no_match(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(valor=500)
        result = evaluator.evaluate(
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
            ctx,
        )
        assert result["outcome"] is False

    # ── AND composite ────────────────────────────────────────────────────

    def test_and_all_true(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A", valor=1500)
        tree = _composite("composite", "AND", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True

    def test_and_one_false(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A", valor=500)
        tree = _composite("composite", "AND", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is False

    def test_and_all_false(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="B", valor=500)
        tree = _composite("composite", "AND", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is False

    # ── OR composite ─────────────────────────────────────────────────────

    def test_or_all_true(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A", valor=1500)
        tree = _composite("composite", "OR", [
            _leaf_eq("invoice.convenio", "B"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True  # second child true

    def test_or_first_true(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A", valor=500)
        tree = _composite("composite", "OR", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True  # first child true

    def test_or_all_false(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="B", valor=500)
        tree = _composite("composite", "OR", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is False

    # ── NOT composite ────────────────────────────────────────────────────

    def test_not_inverts_true(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A")
        tree = _composite("composite", "NOT", [
            _leaf_eq("invoice.convenio", "B"),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True  # eq false → NOT → true

    def test_not_inverts_false(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A")
        tree = _composite("composite", "NOT", [
            _leaf_eq("invoice.convenio", "A"),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is False  # eq true → NOT → false

    # ── Short-circuit ────────────────────────────────────────────────────

    def test_and_short_circuit(self):
        """AND short-circuits on first false child."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="B", valor=1500)
        # Second child would be true but first is false → AND short-circuits
        tree = _composite("composite", "AND", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is False
        # Verify trace: second child should not have been evaluated
        children = result.get("trace", {}).get("_children", [])
        assert len(children) == 2
        assert children[0]["outcome"] is False
        assert children[1].get("outcome") is None  # NOT evaluated (short-circuited)

    def test_or_short_circuit(self):
        """OR short-circuits on first true child."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A", valor=500)
        tree = _composite("composite", "OR", [
            _leaf_eq("invoice.convenio", "A"),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True
        children = result.get("trace", {}).get("_children", [])
        assert len(children) == 2
        assert children[0]["outcome"] is True
        assert children[1].get("outcome") is None  # NOT evaluated

    # ── Deeply nested trees ──────────────────────────────────────────────

    def test_nested_and_or(self):
        """AND(OR(eq(A), eq(B)), gt(valor, 1000))."""
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="B", valor=1500)
        tree = _composite("composite", "AND", [
            _composite("composite", "OR", [
                _leaf_eq("invoice.convenio", "A"),
                _leaf_eq("invoice.convenio", "B"),
            ]),
            _atomic(operador="gt", fuente_datos="invoice.valor", valor_esperado=1000),
        ])
        result = evaluator.evaluate(tree, ctx)
        assert result["outcome"] is True

    # ── Unknown operator ─────────────────────────────────────────────────

    def test_unknown_operator_returns_error(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(valor=100)
        result = evaluator.evaluate(
            _atomic(operador="fuzzy_match", fuente_datos="invoice.valor", valor_esperado="x"),
            ctx,
        )
        assert result["outcome"] is False
        assert result.get("error") is not None

    # ── Missing data path ────────────────────────────────────────────────

    def test_missing_provider_for_path(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(valor=100)
        result = evaluator.evaluate(
            _atomic(operador="eq", fuente_datos="unknown.some_field", valor_esperado="x"),
            ctx,
        )
        assert result["outcome"] is False

    # ── Result structure ─────────────────────────────────────────────────

    def test_result_has_trace(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A")
        result = evaluator.evaluate(
            _leaf_eq("invoice.convenio", "A"), ctx
        )
        assert "trace" in result
        assert result["trace"]["outcome"] is True

    def test_result_has_outcome_key(self):
        from app.services.engine.condition_evaluator import ConditionEvaluator
        evaluator = ConditionEvaluator()
        ctx = _make_ctx(convenio="A")
        result = evaluator.evaluate(
            _leaf_eq("invoice.convenio", "A"), ctx
        )
        assert "outcome" in result
