"""GroupEvaluator — evaluates condition trees against GROUPS of rows.

Pre-scan → partition → aggregate → evaluate → merge lifecycle.
Keeps the row-by-row ConditionEvaluator path untouched.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.services.engine.context import EvaluationContext

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from app.services.engine.condition_evaluator import ConditionEvaluator
    from app.services.engine.evidence_collector import EvidenceCollector

logger = logging.getLogger(__name__)


class GroupEvaluator:
    """Evaluates conditions against GROUPS of rows instead of individual rows.

    Lifecycle:
        1. build_groups() — pre-scan rows, key by factura.
        2. _build_group_data() — for each group, compute aggregate values.
        3. evaluate() — evaluate condition tree against group-level data.

    Supported aggregation functions:
        - distinct_count(field) → number of distinct values in group
        - group_size → number of rows in group
        - sum(field) → sum of numeric values in group
    """

    @staticmethod
    def build_groups(
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        group_by_field: str = "numero_factura",
    ) -> dict[str, list[int]]:
        """Pre-scan: build groups from sheet data keyed by factura.

        Args:
            data_sheet: openpyxl Worksheet with invoice data.
            indices: Column name → 0-based column index mapping.
            group_by_field: Column to group by (default: numero_factura).

        Returns:
            Dict mapping factura string → list of 1-based row numbers.
            Empty dict if the group-by column is missing.
        """
        groups: dict[str, list[int]] = {}
        num_fact_idx = indices.get(group_by_field)
        if num_fact_idx is None:
            return groups

        for row in range(2, data_sheet.max_row + 1):
            factura = str(
                data_sheet.cell(row=row, column=num_fact_idx + 1).value or ""
            ).strip()
            if not factura:
                continue
            if factura not in groups:
                groups[factura] = []
            groups[factura].append(row)

        return groups

    @staticmethod
    def _build_group_data(
        factura: str,
        rows: list[int],
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        agg_configs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute aggregate data for a group of rows.

        For each config in agg_configs, computes the specified aggregation
        and stores the result under the target field name.

        Args:
            factura: Group key (invoice number).
            rows: List of 1-based row numbers in this group.
            data_sheet: openpyxl Worksheet.
            indices: Column name → index mapping.
            agg_configs: List of dicts with keys:
                - function: "distinct_count" | "group_size" | "sum"
                - field: Source column name (not needed for group_size)
                - target: Output field name (default: {function}_{field})

        Returns:
            Dict with aggregated values plus "numero_factura" key.
        """
        agg_data: dict[str, Any] = {"numero_factura": factura}

        for config in agg_configs:
            func = config.get("function", "")
            field = config.get("field", "")
            target = config.get("target") or (
                f"{func}_{field}" if field else func
            )

            if func == "distinct_count":
                agg_data[target] = GroupEvaluator._agg_distinct_count(
                    rows, data_sheet, indices, field
                )
            elif func == "group_size":
                agg_data[target] = len(rows)
            elif func == "sum":
                agg_data[target] = GroupEvaluator._agg_sum(
                    rows, data_sheet, indices, field
                )
            else:
                logger.warning("Unknown aggregation function: %s", func)

        return agg_data

    @staticmethod
    def _agg_distinct_count(
        rows: list[int],
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        field: str,
    ) -> int:
        """Count distinct non-None values of a field across rows."""
        values: set[str] = set()
        field_idx = indices.get(field)
        if field_idx is None:
            return 0
        for row in rows:
            val = data_sheet.cell(row=row, column=field_idx + 1).value
            if val is not None:
                values.add(str(val).strip())
        return len(values)

    @staticmethod
    def _agg_sum(
        rows: list[int],
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        field: str,
    ) -> float:
        """Sum numeric values of a field across rows."""
        total = 0.0
        field_idx = indices.get(field)
        if field_idx is None:
            return total
        for row in rows:
            val = data_sheet.cell(row=row, column=field_idx + 1).value
            try:
                total += float(val)
            except (ValueError, TypeError):
                pass
        return total

    @staticmethod
    def evaluate(
        groups: dict[str, list[int]],
        data_sheet: "Worksheet",
        indices: dict[str, int | None],
        agg_configs: list[dict[str, Any]],
        condition_tree: dict | None,
        condition_evaluator: "ConditionEvaluator",
        rule_info: dict[str, Any],
        evidence_collector: "EvidenceCollector",
    ) -> list[dict[str, Any]]:
        """Evaluate a group-by rule against all groups.

        For each group:
        1. Compute aggregated data via _build_group_data.
        2. Build an EvaluationContext with the aggregated data.
        3. Evaluate the condition tree via ConditionEvaluator.
        4. Record evidence and collect MATCH results.

        Args:
            groups: Dict mapping factura → list of row numbers.
            data_sheet: openpyxl Worksheet.
            indices: Column name → index mapping.
            agg_configs: Aggregation configurations from rule parametros.
            condition_tree: Root node of the condition tree.
            condition_evaluator: ConditionEvaluator instance.
            rule_info: Dict with id, version, dominio, nombre, descripcion, severidad.
            evidence_collector: EvidenceCollector for audit trail.

        Returns:
            List of detection dicts with factura, problema, regla, severidad.
        """
        results: list[dict[str, Any]] = []

        for factura, rows in groups.items():
            # 1. Compute aggregated data
            group_data = GroupEvaluator._build_group_data(
                factura, rows, data_sheet, indices, agg_configs
            )

            # 2. Build evaluation context with aggregated data
            ctx = EvaluationContext(invoice_data=group_data, indices=indices)

            # 3. Evaluate condition tree
            eval_result = condition_evaluator.evaluate(condition_tree, ctx)
            outcome = eval_result.get("outcome", False)
            error_msg = eval_result.get("error")

            # 4. Determine final outcome
            if error_msg:
                final_outcome = "ERROR"
            elif outcome:
                final_outcome = "MATCH"
            else:
                final_outcome = "NO_MATCH"

            # 5. Record evidence (immutable snapshot)
            evidence_collector.record(
                regla_id=rule_info["id"],
                regla_version=rule_info["version"],
                dominio=rule_info["dominio"],
                factura=factura,
                outcome=final_outcome,
                arbol_evaluado=eval_result.get("trace", {}),
                snapshot_fila=group_data,
                error_mensaje=error_msg,
            )

            # 6. If MATCH, add to detection results
            if outcome and not error_msg:
                problem = {
                    "factura": factura,
                    "problema": rule_info.get("descripcion") or rule_info.get("nombre", ""),
                    "regla": rule_info.get("nombre", ""),
                    "severidad": rule_info.get("severidad", "error"),
                }
                results.append(problem)

        return results
