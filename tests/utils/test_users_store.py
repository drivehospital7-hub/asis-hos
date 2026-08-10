"""Unit tests for app/utils/users_store.py — SQLAlchemy DB facade.

These tests describe the DB-backed behavior (sdd change
control-errores-role-visibility, Phase 1). Runtime operations use only the
provisioned users table; ``instance/users.json`` is not a fallback.

Tests run against an in-memory SQLite engine so no PostgreSQL server is
required. ``users_store.SessionLocal`` is patched to a sessionmaker bound
to that engine; ``Base.metadata.create_all`` provisions the schema.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import Base
from app.utils import users_store
import app.models  # noqa: F401  (registra los modelos en Base.metadata)


# =============================================================================
# Fixtures — in-memory SQLite backend
# =============================================================================


@pytest.fixture
def db_session():
    """Patches users_store.SessionLocal with an in-memory SQLite sessionmaker.

    Creates the full schema (users, user_areas, ...) explicitly so tests
    control the data themselves.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch.object(users_store, "SessionLocal", Session):
        yield Session


def _add_user(Session, **overrides):
    """Insert a user row directly via SQLAlchemy."""
    base = {
        "username": "user_x",
        "password_hash": generate_password_hash("pass123"),
        "rol": "usuario",
        "permisos": ["odontologia"],
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    }
    base.update(overrides)
    db = Session()
    try:
        db.add(users_store.User(**base))
        db.commit()
    finally:
        db.close()


# =============================================================================
# VALID_ROLES — new roles accepted
# =============================================================================


class TestValidRoles:
    """Spec R7: validador and facturador SHALL be valid assignable roles."""

    @pytest.mark.parametrize("rol", ["admin", "usuario", "facturador", "validador", "medico"])
    def test_valid_roles_includes_role(self, rol):
        """VALID_ROLES MUST accept each supported role."""
        assert rol in users_store.VALID_ROLES

    def test_valid_roles_excludes_unknown(self):
        """Unknown role MUST NOT be valid."""
        assert "superadmin" not in users_store.VALID_ROLES


# =============================================================================
# check_credentials()
# =============================================================================


class TestCheckCredentials:
    """check_credentials validates against the users table."""

    def test_valid_credentials(self, db_session):
        """Valid username+password → dict with username/rol/permisos/person fields."""
        _add_user(
            db_session,
            username="lorenya",
            rol="facturador",
            primer_nombre="LORENY ",
            apellido_1="ESPAÑA ",
        )
        result = users_store.check_credentials("lorenya", "pass123")

        assert result is not None
        assert result["username"] == "lorenya"
        assert result["rol"] == "facturador"
        assert result["primer_nombre"] == "LORENY "
        assert result["apellido_1"] == "ESPAÑA "

    def test_invalid_password(self, db_session):
        """Wrong password → None."""
        _add_user(db_session, username="lorenya", password_hash=generate_password_hash("pass123"))
        assert users_store.check_credentials("lorenya", "wrong") is None

    def test_non_existent_user(self, db_session):
        """Unknown username → None."""
        assert users_store.check_credentials("ghost", "pass123") is None


# =============================================================================
# get_user() / list_users()
# =============================================================================


class TestGetUser:
    """get_user returns the full record (with password_hash)."""

    def test_get_user_returns_row_with_hash(self, db_session):
        """Existing user → dict incl. password_hash and person fields."""
        h = generate_password_hash("pass123")
        _add_user(db_session, username="admin", password_hash=h, rol="admin", permisos=["*"])
        user = users_store.get_user("admin")

        assert user is not None
        assert user["password_hash"] == h
        assert user["rol"] == "admin"
        assert user["permisos"] == ["*"]

    def test_get_user_missing(self, db_session):
        """Unknown user → None."""
        assert users_store.get_user("ghost") is None


