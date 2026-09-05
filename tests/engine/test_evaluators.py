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
        expected = {"eq", "gt", "gte", "lt", "lte", "in", "contains", "regex", "regex_extract", "exists_in_db",
                    "set_contains_all", "set_intersects", "all_values_match"}
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


class TestRegexExtractEvaluator:
    """Tests for RegexExtractEvaluator (operator=regex_extract)."""

    def test_extracts_capture_group(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        result = evaluator.evaluate({}, "EMSSANAR - {ESSC18} «Contributivo»", r"\{([A-Z0-9]+)\}")
        assert result is True

    def test_no_match_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        result = evaluator.evaluate({}, "no pattern here", r"\{([A-Z0-9]+)\}")
        assert result is False

    def test_none_text_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        assert evaluator.evaluate({}, None, r"\{([A-Z0-9]+)\}") is False

    def test_empty_pattern_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        assert evaluator.evaluate({}, "text", "") is False

    def test_invalid_regex_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        assert evaluator.evaluate({}, "text", r"[invalid") is False

    def test_no_capture_group_returns_true(self):
        """regex_extract still returns True if pattern matches (even without groups)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        result = evaluator.evaluate({}, "hello world", r"hello")
        assert result is True

    def test_extract_utility_method(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        text = "EMSSANAR - {ESSC18} «Contributivo»"
        extracted = evaluator.extract(text, r"\{([A-Z0-9]+)\}")
        assert extracted == "ESSC18"

    def test_extract_utility_no_match(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["regex_extract"]
        extracted = evaluator.extract("no pattern", r"\{([A-Z0-9]+)\}")
        assert extracted is None


class TestExistsInDBEvaluator:
    """Tests for ExistsInDBEvaluator (operator=exists_in_db)."""

    def test_match_found(self):
        """When DB query returns a row, evaluate returns True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        session = MagicMock()
        session.execute.return_value.fetchone.return_value = (1,)
        ctx = EvaluationContext(session=session)

        result = evaluator.evaluate(
            {},
            "990203",
            {"table": "procedimiento", "field": "cups"},
            context=ctx,
        )
        assert result is True

    def test_no_match_returns_false(self):
        """When DB query returns no rows, evaluate returns False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        session = MagicMock()
        session.execute.return_value.fetchone.return_value = None
        ctx = EvaluationContext(session=session)

        result = evaluator.evaluate(
            {},
            "NONEXIST",
            {"table": "procedimiento", "field": "cups"},
            context=ctx,
        )
        assert result is False

    def test_cache_hit(self):
        """Second lookup for same (table, field, value) uses cache, not DB."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        session = MagicMock()
        session.execute.return_value.fetchone.return_value = (1,)
        ctx = EvaluationContext(session=session)

        # First call — hits DB
        result1 = evaluator.evaluate({}, "990203", {"table": "proc", "field": "cups"}, context=ctx)
        assert result1 is True
        assert session.execute.call_count == 1

        # Second call — cache hit, no DB query
        result2 = evaluator.evaluate({}, "990203", {"table": "proc", "field": "cups"}, context=ctx)
        assert result2 is True
        assert session.execute.call_count == 1  # Still 1

    def test_no_session_returns_false(self):
        """Without a DB session, evaluate returns False gracefully."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        ctx = EvaluationContext(session=None)
        result = evaluator.evaluate(
            {}, "990203", {"table": "proc", "field": "cups"}, context=ctx,
        )
        assert result is False

    def test_none_row_value_returns_false(self):
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        ctx = EvaluationContext(session=MagicMock())
        result = evaluator.evaluate(
            {}, None, {"table": "proc", "field": "cups"}, context=ctx,
        )
        assert result is False

    def test_invalid_expected_dict_returns_false(self):
        """Non-dict or missing keys returns False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        ctx = EvaluationContext(session=MagicMock())

        assert evaluator.evaluate({}, "X", "not_a_dict", context=ctx) is False
        assert evaluator.evaluate({}, "X", {}, context=ctx) is False
        assert evaluator.evaluate({}, "X", {"table": "t"}, context=ctx) is False
        assert evaluator.evaluate({}, "X", {"field": "f"}, context=ctx) is False

    def test_context_passed_to_existing_evaluators_ignored(self):
        """Existing evaluators accept context=None without errors (backward compat)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        eq_eval = EVALUATOR_REGISTRY["eq"]
        result = eq_eval.evaluate({}, "A", "A", context=None)
        assert result is True

    def test_db_error_returns_false_gracefully(self):
        """When DB query throws, returns False (never crashes)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        session = MagicMock()
        session.execute.side_effect = RuntimeError("DB down")
        ctx = EvaluationContext(session=session)

        result = evaluator.evaluate(
            {}, "990203", {"table": "procedimiento", "field": "cups"}, context=ctx,
        )
        assert result is False


class TestSetContainsAllEvaluator:
    """Tests for SetContainsAllEvaluator (operator=set_contains_all).

    set_contains_all: True iff set(row_value) ⊇ set(expected).
    row_value is a list (from collect_set), expected is a list of values.
    """

    def test_full_contain(self):
        """All expected values present → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, ["A", "B", "C"], ["A", "B"]) is True

    def test_partial_overlap(self):
        """Only some expected values present → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, ["A", "B"], ["A", "C"]) is False

    def test_empty_row_value(self):
        """Empty row_value list with non-empty expected → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, [], ["A"]) is False

    def test_empty_expected(self):
        """Empty expected list → True (vacuous truth)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, ["A", "B"], []) is True

    def test_none_row_value(self):
        """None row_value → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, None, ["A"]) is False

    def test_row_value_not_a_list(self):
        """String row_value → set() iterates chars, False likely."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        # set("A,B,C") = {",", "A", "B", "C"} — "A" is in it but this is a degenerate case
        # We test that it doesn't crash and returns a bool
        result = evaluator.evaluate({}, "A,B,C", ["A"])
        assert isinstance(result, bool)

    def test_string_numbers(self):
        """Mixed string/numeric values compared as strings."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_contains_all"]
        assert evaluator.evaluate({}, ["5DSB01", "890701"], ["5DSB01"]) is True


class TestSetIntersectsEvaluator:
    """Tests for SetIntersectsEvaluator (operator=set_intersects).

    set_intersects: True iff set(row_value) ∩ set(expected) ≠ ∅.
    """

    def test_partial_intersect(self):
        """Some values overlap → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, ["A", "B", "C"], ["C", "D"]) is True

    def test_no_intersect(self):
        """No overlapping values → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, ["A", "B"], ["C", "D"]) is False

    def test_full_intersect(self):
        """All values overlap → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, ["A", "B"], ["A", "B"]) is True

    def test_empty_reference(self):
        """Empty expected list → False (no intersection possible)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, ["A", "B"], []) is False

    def test_empty_row_value(self):
        """Empty row_value → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, [], ["A"]) is False

    def test_none_row_value(self):
        """None row_value → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, None, ["A"]) is False

    def test_single_element_match(self):
        """Single element row_value matching expected → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["set_intersects"]
        assert evaluator.evaluate({}, ["5DSB01"], ["5DSB01", "129B02"]) is True


