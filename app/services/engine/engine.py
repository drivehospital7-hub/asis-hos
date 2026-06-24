"""RuleEvaluationEngine — orchestrates the full rule evaluation flow.

Loads rules, evaluates condition trees against sheet rows, collects evidence,
and returns structured detection results.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.models import Regla, Condicion, ResultadoAuditoria
from app.services.engine.context import EvaluationContext
from app.services.engine.condition_evaluator import ConditionEvaluator
from app.services.engine.evidence_collector import EvidenceCollector
from app.services.engine.exception_handler import ExceptionHandler
from app.services.engine.rule_resolver import RuleResolver

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RuleEvaluationEngine:
    """Orchestrates rule loading, condition evaluation, exception handling,
    and evidence collection for a single rule against an Excel sheet.

    Usage:
        engine = RuleEvaluationEngine(session)
        results = engine.evaluate_sheet("valores_decimales", data_sheet, indices)
    """

    def __init__(self, session: "Session") -> None:
        self._session = session
        self._resolver = RuleResolver()
        self._evaluator = ConditionEvaluator()
        self._exception_handler = ExceptionHandler()
        self._evidence_collector = EvidenceCollector()

    def evaluate_sheet(
        self,
        rule_name: str,
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
    ) -> list[dict[str, Any]]:
        """Evaluate a single rule against all rows in an Excel sheet.

        Args:
            rule_name: Rule name to evaluate (e.g., 'valores_decimales').
            data_sheet: openpyxl Worksheet with invoice data.
            indices: Column name → 0-based column index mapping.

        Returns:
            List of detection dicts with keys: factura, problema, regla, severidad,
            and optional rule-specific keys.
        """
        # Load the rule
        rule = self._load_rule_by_name(rule_name)
        if rule is None:
            logger.warning("Rule not found: %s", rule_name)
            return []

        # Load conditions and build tree
        conditions = self._load_conditions(rule.id)
        tree = self._evaluator.build_tree(conditions)
        if tree is None:
            logger.warning("No condition tree for rule: %s", rule_name)
            return []

        # Load param configs
        param_configs = rule.parametros or []
        if not param_configs:
            param_configs = [{}]  # Default: single evaluation with no overrides

        results: list[dict[str, Any]] = []

        # Iterate over rows (row 1 = header, data starts at row 2)
        for row in range(2, data_sheet.max_row + 1):
            row_data, factura = self._build_row_context(data_sheet, row, indices)
            if not factura:
                continue

            ctx = EvaluationContext(invoice_data=row_data, indices=indices)

            # Check exceptions
            effect, overrides = self._exception_handler.apply_exceptions(
                rule, ctx, self._session
            )
            if effect == "skip":
                logger.debug("Rule %s skipped for factura %s", rule_name, factura)
                continue

            # Evaluate with each param config
            for config_idx, params in enumerate(param_configs):
                if overrides:
                    params = {**params, **overrides}  # Merge overrides

                eval_ctx = EvaluationContext(
                    invoice_data={**row_data, **(params if isinstance(params, dict) else {})},
                    indices=indices,
                )

                eval_result = self._evaluator.evaluate(tree, eval_ctx)
                outcome = eval_result.get("outcome", False)
                error_msg = eval_result.get("error")

                # Determine result status
                if error_msg:
                    final_outcome = "ERROR"
                elif outcome:
                    final_outcome = "MATCH"
                else:
                    final_outcome = "NO_MATCH"

                # Record evidence (immutable snapshot)
                self._evidence_collector.record(
                    regla_id=rule.id,
                    regla_version=rule.version,
                    dominio=rule.dominio,
                    factura=factura,
                    param_config_id=config_idx if param_configs else None,
                    outcome=final_outcome,
                    arbol_evaluado=eval_result.get("trace", {}),
                    snapshot_fila=row_data,
                    error_mensaje=error_msg,
                )

                # If MATCH, add to detection results
                if outcome and not error_msg:
                    problem = {
                        "factura": factura,
                        "problema": rule.descripcion or rule.nombre,
                        "regla": rule.nombre,
                        "severidad": rule.severidad,
                        "param_config_id": config_idx,
                    }
                    results.append(problem)

        # Flush all evidence and capture records with IDs
        evidencias = self._evidence_collector.flush_batch(self._session)

        # Create ResultadoAuditoria for each evidence record
        for ev in evidencias:
            if ev.outcome == "MATCH":
                resultado_str = "FAIL"
            elif ev.outcome == "ERROR":
                resultado_str = "ERROR"
            else:
                resultado_str = "PASS"

            ra = ResultadoAuditoria(
                evidencia_id=ev.id,
                regla_id=ev.regla_id,
                regla_version=ev.regla_version,
                factura=ev.factura,
                param_config_id=ev.param_config_id,
                resultado=resultado_str,
                severidad=rule.severidad,
                mensaje=ev.error_mensaje or rule.descripcion,
                detalles={"outcome": ev.outcome},
            )
            self._session.add(ra)

        self._session.flush()

        return results

    # ── Internal helpers ──────────────────────────────────────────────────

    def _load_rule_by_name(self, rule_name: str) -> Regla | None:
        """Load a single rule by name."""
        return (
            self._session.query(Regla)
            .filter(Regla.nombre == rule_name)
            .filter(Regla.activo == True)  # noqa: E712
            .first()
        )

    def _load_conditions(self, regla_id: int) -> list[dict]:
        """Load all conditions for a rule and convert to dicts."""
        rows = (
            self._session.query(Condicion)
            .filter(Condicion.regla_id == regla_id)
            .order_by(Condicion.padre_id.asc().nullsfirst(), Condicion.orden.asc())
            .all()
        )
        return [
            {
                "id": c.id,
                "regla_id": c.regla_id,
                "padre_id": c.padre_id,
                "tipo": c.tipo,
                "operador": c.operador,
                "fuente_datos": c.fuente_datos,
                "valor_esperado": c.valor_esperado,
                "orden": c.orden,
            }
            for c in rows
        ]

    def _build_row_context(
        self,
        data_sheet: "Worksheet",
        row: int,
        indices: dict[str, int | None],
    ) -> tuple[dict[str, Any], str | None]:
        """Extract row data from Excel worksheet using column indices.

        Returns:
            (row_data_dict, factura_string) where factura_string may be None.
        """
        row_data: dict[str, Any] = {}
        factura = None

        for col_name, col_idx in indices.items():
            if col_idx is None:
                continue
            value = data_sheet.cell(row=row, column=col_idx + 1).value
            row_data[col_name] = value
            if col_name in ("numero_factura", "factura") and value is not None:
                factura = str(value).strip()

        return row_data, factura
