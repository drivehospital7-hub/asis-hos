"""Tests for rule_service.py — CRUD, auto-versioning, and version management.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


class TestRuleServiceQueries:
    """Unit tests for query operations."""

    def test_create_rule_returns_regla_with_id(self):
        """Creating a rule returns a dict with id and estado=draft, version=1."""
        from app.services.reglas.rule_service import create_rule

        mock_db = MagicMock()
        mock_db.add.return_value = None
        mock_db.flush.return_value = None

        data = {
            "nombre": "Test Rule",
            "descripcion": "A test rule",
            "dominio": "odontologia",
            "severidad": "alta",
            "prioridad": 50,
            "parametros": {"tolerancia": 0.1},
        }

        result = create_rule(mock_db, data)

        assert result["estado"] == "draft"
        assert result["version"] == 1
        assert result["nombre"] == "Test Rule"
        assert "id" in result
        mock_db.add.assert_called_once()

    def test_create_rule_stores_condiciones_tree(self):
        """Creating a rule with nested conditions stores them."""
        from app.services.reglas.rule_service import create_rule

        mock_db = MagicMock()
        mock_db.add.return_value = None

        condiciones = {
            "tipo": "AND",
            "condiciones": [
                {"tipo": "atomic", "operador": "eq", "fuente_datos": "campo1", "valor_esperado": "X"},
                {"tipo": "atomic", "operador": "gt", "fuente_datos": "campo2", "valor_esperado": 10},
            ],
        }

        data = {
            "nombre": "Rule with tree",
            "dominio": "urgencias",
            "condiciones": condiciones,
        }

        result = create_rule(mock_db, data)
        assert result["nombre"] == "Rule with tree"
        assert result["version"] == 1

    def test_get_rule_returns_dict_with_nested_conditions(self):
        """get_rule returns full rule with nested condition tree."""
        from app.services.reglas.rule_service import get_rule

        mock_db = MagicMock()

        # Mock a Regla instance
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Test"
        mock_rule.dominio = "odontologia"
        mock_rule.estado = "active"
        mock_rule.version = 3
        mock_rule.severidad = "alta"
        mock_rule.prioridad = 50
        mock_rule.activo = True
        mock_rule.parametros = {"tolerancia": 0.1}
        mock_rule.parametros_default = None
        mock_rule.descripcion = "Test rule"
        mock_rule.creado_en = None
        mock_rule.actualizado_en = None
        mock_rule.to_dict.return_value = {
            "id": 1, "rule_base_id": 1, "nombre": "Test", "dominio": "odontologia",
            "estado": "active", "version": 3, "severidad": "alta", "prioridad": 50,
            "activo": True, "parametros": {"tolerancia": 0.1},
        }

        # Mock child conditions
        mock_child = MagicMock()
        mock_child.id = 10
        mock_child.regla_id = 1
        mock_child.padre_id = None
        mock_child.tipo = "atomic"
        mock_child.operador = "eq"
        mock_child.fuente_datos = "campo"
        mock_child.valor_esperado = "X"
        mock_child.orden = 0
        mock_child.to_dict.return_value = {"id": 10, "tipo": "atomic", "operador": "eq"}

        # Root condition
        mock_root = MagicMock()
        mock_root.id = 5
        mock_root.regla_id = 1
        mock_root.padre_id = None
        mock_root.tipo = "composite"
        mock_root.operador = "AND"
        mock_root.fuente_datos = None
        mock_root.valor_esperado = None
        mock_root.orden = 0
        mock_root.to_dict.return_value = {"id": 5, "tipo": "composite", "operador": "AND"}

        mock_rule.condiciones = [mock_root, mock_child]

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        result = get_rule(mock_db, 1)

        assert result["id"] == 1
        assert result["nombre"] == "Test"
        assert "condiciones" in result
        assert "excepciones" in result

    def test_get_rule_not_found_returns_none(self):
        """get_rule returns None when rule doesn't exist."""
        from app.services.reglas.rule_service import get_rule

        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None

        result = get_rule(mock_db, 999)
        assert result is None

    def test_list_rules_returns_all_rules(self):
        """list_rules returns all rules with no filters."""
        from app.services.reglas.rule_service import list_rules

        mock_db = MagicMock()

        mock_rule = MagicMock()
        mock_rule.to_dict.return_value = {"id": 1, "nombre": "R1", "dominio": "odontologia", "estado": "active"}
        mock_rule2 = MagicMock()
        mock_rule2.to_dict.return_value = {"id": 2, "nombre": "R2", "dominio": "urgencias", "estado": "draft"}

        mock_query = mock_db.query.return_value
        # Chain: query → filter → filter → all
        mock_query.all.return_value = [mock_rule, mock_rule2]

        result = list_rules(mock_db)
        assert len(result) == 2
        assert result[0]["nombre"] == "R1"
        assert result[1]["nombre"] == "R2"

    def test_list_rules_filters_by_dominio(self):
        """list_rules filters by dominio when provided."""
        from app.services.reglas.rule_service import list_rules

        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter_estado = mock_filter.filter.return_value
        mock_filter_estado.all.return_value = []

        result = list_rules(mock_db, dominio="odontologia")
        assert result == []


