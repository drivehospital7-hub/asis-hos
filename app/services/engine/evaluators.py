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

# Constants for CupsContratadoEvaluator
from app.constants.urgencias import FACTURADORES_URGENCIAS, VALOR_TARIFARIO_FARMACIA

_FACTURADORES_URGENCIAS_NORM: frozenset[str] = frozenset(
    " ".join(f.upper().split()) for f in FACTURADORES_URGENCIAS
)


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
    """Equality check (==) with type coercion.

    Handles mismatched types between Excel values (str) and stored expected
    values (int/float from JSONB).  Falls back to string comparison when
    numeric coercion is not possible.
    """

    operator = "eq"

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        # Same type — direct comparison
        if type(row_value) is type(expected):
            return row_value == expected

        # Both None
        if row_value is None and expected is None:
            return True
        if row_value is None or expected is None:
            return False

        # Numeric coercion (handles "0" == 0, 0 == 0.0, etc.)
        try:
            return float(row_value) == float(expected)
        except (TypeError, ValueError):
            pass

        # String coercion fallback
        return str(row_value) == str(expected)


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
    """Membership check with string coercion fallback.

    Handles type mismatches between Excel values (e.g. int 1) and stored
    expected values from JSONB (e.g. str "1").  Does NOT do numeric coercion
    because that would conflate distinct values like 3424 and "03424".
    """

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

        # 1. Direct check (same types)
        if row_value in expected:
            return True

        # 2. String coercion: compare as stripped uppercase strings
        row_str = str(row_value).strip().upper() if row_value is not None else ""
        for val in expected:
            if str(val).strip().upper() == row_str:
                return True

        return False


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
    """DEPRECATED — replaced by condition tree (migration 16).

    This evaluator is kept for backward compatibility during the test/rollback
    window. New rules must use the condition tree from 16_sala_observacion_condiciones.sql.

    Known bug: estancia <= 2h returns False (no detection) even when the sala
    code is wrong (the condition tree's sub-rule 6 fixes this).
    """
    operator = "sala_obs_check"
    SALA_CODES = frozenset({"5DSB01", "05DSB01", "129B02", "38114", "38915"})
    ENTITIES_05DSB01 = frozenset({"ESS118", "ESSC18"})

    def evaluate(self, condition, row_value, expected, context=None):
        import warnings
        warnings.warn(
            "SalaObservacionEvaluator is deprecated. "
            "Use condition trees (cat_in + eq) via engine path.",
            DeprecationWarning,
            stacklevel=2,
        )
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
    """DEPRECATED — replaced by condition trees (migrations 14+15).

    This evaluator is kept for backward compatibility during migration.
    New rules must use the condition tree approach instead.
    The evaluator had known bugs: input uppercased but compared against
    mixed-case constants (REGLA1/REGLA9/REVERSE1/REVERSE9 were affected).
    The condition trees fix these bugs by using case-insensitive cat_in.
    """
    operator = "centro_costo_check"

    def evaluate(self, condition, row_value, expected, context=None):
        import warnings
        warnings.warn(
            "CentroCostoCheckEvaluator is deprecated. "
            "Use condition trees (cat_in + eq) via engine path.",
            DeprecationWarning,
            stacklevel=2,
        )
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

        if tarif == TAR_FARM and centro != CC_FARM:
            return True
        if cod_tipo == COD_DIAG and lab == LAB_NO and codigo not in EXCEPT and centro != CC_DIAG:
            return True
        if centro == CC_DIAG and (cod_tipo != COD_DIAG or lab != LAB_NO):
            return True
        if cod_tipo == COD_TRASL and centro != CC_TRAS:
            return True
        if centro == CC_TRAS and cod_tipo != COD_TRASL:
            return True
        if codigo in COD_PYP and centro != CC_PYP:
            return True
        if centro == CC_PYP and codigo not in COD_PYP:
            return True
        if codigo in COD_QUIR and centro != CC_QUIR:
            return True
        if centro == CC_QUIR and codigo not in COD_QUIR:
            return True
        if centro == CC_FARM and tarif != TAR_FARM:
            return True
        if codigo in COD_HOSP and centro != CC_HOSP:
            return True

        return False