class TestListUsers:
    """list_users returns all users WITHOUT password_hash."""

    def test_list_users_excludes_hash(self, db_session):
        """Returned dicts must not expose password_hash."""
        _add_user(db_session, username="admin")
        result = users_store.list_users()

        assert len(result) == 1
        assert result[0]["username"] == "admin"
        assert "password_hash" not in result[0]

    def test_list_users_empty(self, db_session):
        """Empty table → empty list without reading the legacy JSON file."""
        with patch("builtins.open", side_effect=AssertionError("JSON must not be read")):
            assert users_store.list_users() == []


# =============================================================================
# create_user()
# =============================================================================


class TestCreateUser:
    """create_user inserts a new row with hashed password."""

    def test_create_user_success(self, db_session):
        """Valid user → (True, msg), row persisted, hash checkable."""
        ok, msg = users_store.create_user("nuevo", "pass123", "usuario", ["odontologia"])

        assert ok is True
        assert "creado" in msg.lower()
        user = users_store.get_user("nuevo")
        assert user is not None
        assert check_password_hash(user["password_hash"], "pass123")

    def test_create_user_duplicate(self, db_session):
        """Duplicate username → (False, msg), no second row."""
        _add_user(db_session, username="admin")
        ok, msg = users_store.create_user("admin", "pass123", "usuario", ["odontologia"])

        assert ok is False
        assert "ya existe" in msg.lower()
        assert len(users_store.list_users()) == 1

    def test_create_facturador_accepted(self, db_session):
        """rol='facturador' MUST be accepted and persisted."""
        ok, msg = users_store.create_user(
            "angie", "pass123", "facturador",
            ["urgencias", "control_urgencias", "facturas_abiertas"],
            primer_nombre="ANGIE ",
            apellido_1="ARIAS ",
        )
        assert ok is True
        user = users_store.get_user("angie")
        assert user["rol"] == "facturador"
        assert user["primer_nombre"] == "ANGIE "

    def test_create_validador_accepted(self, db_session):
        """rol='validador' MUST be accepted and persisted."""
        ok, msg = users_store.create_user(
            "val", "pass123", "validador",
            ["control_urgencias:write", "facturas_abiertas"],
        )
        assert ok is True
        assert users_store.get_user("val")["rol"] == "validador"

    def test_create_invalid_rol_rejected(self, db_session):
        """Unknown rol → (False, msg), nothing inserted."""
        ok, msg = users_store.create_user("x", "pass123", "superadmin", ["odontologia"])

        assert ok is False
        assert "rol" in msg.lower()
        assert users_store.get_user("x") is None

    def test_create_rejects_mutually_exclusive_permisos(self, db_session):
        """control_urgencias + control_urgencias:write → (False, msg)."""
        ok, msg = users_store.create_user(
            "x", "pass123", "usuario",
            ["control_urgencias", "control_urgencias:write"],
        )
        assert ok is False
        assert "mutuamente excluyentes" in msg.lower()


# =============================================================================
# update_user()
# =============================================================================


