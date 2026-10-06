"""Unit tests for grupos_service (mocked DB session)."""

from unittest.mock import MagicMock

import pytest

from app.models import GrupoError, Regla
from app.services.reglas.grupos_service import (
    create_grupo,
    delete_grupo,
    list_grupos,
    rename_grupo,
    unassign_grupo,
    validate_rename,
)


def _mock_db(rule_rows=None, grupo_rows=None, counts=None, activas=None):
    """Mock session dispatching query() by model with chainable result."""
    db = MagicMock()
    q_regla = MagicMock()
    q_regla.filter.return_value = q_regla
    q_regla.group_by.return_value = q_regla
    q_regla.all.side_effect = [
        counts if counts is not None else [],
        activas if activas is not None else [],
    ]

    def _query(*models):
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            return q_regla
        q = MagicMock()
        q.all.return_value = grupo_rows if grupo_rows is not None else []
        q.filter_by.return_value.first.return_value = None
        return q

    db.query.side_effect = _query
    return db


def test_list_merges_catalog_and_in_use_with_counts():
    db = _mock_db(
        grupo_rows=[MagicMock(nombre="Decimales", tipo="simple")],
        counts=[("Mi Grupo", 2)],
        activas=[("Mi Grupo", 1)],
    )
    items = list_grupos(db)
    assert len(items) == 2
    mine = next(i for i in items if i["nombre"] == "Mi Grupo")
    assert mine == {
        "nombre": "Mi Grupo",
        "tipo": "simple",
        "total_reglas": 2,
        "reglas_activas": 1,
    }
    dec = next(i for i in items if i["nombre"] == "Decimales")
    assert dec["total_reglas"] == 0 and dec["reglas_activas"] == 0


def test_validate_rename_blocks_sistema_both_ways():
    with pytest.raises(ValueError):
        validate_rename("Duplicados-Farmacia", "Otro")
    with pytest.raises(ValueError):
        validate_rename("Otro", "Duplicados-Farmacia")
    with pytest.raises(ValueError):
        validate_rename("A", "A")
    with pytest.raises(ValueError):
        validate_rename("A", "  ")
    assert validate_rename(" A ", " B ") == ("A", "B")


def test_create_grupo_inserts_simple_row():
    db = _mock_db()
    result = create_grupo(db, "ARL Autorizaciones")
    assert result == {"nombre": "ARL Autorizaciones", "tipo": "simple"}
    added = db.add.call_args[0][0]
    assert isinstance(added, GrupoError) and added.nombre == "ARL Autorizaciones"
    db.commit.assert_called_once()


def test_create_grupo_rejects_blank_and_sistema():
    db = _mock_db()
    with pytest.raises(ValueError):
        create_grupo(db, "   ")
    with pytest.raises(ValueError):
        create_grupo(db, "Duplicados-Farmacia")


def test_rename_updates_rules_and_row():
    db = MagicMock()
    r1, r2 = MagicMock(), MagicMock()
    fila = MagicMock(nombre="Viejo", tipo="simple")
    first_results = iter([fila, None])

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.all.return_value = [r1, r2]
        else:
            q.filter_by.return_value.first.side_effect = lambda *a, **k: next(first_results)
        return q

    db.query.side_effect = _query
    result = rename_grupo(db, "Viejo", "Nuevo", responsible="admin")
    assert result == {"anterior": "Viejo", "nuevo": "Nuevo", "actualizadas": 2}
    assert r1.grupo_error == "Nuevo" and r2.grupo_error == "Nuevo"
    assert r1.cambio_responsable == "admin"
    assert fila.nombre == "Nuevo"
    db.commit.assert_called_once()


def test_rename_unused_raises():
    db = MagicMock()

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.all.return_value = []
        else:
            q.filter_by.return_value.first.return_value = None
        return q

    db.query.side_effect = _query
    with pytest.raises(ValueError):
        rename_grupo(db, "Fantasma", "Nuevo")


def test_rename_unused_row_renames_suggestion_only():
    db = MagicMock()
    fila = MagicMock(nombre="Vieja", tipo="simple")
    seen = {"n": 0}

    def _first(*a, **k):
        seen["n"] += 1
        return fila if seen["n"] == 1 else None

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.all.return_value = []
        else:
            q.filter_by.return_value.first.side_effect = _first
        return q

    db.query.side_effect = _query
    result = rename_grupo(db, "Vieja", "Nueva")
    assert result == {"anterior": "Vieja", "nuevo": "Nueva", "actualizadas": 0}
    assert fila.nombre == "Nueva"


def test_delete_grupo_removes_unused_row_and_guards():
    db = MagicMock()
    fila = MagicMock(nombre="Vieja", tipo="simple")
    scalar_calls = {"n": 0}

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.scalar.return_value = 0
        else:
            q.filter_by.return_value.first.return_value = fila
            q.filter.return_value = q
            q.scalar.return_value = 0
        return q

    db.query.side_effect = _query
    assert delete_grupo(db, "Vieja") == {"grupo": "Vieja", "eliminado": True}
    db.delete.assert_called_once_with(fila)
    with pytest.raises(ValueError):
        delete_grupo(db, "Duplicados-Farmacia")


def test_delete_grupo_refuses_in_use():
    db = MagicMock()
    fila = MagicMock(nombre="Usado", tipo="simple")

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.scalar.return_value = 3
        else:
            q.filter_by.return_value.first.return_value = fila
            q.filter.return_value = q
            q.scalar.return_value = 3
        return q

    db.query.side_effect = _query
    with pytest.raises(ValueError, match="desasign"):
        delete_grupo(db, "Usado")


def test_unassign_sets_null_deletes_simple_row_and_blocks_sistema():
    db = MagicMock()
    r1 = MagicMock()
    fila = MagicMock(nombre="Viejo", tipo="simple")

    def _query(*models):
        q = MagicMock()
        first = models[0] if models else None
        if first is Regla or getattr(first, "class_", None) is Regla:
            q.filter.return_value.all.return_value = [r1]
        else:
            q.filter_by.return_value.first.return_value = fila
        return q

    db.query.side_effect = _query
    result = unassign_grupo(db, "Viejo")
    assert result == {"grupo": "Viejo", "actualizadas": 1}
    assert r1.grupo_error is None
    db.delete.assert_called_once_with(fila)
    with pytest.raises(ValueError):
        unassign_grupo(db, "Duplicados-Farmacia")