class CentroCostoIntramuralEvaluator(AtomicEvaluator):
    """DEPRECATED — replaced by condition trees (migration 15).

    Kept for backward compatibility during migration.
    """
    operator = "centro_costo_intramural"

    def evaluate(self, condition, row_value, expected, context=None):
        import warnings
        warnings.warn(
            "CentroCostoIntramuralEvaluator is deprecated. "
            "Use condition trees (cat_in + eq) via engine path.",
            DeprecationWarning,
            stacklevel=2,
        )
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
            CENTRO_COSTO_URGENCIAS as CC_URG,
            VALOR_TARIFARIO_FARMACIA as TAR_FARM,
            CODIGOS_EXCEPTUADOS as EXCEPT,
            CODIGOS_HOSPITALIZACION_ESTANCIA as COD_HOSP,
            CODIGOS_PYP_URGENCIAS as COD_PYP,
            CODIGOS_QUIROFANO_URGENCIAS as COD_QUIR,
            FACTURADORES_URGENCIAS as _FACTURADORES,
            CENTRO_COSTO_SALUD_PUBLICA as CC_SALUD,
            CENTRO_COSTO_AMBULATORIO as CC_AMB,
            CENTROS_COSTO_PYP_INTRAMURAL as CC_PYP_INTRA,
            CENTROS_COSTO_LABORATORIO_VALIDOS as CC_LAB,
            CODIGOS_EXCLUIDOS_VACUNACION as EXCL_VAC,
            CODIGOS_EXCEPTUADOS_AMBULATORIO as EXC_AMB,
            CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS as EXC_RESP,
            CODIGO_TIPO_PROCEDIMIENTO_VACUNACION as TIPO_VAC,
            CODIGOS_TIPO_PROCEDIMIENTO_AMBULATORIO as TIPO_AMB,
            CODIGOS_TIPO_PROCEDIMIENTO_LABORATORIO as TIPO_LAB,
            LABORATORIO_SI as LAB_SI,
        )
        _FACTURADORES_URGENCIAS_NORM = frozenset(
            " ".join(f.upper().split()) for f in _FACTURADORES
        )

        inv = getattr(context, "invoice_data", {}) or {}
        centro = str(inv.get("centro_costo", "")).strip().upper()
        codigo = str(inv.get("codigo", "")).strip().upper()
        cod_tipo = str(inv.get("codigo_tipo_procedimiento", "")).strip().upper()
        lab = str(inv.get("laboratorio", "")).strip()
        tarif = str(inv.get("tarifario", "")).strip()
        responsable = str(inv.get("responsable_cierra", "")).strip()

        if not centro:
            return False

        # ── Common rules (without REGLA3/REVERSE3) ──
        if tarif.upper() == TAR_FARM.upper() and centro != CC_FARM:
            return True
        if cod_tipo == COD_DIAG and lab.upper() == LAB_NO.upper() and codigo not in EXCEPT and centro != CC_DIAG:
            return True
        if centro == CC_DIAG and (cod_tipo != COD_DIAG or lab.upper() != LAB_NO.upper()):
            return True
        if cod_tipo == COD_TRASL and centro != CC_TRAS:
            return True
        if centro == CC_TRAS and cod_tipo != COD_TRASL:
            return True
        if codigo in COD_QUIR and centro != CC_QUIR:
            return True
        if centro == CC_QUIR and codigo not in COD_QUIR:
            return True
        if centro == CC_FARM and tarif.upper() != TAR_FARM.upper():
            return True
        if codigo in COD_HOSP and centro != CC_HOSP:
            return True

        # ── Intramural-specific rules ──
        if codigo in COD_PYP and centro not in CC_PYP_INTRA:
            return True
        if centro in CC_PYP_INTRA and codigo not in COD_PYP:
            return True
        if (
            cod_tipo in TIPO_LAB
            and lab.upper() == LAB_SI.upper()
            and centro not in CC_LAB
        ):
            return True
        if centro in CC_LAB:
            es_exceptuado = codigo in EXCEPT
            if cod_tipo not in TIPO_LAB or (not es_exceptuado and lab.upper() != LAB_SI.upper()):
                return True
        if (
            cod_tipo == TIPO_VAC
            and codigo not in EXCL_VAC
            and codigo not in COD_PYP
            and centro != CC_SALUD
            and not (cod_tipo in TIPO_LAB and lab.upper() == LAB_SI.upper())
        ):
            return True
        if centro == CC_SALUD:
            if cod_tipo != TIPO_VAC or codigo in EXCL_VAC:
                return True
        if (
            cod_tipo in TIPO_AMB
            and codigo not in EXC_AMB
            and centro != CC_AMB
        ):
            return True
        if centro == CC_AMB and cod_tipo not in TIPO_AMB:
            return True

        responsable_norm = " ".join(responsable.upper().split()) if responsable else ""
        CENTROS_RESPONSABLE = {CC_URG, CC_HOSP}
        if (
            responsable_norm
            and responsable_norm in _FACTURADORES_URGENCIAS_NORM
            and cod_tipo in ("01", "04")
            and codigo not in EXC_RESP
            and centro not in CENTROS_RESPONSABLE
        ):
            return True

        return False


