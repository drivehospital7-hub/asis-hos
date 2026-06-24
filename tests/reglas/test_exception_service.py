"""Tests for exception_service.py — Excepcion CRUD.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock


class TestExceptionService:
    """Tests for exception CRUD operations."""

    def test_list_exceptions_returns_all_for_rule(self):
        """list_exceptions returns all exceptions for a rule."""
        from app.services.reglas.exception_service import list_exceptions

        mock_db = MagicMock()
        mock_exc1 = MagicMock()
        mock_exc1.to_dict.return_value = {"id": 1, "tipo_efecto": "skip", "activo": True}
        mock_exc2 = MagicMock()
        mock_exc2.to_dict.return_value = {"id": 2, "tipo_efecto": "downgrade", "activo": True}

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = [mock_exc1, mock_exc2]

        result = list_exceptions(mock_db, 1)

        assert len(result) == 2
        assert result[0]["tipo_efecto"] == "skip"

    def test_list_exceptions_empty(self):
        """list_exceptions returns empty list when no exceptions."""
        from app.services.reglas.exception_service import list_exceptions

        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.all.return_value = []

        result = list_exceptions(mock_db, 999)
        assert result == []

    def test_create_exception_returns_exception(self):
        """create_exception creates and returns a new exception."""
        from app.services.reglas.exception_service import create_exception

        mock_db = MagicMock()

        data = {
            "tipo_efecto": "skip",
            "condicion_json": {"campo": "valor"},
            "activo": True,
        }

        result = create_exception(mock_db, 1, data)

        assert result["tipo_efecto"] == "skip"
        assert result["regla_id"] == 1
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_exception_missing_tipo_efecto_raises(self):
        """create_exception raises ValueError when tipo_efecto missing."""
        from app.services.reglas.exception_service import create_exception

        mock_db = MagicMock()
        data = {"condicion_json": {}}

        import pytest
        with pytest.raises(ValueError, match="tipo_efecto"):
            create_exception(mock_db, 1, data)
