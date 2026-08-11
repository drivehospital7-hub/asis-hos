"""Unit tests for CupsEquivalentesTransversalEvaluator.

Strict TDD: tests written BEFORE implementation.
Operator: cups_equiv_transversal_check

Uses CODIGOS_CUPS_EQUIVALENTES from cups_equivalentes.py:
906317 → 1906317 (Hepatitis B Prueba rápida)
906249 → 906249PR (VIH Prueba rápida)
"""

from __future__ import annotations

import pytest


class TestCupsEquivalentesTransversalEvaluator:
    """Tests for CupsEquivalentesTransversalEvaluator."""

    @pytest.fixture
    def evaluator(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        return EVALUATOR_REGISTRY["cups_equiv_transversal_check"]

    # ── Equivalent found ────────────────────────────────────────────────

    def test_906317_matches(self, evaluator):
        """Codigo 906317 has equivalent 1906317 → MATCH."""
        assert evaluator.evaluate({}, "906317", None) is True

    def test_906249_matches(self, evaluator):
        """Codigo 906249 has equivalent 906249PR → MATCH."""
        assert evaluator.evaluate({}, "906249", None) is True

    # ── No equivalent ───────────────────────────────────────────────────

    def test_no_equivalent_code(self, evaluator):
        """Codigo 890201 has no known equivalent → NO_MATCH."""
        assert evaluator.evaluate({}, "890201", None) is False

    def test_correct_code_1906317(self, evaluator):
        """Codigo 1906317 is already correct → NO_MATCH (not in mapping)."""
        assert evaluator.evaluate({}, "1906317", None) is False

    def test_correct_code_906249pr(self, evaluator):
        """Codigo 906249PR is already correct → NO_MATCH."""
        assert evaluator.evaluate({}, "906249PR", None) is False

    # ── Edge cases ──────────────────────────────────────────────────────

    def test_none_row_value(self, evaluator):
        """None row_value → NO_MATCH."""
        assert evaluator.evaluate({}, None, None) is False

    def test_empty_string(self, evaluator):
        """Empty string row_value → NO_MATCH."""
        assert evaluator.evaluate({}, "", None) is False

    def test_case_insensitive(self, evaluator):
        """Lowercase '906317' → MATCH (stripped and uppercased)."""
        assert evaluator.evaluate({}, "906317", None) is True

    def test_whitespace_stripped(self, evaluator):
        """Codigo with whitespace ' 906317 ' → MATCH (stripped)."""
        assert evaluator.evaluate({}, " 906317 ", None) is True

    def test_integer_row_value(self, evaluator):
        """Integer 906317 → MATCH."""
        assert evaluator.evaluate({}, 906317, None) is True

    def test_not_in_mapping_returns_false(self, evaluator):
        """Random string not in mapping → NO_MATCH."""
        assert evaluator.evaluate({}, "NOT_A_CODE", None) is False