class TestUpdateUser:
    """update_user supports partial updates and new roles."""

    def test_update_password_and_fields(self, db_session):
        """password/rol/permisos updated; hash re-generated."""
        _add_user(db_session, username="odonto", rol="usuario")
        ok, msg = users_store.update_user(
            "odonto",
            {"password": "new123", "rol": "facturador", "permisos": ["control_urgencias"]},
        )

        assert ok is True
        user = users_store.get_user("odonto")
        assert user["rol"] == "facturador"
        assert user["permisos"] == ["control_urgencias"]
        assert check_password_hash(user["password_hash"], "new123")

    def test_update_rol_facturador_accepted(self, db_session):
        """rol='facturador' accepted on update."""
        _add_user(db_session, username="odonto", rol="usuario")
        ok, _ = users_store.update_user("odonto", {"rol": "facturador"})
        assert ok is True
        assert users_store.get_user("odonto")["rol"] == "facturador"

    def test_update_rol_validador_accepted(self, db_session):
        """rol='validador' accepted on update."""
        _add_user(db_session, username="odonto", rol="usuario")
        ok, _ = users_store.update_user("odonto", {"rol": "validador"})
        assert ok is True
        assert users_store.get_user("odonto")["rol"] == "validador"

    def test_update_rol_medico_accepted(self, db_session):
        """rol='medico' accepted on update."""
        _add_user(db_session, username="odonto", rol="usuario")
        ok, _ = users_store.update_user("odonto", {"rol": "medico"})
        assert ok is True
        assert users_store.get_user("odonto")["rol"] == "medico"

    def test_update_invalid_rol_rejected(self, db_session):
        """Unknown rol → (False, msg), rol unchanged."""
        _add_user(db_session, username="odonto", rol="usuario")
        ok, msg = users_store.update_user("odonto", {"rol": "superadmin"})

        assert ok is False
        assert "rol" in msg.lower()
        assert users_store.get_user("odonto")["rol"] == "usuario"

    def test_update_skip_password_empty(self, db_session):
        """password='' → hash preserved."""
        h = generate_password_hash("oldpass")
        _add_user(db_session, username="odonto", password_hash=h)
        ok, _ = users_store.update_user("odonto", {"password": "", "rol": "usuario"})

        assert ok is True
        assert users_store.get_user("odonto")["password_hash"] == h

    def test_update_non_existent_user(self, db_session):
        """Unknown user → (False, msg)."""
        ok, msg = users_store.update_user("ghost", {"rol": "usuario"})
        assert ok is False
        assert "no encontrado" in msg.lower()

    def test_update_person_fields_partial(self, db_session):
        """Only provided person fields updated; others preserved."""
        _add_user(db_session, username="odonto", primer_nombre="Carlos", apellido_1="Ruiz")
        ok, _ = users_store.update_user("odonto", {"apellido_1": "López"})

        assert ok is True
        user = users_store.get_user("odonto")
        assert user["primer_nombre"] == "Carlos"
        assert user["apellido_1"] == "López"
        assert user["segundo_nombre"] == ""


# =============================================================================
# delete_user()
# =============================================================================


class TestDeleteUser:
    """delete_user removes a row; admin is protected."""

    def test_delete_existing_user(self, db_session):
        """Normal user → (True, msg), row gone."""
        _add_user(db_session, username="odonto")
        ok, msg = users_store.delete_user("odonto")

        assert ok is True
        assert "eliminado" in msg.lower()
        assert users_store.get_user("odonto") is None

    def test_delete_admin_blocked(self, db_session):
        """delete_user('admin') → (False, msg), row stays."""
        _add_user(db_session, username="admin", rol="admin")
        ok, msg = users_store.delete_user("admin")

        assert ok is False
        assert users_store.get_user("admin") is not None

    def test_delete_non_existent(self, db_session):
        """Unknown user → (False, msg)."""
        ok, msg = users_store.delete_user("ghost")
        assert ok is False
        assert "no encontrado" in msg.lower()


# =============================================================================
# get_facturadores()
# =============================================================================


