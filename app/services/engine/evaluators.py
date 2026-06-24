"""AtomicEvaluator registry and built-in comparison operators.

Each evaluator implements a single comparison: eq, gt, lt, gte, lte, in, contains.
Unknown operators → logged error, never crash.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class AtomicEvaluator(ABC):
    """Base class for atomic condition evaluators.

    operator: str — registry key (e.g., "eq", "gt", "in").
    """

    operator: str = ""

    @abstractmethod
    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        """Compare row_value against expected using this evaluator's logic."""
        ...


class EqEvaluator(AtomicEvaluator):
    """Equality check (==)."""

    operator = "eq"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        return row_value == expected


class GtEvaluator(AtomicEvaluator):
    """Greater-than check (>). Coerces to float for comparison."""

    operator = "gt"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        try:
            return float(row_value) > float(expected)
        except (TypeError, ValueError):
            return False


class GteEvaluator(AtomicEvaluator):
    """Greater-than-or-equal check (>=). Coerces to float."""

    operator = "gte"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        try:
            return float(row_value) >= float(expected)
        except (TypeError, ValueError):
            return False


class LtEvaluator(AtomicEvaluator):
    """Less-than check (<). Coerces to float."""

    operator = "lt"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        try:
            return float(row_value) < float(expected)
        except (TypeError, ValueError):
            return False


class LteEvaluator(AtomicEvaluator):
    """Less-than-or-equal check (<=). Coerces to float."""

    operator = "lte"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        try:
            return float(row_value) <= float(expected)
        except (TypeError, ValueError):
            return False


class InEvaluator(AtomicEvaluator):
    """Membership check: row_value in expected (list)."""

    operator = "in"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        if not isinstance(expected, (list, tuple, set, frozenset)):
            return False
        return row_value in expected


class ContainsEvaluator(AtomicEvaluator):
    """Substring check: expected in str(row_value)."""

    operator = "contains"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        if row_value is None:
            return False
        try:
            return str(expected) in str(row_value)
        except (TypeError, ValueError):
            return False


class RegexEvaluator(AtomicEvaluator):
    """Regex match: re.search(expected, str(row_value))."""

    operator = "regex"

    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool:
        if row_value is None:
            return False
        try:
            import re
            pattern = str(expected) if expected else ""
            if not pattern:
                return False
            return bool(re.search(pattern, str(row_value)))
        except (TypeError, ValueError, re.error):
            return False


# ── Registry ──────────────────────────────────────────────────────────────

EVALUATOR_REGISTRY: dict[str, AtomicEvaluator] = {}


def _register_builtins() -> None:
    """Register all built-in evaluators."""
    builtins = [
        EqEvaluator(),
        GtEvaluator(),
        GteEvaluator(),
        LtEvaluator(),
        LteEvaluator(),
        InEvaluator(),
        ContainsEvaluator(),
        RegexEvaluator(),
    ]
    for ev in builtins:
        EVALUATOR_REGISTRY[ev.operator] = ev


_register_builtins()


def get_evaluator(operator: str) -> AtomicEvaluator | None:
    """Look up an evaluator by operator name. Returns None if unknown."""
    evaluator = EVALUATOR_REGISTRY.get(operator)
    if evaluator is None:
        logger.error("Unknown evaluator operator: %s", operator)
    return evaluator
