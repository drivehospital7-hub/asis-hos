"""Unit tests for AtomicEvaluator registry and built-in evaluators.

Truth tables: each evaluator tested with ≥3 cases.
"""

from __future__ import annotations

import pytest


class TestEqEvaluator:
    """Tests for EqEvaluator (operator=eq)."""

    def test_equal_strings(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, "hello", "hello") is True

    def test_different_strings(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, "hello", "world") is False

    def test_equal_integers(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, 42, 42) is True

    def test_different_integers(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, 1, 2) is False

    def test_none_vs_none(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, None, None) is True

    def test_none_vs_value(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["eq"]
        assert evaluator.evaluate({}, None, "hello") is False


class TestGtEvaluator:
    """Tests for GtEvaluator (operator=gt)."""

    def test_greater(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gt"]
        assert evaluator.evaluate({}, 10, 5) is True

    def test_equal(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gt"]
        assert evaluator.evaluate({}, 5, 5) is False

    def test_less(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gt"]
        assert evaluator.evaluate({}, 3, 5) is False

    def test_string_coerced(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gt"]
        assert evaluator.evaluate({}, "10", "5") is True

    def test_float_values(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gt"]
        assert evaluator.evaluate({}, 10.5, 10.0) is True


class TestGteEvaluator:
    """Tests for GteEvaluator (operator=gte)."""

    def test_greater(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gte"]
        assert evaluator.evaluate({}, 10, 5) is True

    def test_equal(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gte"]
        assert evaluator.evaluate({}, 5, 5) is True

    def test_less(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["gte"]
        assert evaluator.evaluate({}, 3, 5) is False


class TestLtEvaluator:
    """Tests for LtEvaluator (operator=lt)."""

    def test_less(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lt"]
        assert evaluator.evaluate({}, 3, 5) is True

    def test_equal(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lt"]
        assert evaluator.evaluate({}, 5, 5) is False

    def test_greater(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lt"]
        assert evaluator.evaluate({}, 10, 5) is False


class TestLteEvaluator:
    """Tests for LteEvaluator (operator=lte)."""

    def test_less(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lte"]
        assert evaluator.evaluate({}, 3, 5) is True

    def test_equal(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lte"]
        assert evaluator.evaluate({}, 5, 5) is True

    def test_greater(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["lte"]
        assert evaluator.evaluate({}, 10, 5) is False


class TestInEvaluator:
    """Tests for InEvaluator (operator=in)."""

    def test_value_in_list(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["in"]
        assert evaluator.evaluate({}, "A", ["A", "B", "C"]) is True

    def test_value_not_in_list(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["in"]
        assert evaluator.evaluate({}, "Z", ["A", "B", "C"]) is False

    def test_numeric_in_list(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["in"]
        assert evaluator.evaluate({}, 42, [1, 42, 99]) is True

    def test_empty_list(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["in"]
        assert evaluator.evaluate({}, "A", []) is False

    def test_none_value(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["in"]
        assert evaluator.evaluate({}, None, ["A", "B"]) is False


class TestContainsEvaluator:
    """Tests for ContainsEvaluator (operator=contains)."""

    def test_substring_match(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["contains"]
        assert evaluator.evaluate({}, "hello world", "hello") is True

    def test_no_match(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["contains"]
        assert evaluator.evaluate({}, "hello world", "xyz") is False

    def test_none_value_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["contains"]
        assert evaluator.evaluate({}, None, "hello") is False

    def test_empty_string(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["contains"]
        assert evaluator.evaluate({}, "", "a") is False


class TestRegistry:
    """Tests for evaluator registry structure."""

    def test_all_builtins_registered(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        expected = {"eq", "gt", "gte", "lt", "lte", "in", "contains"}
        for op in expected:
            assert op in EVALUATOR_REGISTRY, f"Missing evaluator: {op}"

    def test_registry_values_are_atomic_evaluators(self):
        from app.services.engine.evaluators import AtomicEvaluator, EVALUATOR_REGISTRY
        for evaluator in EVALUATOR_REGISTRY.values():
            assert isinstance(evaluator, AtomicEvaluator)

    def test_unknown_operator_returns_none(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        assert "fuzzy_match" not in EVALUATOR_REGISTRY

    def test_evaluators_have_operator_attribute(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        for op, evaluator in EVALUATOR_REGISTRY.items():
            assert evaluator.operator == op