class RevisionCantidadIntramuralEvaluator(AtomicEvaluator):
    """Cascade threshold check for Intramural quantity revisions.

    Operator: revision_cantidad_intramural

    Returns True if cantidad exceeds the applicable threshold (detection = problem).

    Cascade (first match wins):
    1. tipo=02 + Lab=No → Cant > 2
    2. tipo=03/04 → Cant > 12
    3. General → Cant > 1

    Before cascade, checks CODIGOS_LIMITE_ESPECIFICO_INTRAMURAL:
    if codigo has a specific limit and cantidad <= limit → return False.
    If cantidad exceeds specific limit → falls through to cascade.
    """
    operator = "revision_cantidad_intramural"

    def evaluate(self, condition, row_value, expected, context=None):
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}
        if not inv:
            return False

        cantidad = row_value
        if cantidad is None:
            return False
        try:
            cantidad = float(cantidad)
        except (TypeError, ValueError):
            return False

        codigo_tipo = str(inv.get("codigo_tipo_procedimiento", "")).strip()
        laboratorio = str(inv.get("laboratorio", "")).strip()
        codigo = str(inv.get("codigo", "")).strip().upper()

        from app.constants.intramural import (
            CODIGOS_LIMITE_ESPECIFICO_INTRAMURAL as LIMITES,
            CODIGO_TIPO_PROC_02 as TIPO_02,
            CODIGOS_TIPO_PROC_03_04 as TIPOS_03_04,
            LABORATORIO_NO as LAB_NO,
            CANTIDAD_MAX_02_NO_LAB as MAX_02,
            CANTIDAD_MAX_03_04 as MAX_03_04,
            CANTIDAD_MAX_GENERAL_INTRAMURAL as MAX_GEN,
        )

        # Check specific code limit FIRST (exact match with legacy behavior)
        if codigo in LIMITES:
            max_cant = LIMITES[codigo]
            if cantidad <= max_cant:
                return False
            # If exceeds specific limit, fall through to cascade

        # Rule 1: tipo=02 + Lab=No → Cant > 2
        if codigo_tipo == TIPO_02 and laboratorio == LAB_NO:
            return cantidad > MAX_02

        # Rule 2: tipo=03/04 → Cant > 12
        if codigo_tipo in TIPOS_03_04:
            return cantidad > MAX_03_04

        # Rule 3 (general): → Cant > 1
        return cantidad > MAX_GEN


