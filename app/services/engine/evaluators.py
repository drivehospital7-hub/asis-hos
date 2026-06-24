"""AtomicEvaluator registry and built-in comparison operators.

Each evaluator implements a single comparison: eq, gt, lt, gte, lte, in, contains.
Unknown operators → logged error, never crash.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.engine.context import EvaluationContext

logger = logging.getLogger(__name__)


class AtomicEvaluator(ABC):
    """Base class for atomic condition evaluators.

    operator: str — registry key (e.g., "eq", "gt", "in").
    """

    operator: str = ""

    @abstractmethod
    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Compare row_value against expected using this evaluator's logic.

        Args:
            condition: The condition node dict (tipo, operador, fuente_datos, etc).
            row_value: The resolved row value from the data source.
            expected: The expected value from valor_esperado (static or JSONB).
            context: Optional EvaluationContext with DB session for cross-reference evaluators.
        """
        ...


class EqEvaluator(AtomicEvaluator):
    """Equality check (==)."""

    operator = "eq"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        return row_value == expected


class GtEvaluator(AtomicEvaluator):
    """Greater-than check (>). Coerces to float for comparison."""

    operator = "gt"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        try:
            return float(row_value) > float(expected)
        except (TypeError, ValueError):
            return False


class GteEvaluator(AtomicEvaluator):
    """Greater-than-or-equal check (>=). Coerces to float."""

    operator = "gte"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        try:
            return float(row_value) >= float(expected)
        except (TypeError, ValueError):
            return False


class LtEvaluator(AtomicEvaluator):
    """Less-than check (<). Coerces to float."""

    operator = "lt"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        try:
            return float(row_value) < float(expected)
        except (TypeError, ValueError):
            return False


class LteEvaluator(AtomicEvaluator):
    """Less-than-or-equal check (<=). Coerces to float."""

    operator = "lte"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        try:
            return float(row_value) <= float(expected)
        except (TypeError, ValueError):
            return False


class InEvaluator(AtomicEvaluator):
    """Membership check: row_value in expected (list)."""

    operator = "in"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if not isinstance(expected, (list, tuple, set, frozenset)):
            return False
        return row_value in expected


class ContainsEvaluator(AtomicEvaluator):
    """Substring check: expected in str(row_value)."""

    operator = "contains"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if row_value is None:
            return False
        try:
            return str(expected) in str(row_value)
        except (TypeError, ValueError):
            return False


class RegexEvaluator(AtomicEvaluator):
    """Regex match: re.search(expected, str(row_value))."""

    operator = "regex"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if row_value is None:
            return False
        try:
            pattern = str(expected) if expected else ""
            if not pattern:
                return False
            return bool(re.search(pattern, str(row_value)))
        except (TypeError, ValueError, re.error):
            return False


class RegexExtractEvaluator(AtomicEvaluator):
    """Regex extract: returns the first capture group from a regex match.

    operator = "regex_extract"

    Unlike RegexEvaluator (which returns bool), this evaluator extracts
    the first capture group (group(1)) from the match and returns it as
    a string. If there's no match or no capture group, returns None.

    This is designed to be used in combination with other evaluators via
    composite condition nodes where the extracted value is compared using
    a downstream atomic evaluator (eq, in, etc.).

    NOTE: The current engine architecture requires the tree to have a
    provider that can resolve the extracted value. Full integration
    requires a future enhancement to support two-step evaluation
    (extract → compare). For now, this evaluator serves as the
    extraction primitive.
    """

    operator = "regex_extract"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Extract first capture group from regex match.

        Args:
            row_value: The text to search (e.g., entidad_afiliacion text).
            expected: The regex pattern string (e.g., r'\\{([A-Z0-9]+)\\}).

        Returns:
            True if a capture group was found (non-None), False otherwise.
            This allows the evaluator to be used as a gate in condition trees.
        """
        if row_value is None:
            return False
        try:
            pattern = str(expected) if expected else ""
            if not pattern:
                return False
            match = re.search(pattern, str(row_value))
            if match:
                # Store the extracted group in the condition dict for downstream use.
                # This is a bridge mechanism until two-step evaluation is supported.
                condition["_extracted_group"] = match.group(1) if match.groups() else match.group(0)
                return True
            return False
        except (TypeError, ValueError, re.error):
            return False

    def extract(self, text: str, pattern: str) -> str | None:
        """Extract the first capture group from text using the given pattern.

        Utility method for direct use outside the condition evaluation tree.
        Returns the capture group string or None if no match.

        Args:
            text: The text to search.
            pattern: The regex pattern string.

        Returns:
            First capture group as string, or None.
        """
        if not text or not pattern:
            return None
        try:
            match = re.search(pattern, text)
            if match and match.groups():
                return match.group(1)
            return None
        except (TypeError, ValueError, re.error):
            return None


class ExistsInDBEvaluator(AtomicEvaluator):
    """Check if a value exists in a referenced database table.

    operator = "exists_in_db"

    The expected value is a JSONB dict with keys:
        table: str — table name (e.g., "procedimiento")
        field: str — column name to search (e.g., "cups")

    Uses context.session to query the DB. Returns True if at least one
    row matches: SELECT 1 FROM {table} WHERE {field} = :value LIMIT 1.

    Cache: queried values are cached in-memory per evaluator instance
    to avoid repeated DB round-trips for the same (table, field, value).
    Cache is session-scoped — cleared on each new detector instantiation.
    """

    operator = "exists_in_db"

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, str], bool] = {}

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if row_value exists in the referenced DB table/field.

        Args:
            row_value: The value to look up (e.g., a CUPS code).
            expected: Dict with "table" and "field" keys.
            context: EvaluationContext with DB session.

        Returns:
            True if at least one matching row exists, False otherwise.
            Returns False if no session is available or query fails.
        """
        if row_value is None:
            return False
        if not isinstance(expected, dict):
            return False

        table_name = expected.get("table", "")
        field_name = expected.get("field", "")
        if not table_name or not field_name:
            return False

        value_str = str(row_value).strip()
        if not value_str:
            return False

        # Check cache first
        cache_key = (table_name, field_name, value_str)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Must have a DB session
        if context is None or context.session is None:
            logger.warning(
                "exists_in_db: no DB session available for table=%s field=%s",
                table_name, field_name,
            )
            return False

        try:
            from sqlalchemy import text
            query = text(
                f"SELECT 1 FROM {table_name} WHERE {field_name} = :val LIMIT 1"
            )
            result = context.session.execute(query, {"val": value_str}).fetchone()
            exists = result is not None
            self._cache[cache_key] = exists
            return exists
        except Exception as exc:
            logger.exception(
                "exists_in_db query failed: table=%s field=%s value=%s: %s",
                table_name, field_name, value_str, exc,
            )
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
        RegexExtractEvaluator(),
        ExistsInDBEvaluator(),
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
