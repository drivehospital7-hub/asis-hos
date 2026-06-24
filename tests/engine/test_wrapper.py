"""Unit tests for RuleBasedDetector — legacy-compatible wrapper."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestRuleBasedDetector:
    """Tests for RuleBasedDetector.detect() matching legacy interface."""

    def test_import_exists(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector
        assert RuleBasedDetector is not None

    def test_detect_returns_list(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector
        from openpyxl import Workbook
        from unittest.mock import MagicMock

        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # Rule not found → empty result
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        session.query.return_value = mock_query

        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=1, value="FACTURA")

        detector = RuleBasedDetector("test_rule", session)
        result = detector.detect(ws, {"numero_factura": 0})
        assert isinstance(result, list)

    def test_detect_has_same_signature_as_legacy(self):
        """RuleBasedDetector.detect(data_sheet, indices) matches legacy signature."""
        import inspect
        from app.services.engine.rule_based_detector import RuleBasedDetector

        sig = inspect.signature(RuleBasedDetector.detect)
        params = list(sig.parameters.keys())
        # detect(self, data_sheet, indices)
        assert "data_sheet" in params
        assert "indices" in params

    def test_init_stores_rule_name_and_session(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector
        session = MagicMock()
        detector = RuleBasedDetector("valores_decimales", session)
        assert detector._rule_name == "valores_decimales"
        assert detector._session is session
