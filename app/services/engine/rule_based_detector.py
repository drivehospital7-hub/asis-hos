"""RuleBasedDetector — legacy-compatible wrapper for the rule engine.

Exposes the same interface as legacy Python detectors:
    detect(data_sheet: Worksheet, indices: dict) → list[dict]

This allows detect_all.py orchestrators to delegate to the DB-backed engine
via feature flag without changing their call patterns.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.services.engine.engine import RuleEvaluationEngine

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from app.services.engine.evidence_collector import EvidenceCollector
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RuleBasedDetector:
    """Wrapper that exposes the same interface as legacy detectors.

    Usage:
        detector = RuleBasedDetector("valores_decimales", session)
        problems = detector.detect(data_sheet, indices)

    The detector supports two data-paths:
    - **Worksheet path** (legacy): Pass ``data_sheet`` and ``indices``.
    - **RowStore path** (fast): Pass ``rows`` (list[dict]) plus ``indices``.
    """

    def __init__(self, rule_name: str, session: "Session") -> None:
        """Initialize detector for a specific rule.

        Args:
            rule_name: DB rule name (e.g., 'valores_decimales', 'ruta_duplicada').
            session: SQLAlchemy session for DB access.
        """
        self._rule_name = rule_name
        self._session = session
        self._engine = RuleEvaluationEngine(session)

    def detect(
        self,
        data_sheet: "Worksheet | None" = None,
        indices: dict[str, int | None] | None = None,
        persist: bool = True,
        rows: list[dict[str, Any]] | None = None,
        evidence_collector: "EvidenceCollector | None" = None,
    ) -> list[dict[str, Any]]:
        """Evaluate the rule against all rows.

        Supports both Worksheet and RowStore data paths. When ``rows`` is
        provided, it takes precedence for data access.

        Args:
            data_sheet: openpyxl Worksheet with invoice data.
            indices: Column name → 0-based column index mapping.
            persist: If True (default), record evidence and audit. If False,
                     skip DB writes — only return detection results.
            rows: Optional list of dicts (RowStore) for O(1) dict access.
            evidence_collector: Optional external EvidenceCollector.

        Returns:
            List of detection dicts. Same format as legacy detectors.
            Empty list if the rule is not found or no problems detected.
        """
        return self._engine.evaluate_sheet(
            rule_name=self._rule_name,
            data_sheet=data_sheet,
            indices=indices,
            persist=persist,
            rows=rows,
            evidence_collector=evidence_collector,
        )
