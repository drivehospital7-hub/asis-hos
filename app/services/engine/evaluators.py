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


class CodigoEntidadCoincideEvaluator(AtomicEvaluator):
    """Cross-field entity code match: extracts code from entidad_afiliacion
    using regex and compares with codigo_entidad_cobrar.

    Uses the evaluation context to access both fields from the row.
    Designed for the codigo_entidad_vs_entidad_afiliacion detector.
    """

    operator = "ent_code_match"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: Any = None,
    ) -> bool:
        import re
        if context is None:
            return False
        invoice = getattr(context, "invoice_data", {}) or {}

        codigo = str(row_value).strip() if row_value else ""
        entidad_afiliacion = str(invoice.get("entidad_afiliacion", "")).strip()

        if not codigo or not entidad_afiliacion:
            return False

        pattern_str = str(expected) if expected else r"[A-Z0-9]+"
        # Wrap in brace extraction with capture group: {CODE}
        pattern_str = r"\{(%s)\}" % pattern_str
        try:
            pattern = re.compile(pattern_str)
            match = pattern.search(entidad_afiliacion)
            if not match:
                return False
            extracted = match.group(1)
            return extracted.upper() == codigo.upper()
        except re.error:
            return False


class SalaObservacionEvaluator(AtomicEvaluator):
    """Sala de observacion rules for Urgencias — per-row check."""
    operator = "sala_obs_check"
    SALA_CODES = frozenset({"5DSB01", "05DSB01", "129B02", "38114", "38915"})
    ENTITIES_05DSB01 = frozenset({"ESS118", "ESSC18"})

    def evaluate(self, condition, row_value, expected, context=None):
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}
        tipo = str(inv.get("tipo_factura_descripcion", "")).strip()
        if tipo != "Urgencias":
            return False
        code = str(row_value).strip() if row_value else ""
        if code not in self.SALA_CODES:
            return False
        entidad = str(inv.get("codigo_entidad_cobrar", "")).strip()
        tarifario = str(inv.get("tarifario", "")).strip().upper()
        estancia = self._calc_estancia(inv)
        if estancia is None:
            return False
        expected_code = self._codigo_esperado(estancia, entidad, tarifario)
        if expected_code is None:
            return False
        return code != expected_code

    def _calc_estancia(self, inv):
        from datetime import datetime
        try:
            f1, f2 = inv.get("fec_factura"), inv.get("fecha_cierre")
            if not f1 or not f2: return None
            d1 = datetime.strptime(str(f1).strip()[:19], "%Y-%m-%d %H:%M:%S")
            d2 = datetime.strptime(str(f2).strip()[:19], "%Y-%m-%d %H:%M:%S")
            return (d2 - d1).total_seconds() / 3600
        except (ValueError, TypeError):
            return None

    def _codigo_esperado(self, estancia, entidad, tarifario):
        if estancia <= 2:
            return None  # any code besides 5DSB01 is error
        if tarifario == "SOAT":
            return "38114" if estancia > 6 else "38915"
        if estancia > 6:
            return "05DSB01" if entidad in self.ENTITIES_05DSB01 else "129B02"
        return "5DSB01"


class SetContainsAllEvaluator(AtomicEvaluator):
    """Checks if ALL expected values are present in row_value (set ⊆ check).

    operator = "set_contains_all"
    row_value is expected to be a list (from collect_set aggregation).
    expected is a list of values to check for.
    """

    operator = "set_contains_all"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if row_value is None:
            return False
        # Both must be iterable — convert to set for subset check
        row_set = set(row_value)
        expected_set = set(expected) if isinstance(expected, (list, tuple, set)) else {expected}
        return expected_set.issubset(row_set)


class SetIntersectsEvaluator(AtomicEvaluator):
    """Checks if row_value intersects with expected values.

    operator = "set_intersects"
    row_value is expected to be a list (from collect_set aggregation).
    expected is a list of values to check intersection with.
    """

    operator = "set_intersects"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if row_value is None:
            return False
        row_set = set(row_value)
        expected_set = set(expected) if isinstance(expected, (list, tuple, set)) else {expected}
        return bool(row_set & expected_set)


class AllValuesMatchEvaluator(AtomicEvaluator):
    """Checks if ALL pairs in row_value have count >= threshold.

    operator = "all_values_match"
    row_value is a list of dicts with a 'count' key (from collect_value_counts).
    expected is an integer threshold.
    """

    operator = "all_values_match"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        if row_value is None:
            return False
        if not isinstance(row_value, (list, tuple)):
            return False
        threshold = int(expected) if expected is not None else 0
        for item in row_value:
            if not isinstance(item, dict):
                return False
            if item.get("count", 0) < threshold:
                return False
        return True