class TestGetFacturadores:
    """get_facturadores returns all DB users eligible as responsables."""

    def test_filters_by_rol_and_composes_identity(self, db_session):
        """Only facturador rows; identity = primer_nombre + apellido_1 (uppercase)."""
        _add_user(db_session, username="angie", rol="facturador",
                  primer_nombre="ANGIE ", apellido_1="ARIAS ")
        _add_user(db_session, username="lorenya", rol="facturador",
                  primer_nombre="LORENY ", apellido_1="ESPAÑA ")
        _add_user(db_session, username="admin", rol="admin", permisos=["*"])

        result = users_store.get_facturadores()

        assert [f["username"] for f in result] == ["angie", "lorenya"]
        assert result[0]["nombre_completo"] == "ANGIE ARIAS"
        assert result[1]["nombre_completo"] == "LORENY ESPAÑA"
        assert all(f["rol"] == "facturador" for f in result)

    def test_empty_when_no_facturadores(self, db_session):
        """Zero facturador users → empty list (no fallback)."""
        _add_user(db_session, username="admin", rol="admin", permisos=["*"])
        assert users_store.get_facturadores() == []

    def test_excludes_facturador_without_primer_nombre(self, db_session):
        """Facturador without primer_nombre → excluded (no usable identity)."""
        _add_user(db_session, username="anon", rol="facturador")
        assert users_store.get_facturadores() == []

    def test_includes_non_facturador_with_responsable_permission(self, db_session):
        """Explicit permission makes a validator eligible as responsable."""
        _add_user(
            db_session,
            username="validador",
            rol="validador",
            permisos=["control_urgencias", "responsable_facturacion"],
            primer_nombre="MARIA",
            apellido_1="GOMEZ",
        )
        result = users_store.get_facturadores()
        assert [user["username"] for user in result] == ["validador"]
        assert result[0]["rol"] == "validador"

    def test_excludes_validator_without_responsable_permission(self, db_session):
        """Validator role alone does not make a user eligible."""
        _add_user(
            db_session,
            username="validador",
            rol="validador",
            permisos=["control_urgencias"],
            primer_nombre="MARIA",
            apellido_1="GOMEZ",
        )
        assert users_store.get_facturadores() == []


# =============================================================================
# User areas (sdd Empieza: user-areas-management)
# =============================================================================