class CronogramaCheckEvaluator(AtomicEvaluator):
    """Valida profesional bacterióloga contra cronograma del día para Intramural.

    Operator: cronograma_check
    row_value: codigo_profesional from sheet
    expected: dict with filter params or None

    Lógica completa de detect_bacteriologas_cronograma legacy:
    1. Filtros: solo Intramural, tipo in {"02","05"}, tipo=02 requiere lab="Si",
       código not in EXCEPCIONES_BACTERIOLOGA
    2. Bypass: responsable in FACTURADORES_URGENCIAS → no error
    3. Bypass: codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA → no error
    4. Parse fec_factura → date
    5. Siglas filter: Chapuel→PYM, Tapia/Ordoñez→CE, default→CE|PYM
    6. Cache de turnos por (mes, año, día, siglas_filter)
    7. Resolver nombres del cronograma a códigos via _NOMBRE_A_CODIGO
    8. Si profesional no está en turno → True (detection)
    """
    operator = "cronograma_check"

    def __init__(self) -> None:
        self._cronograma_cache: dict[tuple[int, int, int, frozenset[str] | None], list[dict]] = {}

    def evaluate(
        self,
        condition: dict,
        row_value: str | None,
        expected: object | None = None,
        context: EvaluationContext | None = None,
    ) -> bool:
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}

        codigo_prof = str(row_value).strip() if row_value else ""
        if not codigo_prof:
            return False

        # 1. Filter: solo Intramural
        tipo_factura = str(inv.get("tipo_factura_descripcion", "")).strip()
        if tipo_factura != "Intramural":
            return False

        # 2. Filter: tipo in {"02","05"}
        tipo_proc = str(inv.get("codigo_tipo_procedimiento", "")).strip()
        if tipo_proc not in ("02", "05"):
            return False

        # 3. tipo="02" requiere lab="Si"
        if tipo_proc == "02":
            lab = str(inv.get("laboratorio", "")).strip().upper()
            if lab not in ("SI", "SÍ"):
                return False

        # 4. Filter: codigo not in EXCEPCIONES_BACTERIOLOGA
        from app.constants.urgencias import EXCEPCIONES_BACTERIOLOGA
        codigo = str(inv.get("codigo", "")).strip()
        if codigo in EXCEPCIONES_BACTERIOLOGA:
            return False

        # 5. Bypass: responsable in FACTURADORES_URGENCIAS → bypass total
        responsable = str(inv.get("responsable_cierra", "")).strip()
        responsable_norm = " ".join(responsable.upper().split()) if responsable else ""
        if responsable_norm and responsable_norm in _FACTURADORES_URGENCIAS_NORM:
            return False

        # 6. Bypass: codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA
        from app.constants.intramural import PROFESIONALES_EXCEPTUADOS_CRONOGRAMA
        if codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA:
            return False

        # 7. Parse fec_factura
        fec_raw = inv.get("fec_factura")
        fecha = self._parse_fecha(fec_raw)
        if fecha is None:
            return False

        # 8. Determine siglas_filter
        siglas_filter: frozenset[str] | None = None  # default: CE|PYM
        responsable_full = " ".join((responsable or "").upper().split())
        if "CHAPUEL" in responsable_full:
            siglas_filter = frozenset({"PYM"})
        elif "TAPIA" in responsable_full or "ORDOÑEZ" in responsable_full:
            siglas_filter = frozenset({"CE"})

        # 9. Get turnos with instance-level cache
        cache_key = (fecha.month, fecha.year, fecha.day, siglas_filter)
        if cache_key not in self._cronograma_cache:
            from app.services.cronograma_bacteriologas_service import get_turno_del_dia
            turnos = get_turno_del_dia(
                fecha.month, fecha.year, fecha.day,
                siglas_filter=set(siglas_filter) if siglas_filter else None,
            )
            self._cronograma_cache[cache_key] = turnos

        turnos = self._cronograma_cache[cache_key]
        if not turnos:
            return False  # No hay cronograma → skip sin error

        # 10. Resolve cronograma names to codes via _NOMBRE_A_CODIGO
        from app.services.intramural.bacteriologas_cronograma import _NOMBRE_A_CODIGO
        codigos_en_turno: set[str] = set()
        for t in turnos:
            nombre = t.get("nombre", "").strip().upper()
            if nombre:
                cod = _NOMBRE_A_CODIGO.get(nombre)
                if cod:
                    codigos_en_turno.add(cod)

        # 11. Verify professional is in turno
        if codigo_prof not in codigos_en_turno:
            return True  # MATCH = detection (problema encontrado)

        return False  # En turno → no detection

    @staticmethod
    def _parse_fecha(val: object) -> object | None:
        """Parse a date value from multiple formats.
        
        Matches the legacy _parse_fecha from bacteriologas_cronograma.py.
        Returns a date object or None if unparseable.
        """
        from datetime import date, datetime, timedelta

        if val is None:
            return None
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            val_stripped = val.strip()
            if not val_stripped:
                return None
            try:
                return datetime.strptime(val_stripped, "%Y-%m-%d").date()
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(val_stripped).date()
            except ValueError:
                pass
            for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
                try:
                    return datetime.strptime(val_stripped, fmt).date()
                except ValueError:
                    continue
            return None
        if isinstance(val, (int, float)):
            try:
                excel_epoch = datetime(1899, 12, 30)
                return (excel_epoch + timedelta(days=int(val))).date()
            except (ValueError, OverflowError):
                return None
        return None


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

            # 1. Direct check (same types)
            if row_value in catalog_list:
                return True

            # 2. Normalization fallback: match InEvaluator behavior — strip + upper
            row_str = str(row_value).strip().upper() if row_value is not None else ""
            for val in catalog_list:
                if str(val).strip().upper() == row_str:
                    return True

            return False
        except Exception:
            return False