class CentroCostoCheckEvaluator(AtomicEvaluator):
    """Centro de costo common rules — checks all REGLA1-9 + REVERSE.

    Returns True if ANY rule detects a violation. NOT wrapper makes it MATCH.
    """
    operator = "centro_costo_check"

    def evaluate(self, condition, row_value, expected, context=None):
        if context is None:
            return False
        from app.constants import (
            CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO as COD_DIAG,
            CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS as COD_TRASL,
            LABORATORIO_NO as LAB_NO,
            CENTRO_COSTO_APOYO_DIAGNOSTICO as CC_DIAG,
            CENTRO_COSTO_FARMACIA as CC_FARM,
            CENTRO_COSTO_HOSPITALIZACION_ESTANCIA as CC_HOSP,
            CENTRO_COSTO_QUIROFANO_URGENCIAS as CC_QUIR,
            CENTRO_COSTO_TRASLADOS as CC_TRAS,
            CENTRO_COSTO_PYP_URGENCIAS as CC_PYP,
            VALOR_TARIFARIO_FARMACIA as TAR_FARM,
            CODIGOS_EXCEPTUADOS as EXCEPT,
            CODIGOS_HOSPITALIZACION_ESTANCIA as COD_HOSP,
            CODIGOS_PYP_URGENCIAS as COD_PYP,
            CODIGOS_QUIROFANO_URGENCIAS as COD_QUIR,
        )
        inv = getattr(context, "invoice_data", {}) or {}
        centro = str(inv.get("centro_costo", "")).strip().upper()
        codigo = str(inv.get("codigo", "")).strip().upper()
        cod_tipo = str(inv.get("codigo_tipo_procedimiento", "")).strip().upper()
        lab = str(inv.get("laboratorio", "")).strip().upper()
        tarif = str(inv.get("tarifario", "")).strip().upper()

        if not centro:
            return False

        # REGLA9: Tarifario farmacia → centro=FARMACIA
        if tarif == TAR_FARM and centro != CC_FARM:
            return True
        # REGLA1: Cod=diagnostico + Lab=NO → centro=APOYO_DIAG
        if cod_tipo == COD_DIAG and lab == LAB_NO and codigo not in EXCEPT and centro != CC_DIAG:
            return True
        # REVERSE1: centro=APOYO_DIAG → cod=diag + lab=NO
        if centro == CC_DIAG and (cod_tipo != COD_DIAG or lab != LAB_NO):
            return True
        # REGLA2: Cod=traslados → centro=TRASLADOS
        if cod_tipo == COD_TRASL and centro != CC_TRAS:
            return True
        # REVERSE2: centro=TRASLADOS → cod=traslados
        if centro == CC_TRAS and cod_tipo != COD_TRASL:
            return True
        # REGLA3: Cod PYP → centro=PYP
        if codigo in COD_PYP and centro != CC_PYP:
            return True
        # REVERSE3: centro=PYP → cod PYP
        if centro == CC_PYP and codigo not in COD_PYP:
            return True
        # REGLA4: Cod quirofano → centro=QUIROFANO
        if codigo in COD_QUIR and centro != CC_QUIR:
            return True
        # REVERSE4: centro=QUIROFANO → cod quirofano
        if centro == CC_QUIR and codigo not in COD_QUIR:
            return True
        # REGLA9REVERSE: centro=FARMACIA → tarifario farmacia
        if centro == CC_FARM and tarif != TAR_FARM:
            return True
        # REGLA8: Cod hospitalizacion → centro=HOSPITALIZACION
        if codigo in COD_HOSP and centro != CC_HOSP:
            return True

        return False


class CatalogInEvaluator(AtomicEvaluator):
    """Checks if row_value is in a catalog list stored in the catalogos DB table.

    valor_esperado is the catalog key (e.g. 'profesionales_odontologia').
    The actual list is queried from the catalogos table at evaluation time.
    Requires context.session to be available (DB connection).

    Use this instead of hardcoding lists in conditions for better maintainability.
    """
    operator = "cat_in"

    def evaluate(self, condition, row_value, expected, context=None):
        if context is None or context.session is None:
            from sqlalchemy import text
            return False
        if not isinstance(expected, str) or not expected.strip():
            return False
        from sqlalchemy import text
        try:
            result = context.session.execute(
                text("SELECT value FROM catalogos WHERE key = :key"),
                {"key": expected.strip()}
            ).fetchone()
            if not result:
                return False
            catalog_list = result[0]
            if not isinstance(catalog_list, (list, tuple, set, frozenset)):
                return False
            return row_value in catalog_list
        except Exception:
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
        CodigoEntidadCoincideEvaluator(),
        SalaObservacionEvaluator(),
        CentroCostoCheckEvaluator(),
        CatalogInEvaluator(),
        SetContainsAllEvaluator(),
        SetIntersectsEvaluator(),
        AllValuesMatchEvaluator(),
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