class TestUserAreas:
    """areas CRUD + validación en users_store (user_areas, sin migración)."""

    def test_create_user_with_areas_persists_rows(self, db_session):
        """create_user(areas=[...]) persiste filas en user_areas y las devuelve ordenadas."""
        ok, msg = users_store.create_user(
            "nuevo", "pass123", "facturador", ["urgencias"],
            primer_nombre="ANGIE", apellido_1="ARIAS",
            areas=["urgencias", "odontologia"],
        )
        assert ok is True
        user = users_store.get_user("nuevo")
        assert user["areas"] == ["odontologia", "urgencias"]  # orden alfabético

        db = db_session()
        try:
            rows = db.query(users_store.UserArea).filter(
                users_store.UserArea.user_id == db.query(users_store.User).filter_by(username="nuevo").one().id
            ).all()
            assert {r.area for r in rows} == {"odontologia", "urgencias"}
        finally:
            db.close()

    def test_create_user_default_areas_empty(self, db_session):
        """Sin areas → lista vacía (no hay filas en user_areas)."""
        ok, _ = users_store.create_user("nuevo", "pass123", "usuario", ["odontologia"])
        assert ok is True
        assert users_store.get_user("nuevo")["areas"] == []

    def test_create_user_invalid_area_rejected_nothing_persisted(self, db_session):
        """Slug inválido → (False, msg); no se crea el usuario ni filas."""
        ok, msg = users_store.create_user(
            "nuevo", "pass123", "usuario", ["odontologia"],
            areas=["no_existe"],
        )
        assert ok is False
        assert "área" in msg.lower() or "area" in msg.lower()
        assert users_store.get_user("nuevo") is None

    def test_update_user_areas_replace_all(self, db_session):
        """update_user({'areas': [...]}) reemplaza TODAS las áreas (no acumula)."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        ok, _ = users_store.update_user("odonto", {"areas": ["extramural", "odontologia"]})
        assert ok is True
        assert users_store.get_user("odonto")["areas"] == ["extramural", "odontologia"]

    def test_update_user_areas_clear(self, db_session):
        """update_user({'areas': []}) limpia las áreas (edición puede vaciar)."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        ok, _ = users_store.update_user("odonto", {"areas": []})
        assert ok is True
        assert users_store.get_user("odonto")["areas"] == []

    def test_update_user_without_areas_preserves(self, db_session):
        """Sin key 'areas' en updates → las áreas no se tocan (partial update)."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        ok, _ = users_store.update_user("odonto", {"rol": "facturador"})
        assert ok is True
        assert users_store.get_user("odonto")["areas"] == ["urgencias"]

    def test_update_user_invalid_area_rejected_unchanged(self, db_session):
        """Slug inválido en update → (False, msg); áreas previas intactas."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        ok, msg = users_store.update_user("odonto", {"areas": ["basura"]})
        assert ok is False
        assert "área" in msg.lower() or "area" in msg.lower()
        assert users_store.get_user("odonto")["areas"] == ["urgencias"]

    def test_create_user_legacy_area_rejected(self, db_session):
        """Slug legacy (equipos_basicos/cruce_facturas/derechos) → rechazado."""
        ok, msg = users_store.create_user(
            "nuevo", "pass123", "usuario", ["odontologia"],
            areas=["equipos_basicos"],
        )
        assert ok is False
        assert "área" in msg.lower() or "area" in msg.lower()
        assert users_store.get_user("nuevo") is None

    def test_update_user_legacy_area_rejected_unchanged(self, db_session):
        """Slug legacy en update → (False, msg); áreas previas intactas."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        ok, msg = users_store.update_user("odonto", {"areas": ["derechos"]})
        assert ok is False
        assert "área" in msg.lower() or "area" in msg.lower()
        assert users_store.get_user("odonto")["areas"] == ["urgencias"]

    def test_update_preserves_legacy_persisted_rows(self, db_session):
        """Filas legacy ya persistidas en user_areas NO se borran al editar."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        db = db_session()
        try:
            user = db.query(users_store.User).filter_by(username="odonto").one()
            db.add(users_store.UserArea(user_id=user.id, area="equipos_basicos"))
            db.add(users_store.UserArea(user_id=user.id, area="cruce_facturas"))
            db.commit()
        finally:
            db.close()

        ok, _ = users_store.update_user(
            "odonto", {"areas": ["extramural", "odontologia"]}
        )
        assert ok is True
        # canónicas reemplazadas + legacy conservada (lista ordenada alfabéticamente)
        assert users_store.get_user("odonto")["areas"] == [
            "cruce_facturas", "equipos_basicos", "extramural", "odontologia",
        ]

    def test_get_facturadores_includes_sorted_areas(self, db_session):
        """get_facturadores expone areas por facturador (para agrupar opciones)."""
        users_store.create_user(
            "angie", "pass123", "facturador", ["urgencias"],
            primer_nombre="ANGIE", apellido_1="ARIAS",
            areas=["odontologia", "urgencias"],
        )
        result = users_store.get_facturadores()
        assert result[0]["areas"] == ["odontologia", "urgencias"]

    def test_list_users_includes_areas(self, db_session):
        """list_users (vía _to_dict) incluye areas ordenadas."""
        users_store.create_user(
            "odonto", "pass123", "usuario", ["odontologia"],
            areas=["urgencias"],
        )
        result = users_store.list_users()
        assert result[0]["areas"] == ["urgencias"]


# =============================================================================
# DB unavailable → error, never JSON fallback
# =============================================================================


class TestDbDown:
    """DB unavailable MUST raise — no JSON/constants fallback (spec R4)."""

    def _make_boom(self):
        def boom():
            raise OperationalError("SELECT", {}, Exception("connection refused"))
        return boom

    def test_check_credentials_raises_on_db_down(self, db_session):
        """check_credentials propagates the DB error instead of returning JSON."""
        with patch.object(users_store, "SessionLocal", self._make_boom()):
            with pytest.raises(OperationalError):
                users_store.check_credentials("admin", "admin123")

    def test_get_facturadores_raises_on_db_down(self, db_session):
        """get_facturadores propagates the DB error (no hardcoded responsables)."""
        with patch.object(users_store, "SessionLocal", self._make_boom()):
            with pytest.raises(OperationalError):
                users_store.get_facturadores()

    def test_list_users_raises_on_db_down(self, db_session):
        """list_users propagates the DB error."""
        with patch.object(users_store, "SessionLocal", self._make_boom()):
            with pytest.raises(OperationalError):
                users_store.list_users()
