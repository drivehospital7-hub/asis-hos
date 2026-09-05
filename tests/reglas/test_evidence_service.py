"""Tests for evidence_service.py — wrapping EvidenceRepository with pagination.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestEvidenceService:
    """Tests for evidence query service."""

    def _setup_mock_db(self, return_items=None, total_count=0):
        """Helper: create mock_db with proper chain for query().filter().count()/all()."""
        mock_db = MagicMock()

        # Mock the Evidencia query chain
        mock_query = MagicMock()
        mock_filter_result = MagicMock()
        mock_filter_result.count.return_value = total_count

        # The .all() returns items
        mock_items = return_items if return_items is not None else []
        mock_filter_result.all.return_value = mock_items

        # The order_by → limit → offset chain returns the filter_result
        mock_ordered = MagicMock()
        mock_limited = MagicMock()
        mock_limited.offset.return_value = mock_filter_result
        mock_ordered.limit.return_value = mock_limited
        mock_filter_result.order_by.return_value = mock_ordered

        # Each filter() in the chain returns mock_filter_result
        mock_filtered = MagicMock()
        mock_filtered.count.return_value = total_count
        mock_filtered.order_by.return_value = mock_ordered

        mock_query.filter.return_value = mock_filtered
        mock_query.order_by.return_value = mock_ordered  # Direct call (no filter) uses this

        # Return mock_db where query() returns mock_filter_result or mock_query
        # When count() is called on the query directly (no filter)
        mock_filter_result.count.return_value = total_count
        mock_query.count.return_value = total_count
        mock_db.query.return_value = mock_query

        return mock_db

    def _make_mock_evidencia(self, **kwargs):
        """Create a mock Evidencia with to_dict()."""
        mock_e = MagicMock()
        mock_e.to_dict.return_value = {
            "id": kwargs.get("id", 1),
            "regla_id": kwargs.get("regla_id", 1),
            "factura": kwargs.get("factura", "F001"),
            "dominio": kwargs.get("dominio", "odontologia"),
            "outcome": kwargs.get("outcome", "MATCH"),
            "creado_en": kwargs.get("creado_en", "2026-06-01"),
        }
        return mock_e

    def test_query_evidence_returns_paginated_results(self):
        """query_evidence returns results with total count."""
        from app.services.reglas.evidence_service import query_evidence

        mock_items = [self._make_mock_evidencia(id=1, factura="F001")]
        mock_db = self._setup_mock_db(return_items=mock_items, total_count=50)

        result = query_evidence(mock_db, regla_id=1, limit=10, offset=0)

        assert result["total"] == 50
        assert len(result["items"]) == 1
        assert result["limit"] == 10
        assert result["offset"] == 0
        assert result["items"][0]["factura"] == "F001"

    def test_query_evidence_with_factura_filter(self):
        """query_evidence filters by factura when provided."""
        from app.services.reglas.evidence_service import query_evidence

        mock_db = self._setup_mock_db(total_count=5)

        result = query_evidence(mock_db, factura="F001")

        assert result["total"] == 5

    def test_query_evidence_default_pagination(self):
        """query_evidence uses default limit=100, offset=0."""
        from app.services.reglas.evidence_service import query_evidence

        mock_db = self._setup_mock_db(total_count=0)

        result = query_evidence(mock_db)

        assert result["limit"] == 100
        assert result["offset"] == 0

    def test_query_evidence_empty_results(self):
        """query_evidence returns empty items list when no matches."""
        from app.services.reglas.evidence_service import query_evidence

        mock_db = self._setup_mock_db(return_items=[], total_count=0)

        result = query_evidence(mock_db, regla_id=999)

        assert result["items"] == []
        assert result["total"] == 0
