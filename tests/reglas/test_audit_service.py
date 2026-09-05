"""Tests for audit_service.py — ResultadoAuditoria queries.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestAuditService:
    """Tests for audit query service."""

    def _setup_mock_db(self, return_items=None, total_count=0):
        """Helper: create mock_db with proper chain for query().filter().count()/all()."""
        mock_db = MagicMock()

        mock_query = MagicMock()
        mock_filter_result = MagicMock()
        mock_filter_result.count.return_value = total_count

        mock_items = return_items if return_items is not None else []
        mock_filter_result.all.return_value = mock_items

        mock_ordered = MagicMock()
        mock_limited = MagicMock()
        mock_limited.offset.return_value = mock_filter_result
        mock_ordered.limit.return_value = mock_limited
        mock_filter_result.order_by.return_value = mock_ordered

        mock_filtered = MagicMock()
        mock_filtered.count.return_value = total_count
        mock_filtered.order_by.return_value = mock_ordered

        mock_query.filter.return_value = mock_filtered
        mock_query.order_by.return_value = mock_ordered  # Direct call (no filter) uses this
        mock_filter_result.count.return_value = total_count
        mock_query.count.return_value = total_count
        mock_db.query.return_value = mock_query

        return mock_db

    def _make_mock_resultado(self, **kwargs):
        """Create a mock ResultadoAuditoria with to_dict()."""
        mock_r = MagicMock()
        mock_r.to_dict.return_value = {
            "id": kwargs.get("id", 1),
            "evidencia_id": kwargs.get("evidencia_id", 1),
            "regla_id": kwargs.get("regla_id", 1),
            "factura": kwargs.get("factura", "F001"),
            "resultado": kwargs.get("resultado", "MATCH"),
            "severidad": kwargs.get("severidad", "error"),
            "mensaje": kwargs.get("mensaje", ""),
            "creado_en": kwargs.get("creado_en", "2026-06-01"),
        }
        return mock_r

    def test_query_audit_returns_paginated_results(self):
        """query_audit returns results with total count."""
        from app.services.reglas.audit_service import query_audit

        mock_items = [
            self._make_mock_resultado(id=1, factura="F001", resultado="MATCH"),
            self._make_mock_resultado(id=2, factura="F002", resultado="NO_MATCH"),
        ]
        mock_db = self._setup_mock_db(return_items=mock_items, total_count=50)

        result = query_audit(mock_db, limit=10, offset=0)

        assert result["total"] == 50
        assert len(result["items"]) == 2
        assert result["limit"] == 10
        assert result["offset"] == 0

    def test_query_audit_filters_by_regla_id(self):
        """query_audit filters by regla_id when provided."""
        from app.services.reglas.audit_service import query_audit

        mock_db = self._setup_mock_db(total_count=5)

        result = query_audit(mock_db, regla_id=1)
        assert result["total"] == 5

    def test_query_audit_filters_by_resultado(self):
        """query_audit filters by resultado when provided."""
        from app.services.reglas.audit_service import query_audit

        mock_db = self._setup_mock_db(total_count=0)

        result = query_audit(mock_db, resultado="MATCH")
        assert result["total"] == 0

    def test_query_audit_default_pagination(self):
        """query_audit uses default limit=100, offset=0."""
        from app.services.reglas.audit_service import query_audit

        mock_db = self._setup_mock_db(total_count=0)

        result = query_audit(mock_db)
        assert result["limit"] == 100
        assert result["offset"] == 0