class TestAllValuesMatchEvaluator:
    """Tests for AllValuesMatchEvaluator (operator=all_values_match).

    all_values_match: True iff ALL pairs in row_value have count >= expected.
    row_value is list of dicts with 'count' key.
    expected is an integer threshold.
    """

    def test_all_above_threshold(self):
        """All counts >= threshold → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        data = [
            {"codigo": "A", "cantidad": 1, "count": 3},
            {"codigo": "B", "cantidad": 1, "count": 5},
        ]
        assert evaluator.evaluate({}, data, 2) is True

    def test_some_below_threshold(self):
        """Some counts < threshold → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        data = [
            {"codigo": "A", "cantidad": 1, "count": 1},
            {"codigo": "B", "cantidad": 1, "count": 3},
        ]
        assert evaluator.evaluate({}, data, 2) is False

    def test_empty_list(self):
        """Empty list → True (vacuous truth)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        assert evaluator.evaluate({}, [], 2) is True

    def test_none_row_value(self):
        """None row_value → False."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        assert evaluator.evaluate({}, None, 2) is False

    def test_exact_threshold(self):
        """Count equal to threshold → True."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        data = [
            {"codigo": "A", "cantidad": 1, "count": 2},
        ]
        assert evaluator.evaluate({}, data, 2) is True

    def test_threshold_zero(self):
        """Threshold of 0 → True (all counts >= 0)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        data = [
            {"codigo": "A", "cantidad": 1, "count": 0},
        ]
        assert evaluator.evaluate({}, data, 0) is True

    def test_row_value_not_list(self):
        """String row_value → tries iteration and may raise."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        evaluator = EVALUATOR_REGISTRY["all_values_match"]
        # A string is iterable but has no 'count' key
        assert evaluator.evaluate({}, "not_a_list", 2) is False
        """When DB query throws, returns False (never crashes)."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        from app.services.engine.context import EvaluationContext
        from unittest.mock import MagicMock

        evaluator = EVALUATOR_REGISTRY["exists_in_db"]
        evaluator._cache.clear()

        session = MagicMock()
        session.execute.side_effect = RuntimeError("DB down")
        ctx = EvaluationContext(session=session)

        result = evaluator.evaluate(
            {}, "990203", {"table": "procedimiento", "field": "cups"}, context=ctx,
        )
        assert result is False
