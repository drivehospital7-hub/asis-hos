"""Tests for rule_service.py — CRUD, auto-versioning, and version management.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


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

    def test_create_rule_stores_reverse_tree(self):
        """Creating a rule accepts a reverse-shaped nested tree."""
        import app.services.reglas.rule_service as rs
        from app.services.reglas.rule_service import create_rule

        mock_db = MagicMock()
        reverse_tree = [{
            "tipo": "composite",
            "operador": "NOT",
            "condiciones": [{
                "tipo": "atomic",
                "operador": "eq",
                "fuente_datos": "invoice.centro_costo",
                "valor_esperado": "TRASLADOS",
            }],
        }]

        with patch.object(rs, "_store_condition_tree") as store_tree:
            result = create_rule(mock_db, {
                "nombre": "Reverse rule",
                "dominio": "urgencias",
                "condiciones": reverse_tree,
            })

        assert result["nombre"] == "Reverse rule"
        store_tree.assert_called_once_with(mock_db, result["id"], None, reverse_tree[0])

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

        with patch.object(rs, 'Regla', return_value=mock_new_rule) as regla_cls:
            result = update_rule(mock_db, 1, {
                "nombre": "Updated Rule",
                "cambio_que": "Updated the rule name",
                "cambio_por_que": "Reflect the current business definition",
            }, responsible="admin")

        assert result["old_rule_id"] == 1
        assert result["new_rule_id"] == 101
        assert result["old_version"] == 3
        assert result["new_version"] == 4
        assert mock_rule.estado == "deprecated"
        kwargs = regla_cls.call_args.kwargs
        assert kwargs["cambio_que"] == "Updated the rule name"
        assert kwargs["cambio_por_que"] == "Reflect the current business definition"
        assert kwargs["cambio_responsable"] == "admin"

    def test_update_rule_persists_submitted_reverse_tree(self):
        """Updating conditions stores the submitted NOT subtree, not the old tree."""
        import app.services.reglas.rule_service as rs
        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.rule_base_id = 1
        mock_rule.nombre = "Reverse rule"
        mock_rule.version = 1
        mock_rule.estado = "active"
        mock_rule.dominio = "urgencias"
        mock_rule.severidad = "error"
        mock_rule.prioridad = 50
        mock_rule.activo = True
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.descripcion = None
        type(mock_rule).condiciones = PropertyMock(return_value=[])

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        mock_filter.first.return_value = mock_rule

        mock_new_rule = MagicMock(spec=rs.Regla)
        mock_new_rule.id = 2
        mock_new_rule.version = 2
        reverse_tree = [{
            "tipo": "composite",
            "operador": "NOT",
            "orden": 0,
            "condiciones": [{
                "tipo": "atomic",
                "operador": "eq",
                "fuente_datos": "invoice.centro_costo",
                "valor_esperado": "TRASLADOS",
                "orden": 0,
            }],
        }]

        with patch.object(rs, "Regla", return_value=mock_new_rule), \
             patch.object(rs, "_store_condition_tree") as store_tree, \
             patch.object(rs, "_clone_conditions") as clone_conditions:
            result = update_rule(mock_db, 1, {
                "condiciones": reverse_tree,
                "cambio_que": "Changed the condition tree",
                "cambio_por_que": "Use the revised validation logic",
            }, responsible="admin")

        assert result["new_rule_id"] == 2
        store_tree.assert_called_once_with(mock_db, 2, None, reverse_tree[0])
        clone_conditions.assert_not_called()

    def test_update_rule_rejects_invalid_reverse_tree(self):
        """A NOT node must have exactly one child before versioning."""
        from app.services.reglas.rule_service import update_rule

        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.estado = "active"
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_rule

        with pytest.raises(ValueError, match="exactly one child"):
            update_rule(mock_db, 1, {"condiciones": [{"operador": "NOT", "condiciones": []}]})

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

    def test_update_rule_requires_audit_metadata_for_real_changes(self):
        """A changed rule cannot create a version without what/why metadata."""
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

        mock_filter = mock_db.query.return_value.filter.return_value
        mock_filter.first.return_value = mock_rule

        with pytest.raises(ValueError, match="cambio_que y cambio_por_que"):
            update_rule(mock_db, 1, {"nombre": "Changed"}, responsible="admin")

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
            update_rule(mock_db, 1, {
                "nombre": "New Name",
                "cambio_que": "Renamed the rule",
                "cambio_por_que": "Align the rule name",
            }, responsible="admin")
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

    def test_create_version_repairs_legacy_null_base_before_cloning(self):
        """A legacy row without a base starts its lineage at its own id."""
        from app.services.reglas.rule_service import create_version

        mock_db = MagicMock()
        mock_rule = MagicMock()
        mock_rule.id = 29
        mock_rule.rule_base_id = None
        mock_rule.nombre = "Legacy"
        mock_rule.dominio = "urgencias"
        mock_rule.severidad = "error"
        mock_rule.prioridad = 25
        mock_rule.version = 1
        mock_rule.activo = True
        mock_rule.parametros = None
        mock_rule.parametros_default = None
        mock_rule.descripcion = None
        type(mock_rule).condiciones = PropertyMock(return_value=[])

        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.first.return_value = None
        mock_filter.first.return_value = mock_rule

        create_version(mock_db, 29)

        assert mock_rule.rule_base_id == 29
        new_rule = mock_db.add.call_args.args[0]
        assert new_rule.rule_base_id == 29

    def test_lineage_migration_requires_proven_identity_sequence(self):
        """The backfill must group only same-name/domain contiguous versions."""
        migration = Path("migrations/006_backfill_rule_version_lineage.sql").read_text()

        assert "GROUP BY nombre, dominio" in migration
        assert "first_version = 1" in migration
        assert "last_version = row_count" in migration
        assert "distinct_versions = row_count" in migration
        assert "SET rule_base_id = id" in migration
        assert "WHERE rule_base_id IS NULL" in migration


def _make_publish_draft(**overrides):
    """Build a Regla-like mock for publish_rule tests.

    Both queries in publish_rule end in .first(), so the caller wires
    mock_db.query.side_effect = [_query_first(draft), _query_first(incumbent)].
    """
    draft = MagicMock()
    draft.id = 10
    draft.rule_base_id = 10
    draft.nombre = "Test Rule"
    draft.descripcion = "A test rule"
    draft.dominio = "odontologia"
    draft.severidad = "alta"
    draft.prioridad = 50
    draft.activo = True
    draft.parametros = None
    draft.parametros_default = None
    draft.version = 1
    draft.estado = "draft"

    cond = MagicMock()
    cond.id = 1
    cond.padre_id = None
    cond.to_dict.return_value = {"id": 1, "tipo": "atomic", "operador": "eq"}
    type(draft).condiciones = PropertyMock(return_value=[cond])

    # to_dict reflects live attributes so post-mutation assertions are real.
    draft.to_dict.side_effect = lambda: {
        "id": draft.id,
        "rule_base_id": draft.rule_base_id,
        "nombre": draft.nombre,
        "descripcion": draft.descripcion,
        "dominio": draft.dominio,
        "severidad": draft.severidad,
        "prioridad": draft.prioridad,
        "activo": draft.activo,
        "parametros": draft.parametros,
        "estado": draft.estado,
        "version": draft.version,
    }

    for key, value in overrides.items():
        if key == "condiciones":
            type(draft).condiciones = PropertyMock(return_value=value)
        else:
            setattr(draft, key, value)
    return draft


def _query_first(return_value):
    """A query mock whose filter(...).first() returns the given value."""
    query = MagicMock()
    query.filter.return_value.first.return_value = return_value
    return query


class TestRuleServicePublish:
    """Unit tests for publish_rule (draft → active promotion).

    Both queries in publish_rule end in .first() (draft lookup, then
    incumbent lookup), so we drive mock_db.query via side_effect — NOT the
    first/order_by pattern used by update_rule.
    """

    def test_publish_draft_v1_without_incumbent_promotes_in_place(self):
        """First publish: same row becomes active, deprecated_id=None, responsible set."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        mock_db.query.side_effect = [_query_first(draft), _query_first(None)]

        result = publish_rule(mock_db, draft.id, responsible="admin")

        assert result["estado"] == "active"
        assert result["deprecated_id"] is None
        assert result["id"] == draft.id
        assert result["version"] == 1
        # Same row: the very same object was promoted, not a new version.
        assert draft.estado == "active"
        assert draft.version == 1
        assert draft.cambio_responsable == "admin"
        mock_db.commit.assert_called_once()

    def test_publish_draft_deprecates_active_incumbent(self):
        """Cloned draft: incumbent active is deprecated and returned as deprecated_id."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        incumbent = MagicMock()
        incumbent.id = 77
        incumbent.estado = "active"
        mock_db.query.side_effect = [_query_first(draft), _query_first(incumbent)]

        result = publish_rule(mock_db, draft.id, responsible="admin")

        assert incumbent.estado == "deprecated"
        assert result["deprecated_id"] == 77
        assert draft.estado == "active"
        mock_db.commit.assert_called_once()

    def test_publish_draft_ignores_deprecated_incumbent(self):
        """A deprecated incumbent is not matched by the active-only query."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        # The incumbent query filters estado=="active", so a deprecated row
        # must NOT be returned by the query mock.
        mock_db.query.side_effect = [_query_first(draft), _query_first(None)]

        result = publish_rule(mock_db, draft.id, responsible="admin")

        assert result["deprecated_id"] is None
        assert draft.estado == "active"
        mock_db.commit.assert_called_once()

    def test_publish_draft_ignores_retired_incumbent(self):
        """A retired incumbent is not matched by the active-only query either."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        mock_db.query.side_effect = [_query_first(draft), _query_first(None)]

        result = publish_rule(mock_db, draft.id, responsible="admin")

        assert result["deprecated_id"] is None
        assert draft.estado == "active"
        mock_db.commit.assert_called_once()

    def test_publish_not_found_raises_value_error(self):
        """Publishing a missing rule raises ValueError without committing."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        mock_db.query.side_effect = [_query_first(None)]

        with pytest.raises(ValueError, match="Rule 999 not found"):
            publish_rule(mock_db, 999, responsible="admin")
        mock_db.commit.assert_not_called()

    def test_publish_rejects_non_draft_rule(self):
        """An active rule cannot be published (non-draft rejection, S-05/S-08)."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft(estado="active")
        mock_db.query.side_effect = [_query_first(draft)]

        with pytest.raises(
            ValueError,
            match=r"Solo se pueden publicar reglas en estado draft \(current: active\)",
        ):
            publish_rule(mock_db, draft.id, responsible="admin")
        mock_db.commit.assert_not_called()

    def test_publish_rejects_empty_condition_tree(self):
        """A draft without conditions cannot be published (S-06)."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft(condiciones=[])
        mock_db.query.side_effect = [_query_first(draft)]

        with pytest.raises(ValueError, match="No se puede publicar una regla sin condiciones"):
            publish_rule(mock_db, draft.id, responsible="admin")
        assert draft.estado == "draft"
        mock_db.commit.assert_not_called()

    def test_publish_requires_responsible(self):
        """responsible=None is rejected before any mutation."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        mock_db.query.side_effect = [_query_first(draft)]

        with pytest.raises(ValueError, match="No se pudo determinar el usuario autenticado"):
            publish_rule(mock_db, draft.id, responsible=None)
        mock_db.commit.assert_not_called()

    def test_publish_requires_non_blank_responsible(self):
        """responsible='   ' (whitespace only) is rejected too."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        mock_db.query.side_effect = [_query_first(draft)]

        with pytest.raises(ValueError, match="No se pudo determinar el usuario autenticado"):
            publish_rule(mock_db, draft.id, responsible="   ")
        mock_db.commit.assert_not_called()

    def test_publish_rolls_back_on_commit_failure(self):
        """A mid-transaction failure rolls back both incumbent and draft (S-08)."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("DB Error")
        draft = _make_publish_draft()
        mock_db.query.side_effect = [_query_first(draft), _query_first(None)]

        with pytest.raises(Exception, match="DB Error"):
            publish_rule(mock_db, draft.id, responsible="admin")
        mock_db.rollback.assert_called_once()

    def test_publish_twice_rejects_second_call(self):
        """Idempotency: the second publish of the same rule is a non-draft rejection."""
        from app.services.reglas.rule_service import publish_rule

        mock_db = MagicMock()
        draft = _make_publish_draft()
        # 1st publish: draft found, no incumbent; 2nd publish: same object now active.
        mock_db.query.side_effect = [
            _query_first(draft), _query_first(None),
            _query_first(draft), _query_first(None),
        ]

        first = publish_rule(mock_db, draft.id, responsible="admin")
        assert first["estado"] == "active"

        with pytest.raises(ValueError, match="Solo se pueden publicar reglas en estado draft"):
            publish_rule(mock_db, draft.id, responsible="admin")
        mock_db.commit.assert_called_once()