class CupsContratadoEvaluator(AtomicEvaluator):
    """Check if a CUPS is properly contracted for the entity.

    operator = "cups_contratado"

    Pre-loads 4 DB datasets on first evaluate(), then checks each row
    against the contracted pairs, applying the same 6 exception branches
    as the legacy detector.

    Returns True when properly contracted (NOT inverts to MATCH).
    """

    operator = "cups_contratado"

    def __init__(self) -> None:
        self._loaded: bool = False
        self._pares_validos: set[tuple[str, str]] = set()
        self._eps_map: dict[str, str] = {}
        self._nota_urgencias_cups: set[str] = set()
        self._nota_cap_cups: dict[int, set[str]] = {}
        self._entidades_con_datos: set[str] = set()

    # ── Public ──────────────────────────────────────────────────────────────

    def evaluate(
        self,
        condition: dict,
        row_value: str | None,
        expected: object | None = None,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if the CUPS is properly contracted.

        Returns True if contracted (no detection), False if not contracted (detection).
        """
        if context is None:
            return False

        codigo = str(row_value).strip().upper() if row_value else ""
        if not codigo:
            return False

        inv = context.invoice_data or {}

        # ── Exception chain (matches legacy detector order) ─────────────────
        # 1. Farmacia skip (checked before cod_entidad, matching legacy)
        tarifario = str(inv.get("tarifario", "")).strip()
        if tarifario == VALOR_TARIFARIO_FARMACIA:
            return True

        cod_entidad = str(inv.get("codigo_entidad_cobrar", "")).strip().upper()
        if not cod_entidad:
            return False

        # Pre-load data on first call
        if not self._loaded and context.session is not None:
            self._preload_data(context.session)

        responsable = str(inv.get("responsable_cierra", "")).strip()
        responsable_norm = " ".join(responsable.upper().split()) if responsable else ""

        # 2. Urgencias facturador: responsable in FACTURADORES_URGENCIAS
        if responsable_norm and responsable_norm in _FACTURADORES_URGENCIAS_NORM:
            if codigo in self._nota_urgencias_cups:
                return True

        # 3. CAP + ESS118 → check nota_cap[3] only
        factura_str = str(inv.get("numero_factura", "")).strip().upper()
        if factura_str.startswith("CAP") and cod_entidad == "ESS118":
            cap_set = self._nota_cap_cups.get(3, set())
            if codigo in cap_set:
                return True
            return False  # Error directo — no cae a pares_validos

        # 4. CAP + EPSS41 → check nota_cap[2] only
        if factura_str.startswith("CAP") and cod_entidad == "EPSS41":
            cap_set = self._nota_cap_cups.get(2, set())
            if codigo in cap_set:
                return True
            return False  # Error directo

        # 5. Entidad sin datos en DB → skip
        if cod_entidad not in self._entidades_con_datos:
            return True

        # 6. Normal check: (entidad, codigo) in pares_validos
        if (cod_entidad, codigo) in self._pares_validos:
            return True

        # 7. Fallback: try codigo_equiv
        codigo_equiv = str(inv.get("codigo_equiv", "")).strip().upper()
        if codigo_equiv and (cod_entidad, codigo_equiv) in self._pares_validos:
            return True

        # 8. FEV autorizado
        if factura_str.startswith("FEV") and cod_entidad in ("EPS037", "EPSS41"):
            return True

        # 9. Not contracted
        return False

    # ── Private ─────────────────────────────────────────────────────────────

    def _preload_data(self, session: Any) -> None:
        """Pre-load all DB datasets needed for evaluation.

        Runs 4 queries:
          1. 5-table JOIN → pares_validos + entidades_con_datos
          2. eps_contratado list → eps_map
          3. nota_hoja id=1,27 → nota_urgencias_cups
          4. nota_hoja id=2,3 → nota_cap_cups
        """
        if self._loaded:
            return

        try:
            from app.database import Session as SessType  # noqa: F401 — type marker
            from app.models import (
                EpsContratado,
                EpsNota,
                NotaHoja,
                NotasTecnicas,
                Procedimiento,
            )

            # Query 1: 5-table JOIN → pares_validos
            results = (
                session.query(EpsContratado, Procedimiento)
                .join(EpsNota, EpsNota.id_eps_contratado == EpsContratado.id)
                .join(NotaHoja, NotaHoja.id == EpsNota.id_nota_hoja)
                .join(NotasTecnicas, NotasTecnicas.id_nota_hoja == NotaHoja.id)
                .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
                .all()
            )

            for ec, proc in results:
                cod_key = ec.cod_contrato.strip().upper()
                cups_key = proc.cups.strip().upper()
                self._pares_validos.add((cod_key, cups_key))
                self._entidades_con_datos.add(cod_key)

            # Query 2: eps_map
            eps_list = session.query(EpsContratado).all()
            for ec in eps_list:
                self._eps_map[ec.cod_contrato.strip().upper()] = ec.eps

            # Query 3: nota_hoja id=1,27 (urgencias)
            nota_urgencias = (
                session.query(Procedimiento)
                .join(NotasTecnicas, NotasTecnicas.id_procedimiento == Procedimiento.id)
                .filter(NotasTecnicas.id_nota_hoja.in_([1, 27]))
                .all()
            )
            for p in nota_urgencias:
                self._nota_urgencias_cups.add(p.cups.strip().upper())

            # Query 4: nota_hoja id=2,3 (CAP)
            cap_results = (
                session.query(NotasTecnicas.id_nota_hoja, Procedimiento.cups)
                .join(Procedimiento, Procedimiento.id == NotasTecnicas.id_procedimiento)
                .filter(NotasTecnicas.id_nota_hoja.in_([2, 3]))
                .all()
            )
            self._nota_cap_cups = {2: set(), 3: set()}
            for nt_id, cups_val in cap_results:
                self._nota_cap_cups[nt_id].add(cups_val.strip().upper())

            self._loaded = True

        except Exception as exc:
            logger.exception(
                "CupsContratadoEvaluator._preload_data failed: %s", exc
            )
            # Mark as loaded to avoid retrying on every row
            self._loaded = True


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
        CentroCostoCheckEvaluator(),
        CentroCostoIntramuralEvaluator(),
        RevisionCantidadIntramuralEvaluator(),
        CronogramaCheckEvaluator(),
        CatalogInEvaluator(),
        SetContainsAllEvaluator(),
        SetIntersectsEvaluator(),
        AllValuesMatchEvaluator(),
        CupsContratadoEvaluator(),
        IdeContratoSimpleEvaluator(),
        PymRutasDxEvaluator(),
        RevisionCantidadUrgenciasEvaluator(),
        CupsEquivalentesTransversalEvaluator(),
    ]
    for ev in builtins:
        EVALUATOR_REGISTRY[ev.operator] = ev


# NOTE: _register_builtins() is called at the end of this module
# after ALL evaluator classes are defined.


def get_evaluator(operator: str) -> AtomicEvaluator | None:
    """Look up an evaluator by operator name. Returns None if unknown."""
    evaluator = EVALUATOR_REGISTRY.get(operator)
    if evaluator is None:
        logger.error("Unknown evaluator operator: %s", operator)
    return evaluator

class RevisionCantidadUrgenciasEvaluator(AtomicEvaluator):
    """Cascade threshold check for Urgencias quantity revisions.

    Operator: revision_cantidad_urgencias_check

    Returns True if cantidad exceeds the applicable threshold (detection = problem).

    Cascade (first match wins, mirrors detect_revision_cantidad_urgencias):
    1. tipo_factura_descripcion != "Urgencias" → NO_MATCH (skip)
    2. codigo in CODIGOS_REVISION_CANTIDAD_EXENTOS → NO_MATCH
    3. codigo in CODIGOS_LIMITE_ESPECIFICO:
       - cantidad <= limit → NO_MATCH
       - cantidad > limit → fall through to cascade
    4. tipo=02 + Lab=No:
       - codigo=903883: Cant > 5 → MATCH
       - general: Cant > 2 → MATCH
    5. tipo in 09/12:
       - codigo=V03AN0101: NO_MATCH (exempt)
       - Cant > 20 → MATCH
    6. General: Cant > 1 → MATCH
    """

    operator = "revision_cantidad_urgencias_check"

    def evaluate(
        self,
        condition: dict,
        row_value: object,
        expected: object = None,
        context: EvaluationContext | None = None,
    ) -> bool:
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}
        if not inv:
            return False

        # 1. Only applies to Urgencias
        tipo = str(inv.get("tipo_factura_descripcion", "")).strip()
        if tipo != "Urgencias":
            return False

        cantidad = row_value
        if cantidad is None:
            return False
        try:
            cantidad = float(cantidad)
        except (TypeError, ValueError):
            return False

        codigo = str(inv.get("codigo", "")).strip().upper()
        codigo_tipo = str(inv.get("codigo_tipo_procedimiento", "")).strip()
        laboratorio = str(inv.get("laboratorio", "")).strip()

        from app.constants.urgencias import (
            CODIGOS_REVISION_CANTIDAD_EXENTOS as EXENTOS,
            CODIGOS_LIMITE_ESPECIFICO as LIMITES,
            CODIGO_TIPO_PROCEDIMIENTO_REVISION_LAB as TIPO_02,
            LABORATORIO_REVISION_EXENTO as LAB_NO,
            CODIGOS_TIPO_PROC_09_12 as TIPOS_09_12,
            CODIGO_EXENTO_V03AN0101 as V03,
            CODIGO_ESPECIAL_02_LAB as COD_903883,
            CANTIDAD_MAX_02_LAB as MAX_02_LAB,
            CANTIDAD_MAX_02_LAB_903883 as MAX_903883,
            CANTIDAD_MAX_09_12 as MAX_09_12,
        )

        # 2. Exempt codes → NO_MATCH
        if codigo in EXENTOS:
            return False

        # 3. Specific code limits → check, fall through if exceeded
        if codigo in LIMITES:
            if cantidad <= LIMITES[codigo]:
                return False
            # If exceeds, fall through to cascade

        # 4. tipo=02 + Lab=No
        if codigo_tipo == TIPO_02 and laboratorio == LAB_NO:
            if codigo == COD_903883:
                return cantidad > MAX_903883
            return cantidad > MAX_02_LAB

        # 5. tipo in 09/12
        if codigo_tipo in TIPOS_09_12:
            if codigo == V03:
                return False
            return cantidad > MAX_09_12

        # 6. General: Cant > 1
        return cantidad > 1


class CupsEquivalentesTransversalEvaluator(AtomicEvaluator):
    """Checks if CUPS code has a known equivalent replacement.

    Operator: cups_equiv_transversal_check

    Returns True if codigo has an equivalent in CODIGOS_CUPS_EQUIVALENTES
    (detection = should replace).
    row_value: codigo from invoice.

    The mapping is static (normative):
    906317 → 1906317 (Hepatitis B Prueba rápida)
    906249 → 906249PR (VIH Prueba rápida)
    """

    operator = "cups_equiv_transversal_check"

    def evaluate(
        self,
        condition: dict,
        row_value: object,
        expected: object = None,
        context: EvaluationContext | None = None,
    ) -> bool:
        codigo = str(row_value).strip().upper() if row_value else ""
        if not codigo:
            return False

        from app.services.transversales.cups_equivalentes import (
            CODIGOS_CUPS_EQUIVALENTES,
        )
        return codigo in CODIGOS_CUPS_EQUIVALENTES


class IdeContratoSimpleEvaluator(AtomicEvaluator):
    """Pre-loaded lookup: (codigo, entidad) -> expected IDE.

    operator = "ide_simple_check"

    Pre-loads a dict[(codigo_norm, entidad_norm) -> expected_ide] from the
    catalogos DB table (key='ide_simple_rules') or from an in-memory dict
    via load_rules(). If no rule matches the (codigo, entidad) pair, returns
    True (skip no validation for that pair).

    Expected value passed to evaluate() is the actual IDE from the row.
    Returns True if it matches the pre-loaded expected value.
    """

    operator = "ide_simple_check"

    def __init__(self) -> None:
        self._rules: dict[tuple[str, str], str] = {}
        self._loaded: bool = False

    def load_rules(self, rules: dict[tuple[str, str], str]) -> None:
        """Pre-load rules from a dict (for testing or in-memory use)."""
        self._rules = {
            (k[0].strip().upper(), k[1].strip().upper()): str(v).strip()
            for k, v in rules.items()
        }
        self._loaded = True

    def _load_from_db(self, session: Any, catalog_key: str = "ide_simple_rules") -> None:
        """Pre-load rules from the catalogos DB table."""
        if self._loaded:
            return
        try:
            from sqlalchemy import text
            result = session.execute(
                text("SELECT value FROM catalogos WHERE key = :key"),
                {"key": catalog_key},
            ).fetchone()
            if result and isinstance(result[0], list):
                for row_list in result[0]:
                    if isinstance(row_list, (list, tuple)) and len(row_list) >= 3:
                        codigo = str(row_list[0]).strip().upper()
                        entidad = str(row_list[1]).strip().upper()
                        expected = str(row_list[2]).strip()
                        self._rules[(codigo, entidad)] = expected
            self._loaded = True
        except Exception:
            logger.exception("IdeContratoSimpleEvaluator._load_from_db failed")
            self._loaded = True

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if the codigo+entidad pair matches the expected IDE.

        Args:
            row_value: The codigo from the invoice row.
            expected: The actual IDE contrato from the invoice row.
            context: EvaluationContext with invoice_data containing codigo_entidad_cobrar.

        Returns:
            True if no rule exists for the pair (skip), or if IDE matches.
            False if a rule exists but IDE does NOT match.
        """
        if row_value is None:
            return True
        if context is None or context.invoice_data is None:
            return False

        codigo = str(row_value).strip().upper()
        if not codigo:
            return True

        entidad = str(context.invoice_data.get("codigo_entidad_cobrar", "")).strip().upper()
        if not entidad:
            return True

        if not self._loaded and context.session is not None:
            self._load_from_db(context.session)

        key = (codigo, entidad)
        if key not in self._rules:
            return True

        expected_ide = self._rules[key]
        actual = str(expected).strip() if expected is not None else ""
        return actual == expected_ide


class PymRutasDxEvaluator(AtomicEvaluator):
    """PYM_RUTAS + Dx + pre-scan laboratorio envio.

    operator = "pym_rutas_dx_check"

    Combines three checks from the legacy detect_ide_contrato_intramural:
    1. PYM_RUTAS + Dx: IDE must be in entity PYM_RUTAS_IDE_MAP
    2. Excludes PYM_INTRAMURAL in NUEVA_EPS_NO_CAPITA
    3. Pre-scan solo_laboratorio_envio bypass
    """

    operator = "pym_rutas_dx_check"

    def __init__(self) -> None:
        self._pre_scan_cache: dict[str, bool] = {}
        self._loaded: bool = False

    def _load_constants(self) -> None:
        if self._loaded:
            return
        from app.constants.base import CODIGOS_LABORATORIO_ENVIO
        from app.constants.intramural import (
            CODIGOS_PYM_RUTAS,
            CODIGOS_PYM_NECESITAN_DX,
            CODIGOS_PYM_INTRAMURAL,
            CODIGOS_NUEVA_EPS_NO_CAPITA,
            TIPO_FACTURA_INTRAMURAL,
        )
        self._LAB_ENVIO: frozenset[str] = CODIGOS_LABORATORIO_ENVIO
        self._PYM_RUTAS: set[str] = set(CODIGOS_PYM_RUTAS.keys())
        self._PYM_NECESITAN_DX: frozenset[str] = CODIGOS_PYM_NECESITAN_DX
        self._PYM_INTRAMURAL: set[str] = set(CODIGOS_PYM_INTRAMURAL.keys())
        self._NUEVA_EPS_NO_CAPITA: frozenset[str] = CODIGOS_NUEVA_EPS_NO_CAPITA
        self._TIPO_INTRAMURAL: str = TIPO_FACTURA_INTRAMURAL

        self._PYM_RUTAS_IDE_MAP: dict[str, set[str]] = {
            "EPSS41": {"955"}, "EPS037": {"961"}, "RES001": {"993"},
            "ESSC62": {"863"}, "ESS062": {"922"}, "RES004": {"908"},
            "EPSI04": {"901"}, "EPSI03": {"965"}, "EPS025": {"902"},
            "RES002": {"952"}, "5177": {"913"}, "86000": {"920"},
            "CCF033": {"937"}, "CCF050": {"914"}, "CCF055": {"868"},
            "CCF102": {"888"}, "CCFC33": {"990"}, "EPS001": {"950"},
            "EPS002": {"936"}, "EPS008": {"870"}, "EPS010": {"925"},
            "EPS017": {"892"}, "EPS018": {"891"}, "EPS040": {"947"},
            "EPS048": {"943"}, "EPSC005": {"932"}, "EPSC34": {"991"},
            "EPSI05": {"977"}, "EPSI06": {"896"}, "EPSIC5": {"979"},
            "EPSS005": {"933"}, "EPSS018": {"927"}, "EPSS02": {"903"},
            "EPSS08": {"945"}, "EPSS10": {"904"}, "EPSS17": {"893"},
            "EPSS34": {"881"}, "EPSS40": {"898"}, "ESS207": {"864"},
            "ESSC24": {"894"}, "ESSC18": {"975"},
        }
        self._loaded = True

    def pre_scan_sheet(
        self,
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        tipo_factura_field: str = "tipo_factura_descripcion",
        tipo_factura_value: str = "Intramural",
    ) -> None:
        """Pre-scan the sheet to find facturas with non-laboratorio codes."""
        num_fact_idx = indices.get("numero_factura")
        codigo_idx = indices.get("codigo")
        tipo_idx = indices.get(tipo_factura_field)

        if num_fact_idx is None or codigo_idx is None:
            return

        self._load_constants()
        has_non_lab: dict[str, bool] = {}

        for row in range(2, data_sheet.max_row + 1):
            if tipo_idx is not None:
                tipo_val = data_sheet.cell(row=row, column=tipo_idx + 1).value
                if str(tipo_val or "").strip().upper() != tipo_factura_value.upper():
                    continue

            factura = str(data_sheet.cell(row=row, column=num_fact_idx + 1).value or "").strip()
            if not factura:
                continue

            codigo = str(data_sheet.cell(row=row, column=codigo_idx + 1).value or "").strip()
            if not codigo:
                continue

            if codigo not in self._LAB_ENVIO:
                has_non_lab[factura] = True

        self._pre_scan_cache = has_non_lab

    def evaluate(
        self,
        condition: dict,
        row_value: Any,
        expected: Any,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Check if code needs a specific IDE per PYM_RUTAS + Dx rules."""
        if row_value is None:
            return True
        if context is None or context.invoice_data is None:
            return False

        self._load_constants()

        codigo = str(row_value).strip().upper()
        if not codigo:
            return True

        inv = context.invoice_data
        entidad = str(inv.get("codigo_entidad_cobrar", "")).strip().upper()
        if not entidad:
            return True

        # Check tipo_factura_descripcion
        tipo = str(inv.get("tipo_factura_descripcion", "")).strip()
        if tipo.upper() != self._TIPO_INTRAMURAL.upper():
            return True

        # Exclusion: PYM_INTRAMURAL in NUEVA_EPS_NO_CAPITA
        if codigo in self._PYM_INTRAMURAL and codigo in self._NUEVA_EPS_NO_CAPITA:
            return True

        # PYM_RUTAS check
        if codigo not in self._PYM_RUTAS:
            return True

        # Check Dx principal
        dx_principal = str(inv.get("codigo_dx_principal", "")).strip().upper()
        if not dx_principal or dx_principal not in self._PYM_NECESITAN_DX:
            return True

        # Excepcion: factura con SOLO laboratorio de envio
        factura = str(inv.get("numero_factura", "")).strip()
        if factura and factura not in self._pre_scan_cache:
            return True

        # Entity must have mapping
        if entidad not in self._PYM_RUTAS_IDE_MAP:
            return True

        ides_validos = self._PYM_RUTAS_IDE_MAP[entidad]
        ide_actual = str(expected).strip() if expected is not None else ""

        return ide_actual in ides_validos


# Re-register with new evaluators
_register_builtins()

