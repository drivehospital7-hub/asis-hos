"""Tests for catalogos_service.py — CRUD operations with dependency validation.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_row(mapping: dict):
    """Create a mock Row-like object with _mapping support."""
    row = MagicMock()
    row._mapping = mapping
    return row


class TestCatalogosList:
    """Tests for list_catalogos()."""

    def test_list_returns_all_catalogos(self):
        """list_catalogos returns all rows with regla_count."""
        from app.services.reglas.catalogos_service import list_catalogos

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [
            _make_row({
                "key": "prof_odon",
                "descripcion": "Profesionales odontología",
                "dominio": "odontologia",
                "value": ["A", "B"],
                "value_count": 2,
                "regla_count": 2,
                "updated_at": "2024-01-01",
            }),
            _make_row({
                "key": "ips_urgencias",
                "descripcion": "IPS urgencias",
                "dominio": "urgencias",
                "value": ["C"],
                "value_count": 1,
                "regla_count": 1,
                "updated_at": "2024-01-02",
            }),
        ]

        result = list_catalogos(mock_db)

        assert len(result) == 2
        assert result[0]["key"] == "prof_odon"
        assert result[0]["descripcion"] == "Profesionales odontología"
        assert result[0]["dominio"] == "odontologia"
        assert result[0]["value_count"] == 2
        assert result[0]["regla_count"] == 2
        assert result[1]["key"] == "ips_urgencias"
        assert result[1]["regla_count"] == 1

    def test_list_empty_when_no_catalogos(self):
        """list_catalogos returns empty list when no rows exist."""
        from app.services.reglas.catalogos_service import list_catalogos

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []

        result = list_catalogos(mock_db)

        assert result == []


class TestCatalogosGet:
    """Tests for get_catalogo()."""

    def test_get_returns_catalogo(self):
        """get_catalogo returns full catalog dict for existing key."""
        from app.services.reglas.catalogos_service import get_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = _make_row({
            "key": "prof_odon",
            "value": ["A", "B"],
            "descripcion": "Profesionales",
            "dominio": "odontologia",
            "updated_at": "2024-01-01",
        })

        result = get_catalogo(mock_db, "prof_odon")

        assert result is not None
        assert result["key"] == "prof_odon"
        assert result["values"] == ["A", "B"]
        assert result["value_count"] == 2
        assert result["descripcion"] == "Profesionales"

    def test_get_returns_none_when_not_found(self):
        """get_catalogo returns None for non-existent key."""
        from app.services.reglas.catalogos_service import get_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        result = get_catalogo(mock_db, "fake_key")

        assert result is None


class TestCatalogosCreate:
    """Tests for create_catalogo()."""

    def test_create_returns_created_catalogo(self):
        """create_catalogo inserts and returns the new catalog."""
        from app.services.reglas.catalogos_service import create_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = _make_row({
            "key": "nuevos_cups",
            "value": ["CUPS1"],
            "descripcion": "Nuevos CUPS",
            "dominio": "urgencias",
            "updated_at": "2024-01-01",
        })

        result = create_catalogo(mock_db, {
            "key": "nuevos_cups",
            "value": ["CUPS1"],
            "descripcion": "Nuevos CUPS",
            "dominio": "urgencias",
        })

        assert result["key"] == "nuevos_cups"
        assert result["values"] == ["CUPS1"]
        assert result["descripcion"] == "Nuevos CUPS"
        mock_db.commit.assert_called_once()

    def test_create_raises_on_duplicate_key(self):
        """create_catalogo raises ValueError on duplicate key (integrity error)."""
        from app.services.reglas.catalogos_service import create_catalogo
        from sqlalchemy.exc import IntegrityError

        mock_db = MagicMock()
        mock_db.execute.side_effect = IntegrityError("mock", "mock", "mock")
        mock_db.execute.return_value.fetchone.return_value = None

        with pytest.raises(ValueError, match="ya existe"):
            create_catalogo(mock_db, {"key": "prof_odon", "value": []})

    def test_create_raises_on_missing_key(self):
        """create_catalogo raises ValueError when key is missing."""
        from app.services.reglas.catalogos_service import create_catalogo

        mock_db = MagicMock()

        with pytest.raises(ValueError, match="Campo requerido"):
            create_catalogo(mock_db, {"value": ["A"]})

    def test_create_raises_on_non_array_value(self):
        """create_catalogo raises ValueError when value is not a list."""
        from app.services.reglas.catalogos_service import create_catalogo

        mock_db = MagicMock()

        with pytest.raises(ValueError, match="debe ser un array"):
            create_catalogo(mock_db, {"key": "test", "value": "string"})

    def test_create_defaults_empty_value(self):
        """create_catalogo defaults value to empty list when not provided."""
        from app.services.reglas.catalogos_service import create_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = _make_row({
            "key": "test_key",
            "value": [],
            "descripcion": None,
            "dominio": None,
            "updated_at": "2024-01-01",
        })

        result = create_catalogo(mock_db, {"key": "test_key"})

        assert result["key"] == "test_key"
        assert result["values"] == []


class TestCatalogosUpdate:
    """Tests for update_catalogo()."""

    def test_update_value(self):
        """update_catalogo changes value and returns updated row."""
        from app.services.reglas.catalogos_service import update_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = _make_row({
            "key": "prof_odon",
            "value": ["A", "B"],
            "descripcion": "Profesionales",
            "dominio": "odontologia",
            "updated_at": "2024-01-02",
        })

        result = update_catalogo(mock_db, "prof_odon", {"value": ["A", "B"]})

        assert result["key"] == "prof_odon"
        assert result["values"] == ["A", "B"]
        mock_db.commit.assert_called_once()

    def test_update_ignores_key_in_body(self):
        """update_catalogo ignores 'key' in body to enforce immutability."""
        from app.services.reglas.catalogos_service import update_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = _make_row({
            "key": "prof_odon",
            "value": ["A"],
            "descripcion": "Updated",
            "dominio": "odontologia",
            "updated_at": "2024-01-02",
        })

        result = update_catalogo(mock_db, "prof_odon", {
            "key": "otro_key",
            "value": ["A"],
            "descripcion": "Updated",
        })

        # Key should remain prof_odon (from URL), body key is ignored
        assert result["key"] == "prof_odon"
        assert result["descripcion"] == "Updated"

    def test_update_raises_on_non_array_value(self):
        """update_catalogo raises ValueError when value is not a list."""
        from app.services.reglas.catalogos_service import update_catalogo

        mock_db = MagicMock()

        with pytest.raises(ValueError, match="debe ser un array"):
            update_catalogo(mock_db, "prof_odon", {"value": "string"})

    def test_update_raises_on_not_found(self):
        """update_catalogo raises ValueError when key not found."""
        from app.services.reglas.catalogos_service import update_catalogo

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        with pytest.raises(ValueError, match="no encontrado"):
            update_catalogo(mock_db, "fake_key", {"value": ["A"]})


class TestCatalogosDelete:
    """Tests for delete_catalogo()."""

    def _make_mock_db(self, fetchall_result=None, fetchone_result=None, third_result=None):
        """Helper to create a mock db with sequential execute calls.

        First call: key existence check (fetchone)
        Second call: condiciones/reglas check (fetchall)
        Third call (if exists): DELETE (no fetch needed)
        """
        mock_db = MagicMock()

        mock_ret1 = MagicMock()
        mock_ret1.fetchone.return_value = fetchone_result

        mock_ret2 = MagicMock()
        mock_ret2.fetchall.return_value = fetchall_result if fetchall_result is not None else []

        if third_result is not None:
            mock_db.execute.side_effect = [mock_ret1, mock_ret2, third_result]
        else:
            mock_db.execute.side_effect = [mock_ret1, mock_ret2]
        return mock_db

    def test_delete_catalogo_success(self):
        """delete_catalogo removes catalog when no rules reference it."""
        from app.services.reglas.catalogos_service import delete_catalogo

        mock_db = self._make_mock_db(
            fetchone_result=_make_row({"key": "huerfano"}),
            fetchall_result=[],
            third_result=MagicMock(),
        )

        result = delete_catalogo(mock_db, "huerfano")

        assert result == {"deleted": True}

    def test_delete_raises_with_active_rules(self):
        """delete_catalogo raises ValueError when active rules reference the key."""
        from app.services.reglas.catalogos_service import delete_catalogo

        mock_db = self._make_mock_db(
            fetchone_result=_make_row({"key": "prof_odon"}),
            fetchall_result=[
                _make_row({"regla_id": 1, "nombre": "Rule 1", "estado": "active", "version": 1}),
            ],
        )

        with pytest.raises(ValueError, match="No se puede eliminar"):
            delete_catalogo(mock_db, "prof_odon")

    def test_delete_allows_with_draft_only_rules(self):
        """delete_catalogo allows delete when only non-active rules reference it."""
        from app.services.reglas.catalogos_service import delete_catalogo

        mock_db = self._make_mock_db(
            fetchone_result=_make_row({"key": "old_cat"}),
            fetchall_result=[
                _make_row({"regla_id": 1, "nombre": "Rule D", "estado": "draft", "version": 1}),
            ],
            third_result=MagicMock(),
        )

        result = delete_catalogo(mock_db, "old_cat")

        assert result["deleted"] is True
        assert "warnings" in result
        assert "reglas" in result["warnings"]

    def test_delete_raises_on_not_found(self):
        """delete_catalogo raises ValueError when key not found."""
        from app.services.reglas.catalogos_service import delete_catalogo

        mock_db = self._make_mock_db(
            fetchone_result=None,
        )

        with pytest.raises(ValueError, match="no encontrado"):
            delete_catalogo(mock_db, "fake_key")


class TestCatalogosReglas:
    """Tests for get_catalogo_reglas()."""

    def test_get_reglas_returns_linked_rules(self):
        """get_catalogo_reglas returns rules referencing the catalog key."""
        from app.services.reglas.catalogos_service import get_catalogo_reglas

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [
            _make_row({"id": 1, "nombre": "Rule A", "dominio": "odontologia", "estado": "active", "version": 1, "activo": True}),
            _make_row({"id": 2, "nombre": "Rule B", "dominio": "urgencias", "estado": "draft", "version": 1, "activo": False}),
        ]

        result = get_catalogo_reglas(mock_db, "prof_odon")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["nombre"] == "Rule A"
        assert result[1]["nombre"] == "Rule B"

    def test_get_reglas_empty_when_no_references(self):
        """get_catalogo_reglas returns empty list when no rules reference the key."""
        from app.services.reglas.catalogos_service import get_catalogo_reglas

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []

        result = get_catalogo_reglas(mock_db, "unused_key")
        assert result == []