class TestRuleServiceAutoVersioning:
    """Tests for the auto-versioning update mechanism."""

    def test_update_rule_deprecates_and_creates_new(self):
        """update_rule deprecates old version and creates new active version."""
        import app.services.reglas.rule_service as rs

        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()

        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Test Rule"
        mock_rule.version = 3
        mock_rule.estado = "active"
        mock_rule.dominio = "odontologia"
        mock_rule.severidad = "alta"
        mock_rule.prioridad = 50
        mock_rule.activo = True
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.descripcion = "Original"
        type(mock_rule).condiciones = PropertyMock(return_value=[])

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None  # version query: no existing rows
        mock_filter.first.return_value = mock_rule  # rule query: returns the rule

        # Patch Regla at module level so constructor returns a mock with ID
        mock_new_rule = MagicMock(spec=rs.Regla)
        mock_new_rule.id = 101
        mock_new_rule.version = 4

        with patch.object(rs, 'Regla', return_value=mock_new_rule):
            result = update_rule(mock_db, 1, {"nombre": "Updated Rule"})

        assert result["old_rule_id"] == 1
        assert result["new_rule_id"] == 101
        assert result["old_version"] == 3
        assert result["new_version"] == 4
        assert mock_rule.estado == "deprecated"

    def test_update_rule_raises_on_deprecated_rule(self):
        """update_rule raises ValueError when rule is not active."""
        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()

        mock_rule = MagicMock()
        mock_rule.estado = "deprecated"

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        with pytest.raises(ValueError, match="Cannot modify non-active rule"):
            update_rule(mock_db, 1, {"nombre": "New"})

    def test_update_rule_noop_on_unchanged_data(self):
        """update_rule returns same IDs when no data changed."""
        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()

        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Same"
        mock_rule.dominio = "odontologia"
        mock_rule.severidad = "alta"
        mock_rule.prioridad = 50
        mock_rule.version = 3
        mock_rule.estado = "active"
        mock_rule.descripcion = None
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.activo = True
        type(mock_rule).condiciones = PropertyMock(return_value=[])
        mock_rule.to_dict.return_value = {
            "nombre": "Same", "dominio": "odontologia", "severidad": "alta",
            "prioridad": 50, "descripcion": None, "activo": True,
            "parametros": None,
        }

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        result = update_rule(mock_db, 1, {"nombre": "Same"})
        assert result["old_rule_id"] == 1
        assert result["new_rule_id"] == 1
        assert result["old_version"] == 3
        assert result["new_version"] == 3

    def test_update_rule_rolls_back_on_failure(self):
        """update_rule rolls back when an error occurs after deprecation."""
        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()
        mock_db.flush.side_effect = [None, Exception("DB Error")]

        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Test"
        mock_rule.version = 2
        mock_rule.estado = "active"
        mock_rule.dominio = "odontologia"
        mock_rule.severidad = "alta"
        mock_rule.prioridad = 50
        mock_rule.activo = True
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.descripcion = ""
        type(mock_rule).condiciones = PropertyMock(return_value=[])

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        mock_filter.first.return_value = mock_rule

        with pytest.raises(Exception, match="DB Error"):
            update_rule(mock_db, 1, {"nombre": "New Name"})
        mock_db.rollback.assert_called_once()


class TestRuleServiceVersionManagement:
    """Tests for version list, clone as draft, soft delete."""

    def test_list_versions_ordered_desc(self):
        """list_versions returns versions ordered by version DESC."""
        from app.services.reglas.rule_service import list_versions

        mock_db = MagicMock()

        mock_v1 = MagicMock()
        mock_v1.to_dict.return_value = {"id": 1, "version": 1, "estado": "retired"}
        mock_v2 = MagicMock()
        mock_v2.to_dict.return_value = {"id": 2, "version": 2, "estado": "deprecated"}
        mock_v3 = MagicMock()
        mock_v3.to_dict.return_value = {"id": 3, "version": 3, "estado": "active"}

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = [mock_v3, mock_v2, mock_v1]

        result = list_versions(mock_db, 1)
        assert len(result) == 3
        assert result[0]["version"] == 3
        assert result[2]["version"] == 1

    def test_soft_delete_sets_estado_retired(self):
        """delete_rule sets estado=retired on the rule."""
        from app.services.reglas.rule_service import delete_rule

        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.estado = "active"

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        delete_rule(mock_db, 1)

        assert mock_rule.estado == "retired"
        mock_db.commit.assert_called_once()

    def test_soft_delete_raises_on_already_retired(self):
        """delete_rule raises ValueError when rule already retired."""
        from app.services.reglas.rule_service import delete_rule

        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.estado = "retired"

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        with pytest.raises(ValueError, match="already retired"):
            delete_rule(mock_db, 1)

    def test_create_version_clones_active_as_draft(self):
        """create_version clones active rule as a new draft."""
        from app.services.reglas.rule_service import create_version

        mock_db = MagicMock()

        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Test"
        mock_rule.dominio = "odontologia"
        mock_rule.severidad = "alta"
        mock_rule.prioridad = 50
        mock_rule.version = 3
        mock_rule.estado = "active"
        mock_rule.activo = True
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.descripcion = "Original"
        type(mock_rule).condiciones = PropertyMock(return_value=[])

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        mock_filter.first.return_value = mock_rule

        result = create_version(mock_db, 1)
        assert result["estado"] == "draft"
        assert result["version"] == 4
        # Original remains active
        assert mock_rule.estado == "active"
