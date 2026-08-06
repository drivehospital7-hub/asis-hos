"""Integration tests for auth routes (login, logout, CRUD, permissions).

Adapted to the SQLAlchemy DB facade (sdd: control-errores-role-visibility):
the store no longer reads ``instance/users.json``, so tests patch
``users_store.SessionLocal`` with an in-memory SQLite engine instead of
``USERS_FILE``. Behavior under test is unchanged.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

from app.database import Base
from app.models import User
from app.utils import users_store
import app.models  # noqa: F401  (registra los modelos en Base.metadata)

DEFAULT_TEST_USERS = [
    {
        "username": "admin",
        "password_hash": generate_password_hash("admin123"),
        "rol": "admin",
        "permisos": ["*"],
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "odontologia",
        "password_hash": generate_password_hash("odonto123"),
        "rol": "usuario",
        "permisos": ["odontologia"],
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "test_user",
        "password_hash": generate_password_hash("test123"),
        "rol": "usuario",
        "permisos": ["odontologia"],
        "primer_nombre": "Test",
        "segundo_nombre": "",
        "apellido_1": "User",
        "apellido_2": "",
    },
]


@contextmanager
def _patched_store(users: list | None = None):
    """Patches the users store to an in-memory SQLite DB seeded with users.

    Reemplaza el antiguo ``patch.object(users_store, "USERS_FILE", ...)``:
    la DB es la única fuente de verdad, así que el seed se hace en la tabla
    ``users`` (SQLite en memoria) y se desactiva el bootstrap JSON lazy.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    seed_db = Session()
    try:
        for u in users or DEFAULT_TEST_USERS:
            seed_db.add(User(**u))
        seed_db.commit()
    finally:
        seed_db.close()

    with (
        patch.object(users_store, "SessionLocal", Session),
        patch.object(users_store, "_SEEDED", True),
    ):
        yield Session


def _seed_users(tmp_path=None):
    """Devuelve la lista de usuarios de test (la DB se siembra en _patched_store).

    Se mantiene el parámetro ``tmp_path`` por compatibilidad con los tests
    que lo pasaban; ya no se escribe ningún archivo JSON.
    """
    return DEFAULT_TEST_USERS


# =============================================================================
# Tests: Login
# =============================================================================


class TestLogin:
    """Existing login behavior — no regression."""

    def test_login_success(self, app_client):
        """Valid credentials → redirect to React dashboard."""
        with _patched_store(_seed_users()):
            resp = app_client.post(
                "/auth/login",
                data={"username": "admin", "password": "admin123"},
                follow_redirects=True,
            )
        assert resp.status_code == 200
        # Redirects to React dashboard (no flash in React)
        assert b"__INITIAL_DATA__" in resp.data

    def test_login_wrong_password(self, app_client):
        """Invalid password → redirect to login (React, no flash)."""
        with _patched_store(_seed_users()):
            resp = app_client.post(
                "/auth/login",
                data={"username": "admin", "password": "wrong"},
                follow_redirects=True,
            )
        assert resp.status_code == 200
        # React login page — no flash messages anymore
        assert b"__INITIAL_DATA__" in resp.data or b"id=\\x22root\\x22" in resp.data

    def test_login_already_authenticated(self, app_client):
        """Redirects a logged-in user to the React dashboard."""
        with _patched_store(_seed_users()):
            app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
            resp = app_client.get("/auth/login", follow_redirects=True)
        assert resp.status_code == 200
        assert b"__INITIAL_DATA__" in resp.data


# =============================================================================
# Tests: Listar usuarios
# =============================================================================


class TestListarUsuarios:
    """GET /auth/usuarios — requires admin."""

    def test_list_as_admin(self, app_client, tmp_path):
        """Admin user can list users."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.get("/auth/usuarios")
            assert resp.status_code == 200
            assert b"admin" in resp.data
            assert b"test_user" in resp.data

    def test_list_as_non_admin(self, app_client):
        """Non-admin → 403 or redirect."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        resp = app_client.get("/auth/usuarios", follow_redirects=True)
        # Should be redirected — no flash in React
        assert resp.status_code == 200

    def test_list_unauthenticated(self, app_client):
        """No session → 401."""
        resp = app_client.get("/auth/usuarios")
        assert resp.status_code == 401

    def test_list_includes_templates_in_initial_data(self, app_client, tmp_path):
        """Admin user: templates are included in initial_data."""
        import json
        from app.utils import templates_store

        templates_file = tmp_path / "templates.json"
        templates = [
            {"nombre": "odontologia", "descripcion": "...", "permisos": ["odontologia"]},
        ]
        templates_file.write_text(json.dumps(templates, indent=2), encoding="utf-8")
        with patch.object(templates_store, "TEMPLATES_FILE", templates_file):
            with _patched_store(_seed_users()):
                with app_client.session_transaction() as sess:
                    sess["ce_authenticated"] = True
                    sess["permisos"] = ["*"]
                    sess["username"] = "admin"

                resp = app_client.get("/auth/usuarios")
                assert resp.status_code == 200

        # HTML response — verify templates section in initial_data
        html = resp.data.decode("utf-8")
        assert '"templates"' in html, "templates key missing from initial_data"
        assert '"nombre":"odontologia"' in html.replace(" ", ""), \
            "odontologia template not found in initial_data"


# =============================================================================
# Tests: Crear usuario (no regression)
# =============================================================================


class TestCrearUsuario:
    """POST /auth/usuarios/crear — requires admin."""

    def test_create_user_success(self, app_client, tmp_path):
        """Valid new user → created, redirect with success."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/crear",
                data={
                    "username": "nuevo_user",
                    "password": "pass123",
                    "rol": "usuario",
                    "permisos": ["odontologia"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

    def test_create_duplicate(self, app_client, tmp_path):
        """Duplicate username → error flash."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/crear",
                data={
                    "username": "admin",
                    "password": "pass123",
                    "rol": "usuario",
                    "permisos": ["odontologia"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

    def test_create_user_with_person_fields(self, app_client, tmp_path):
        """POST with 4 person fields → stored in user record."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/crear",
                data={
                    "username": "nuevo_user",
                    "password": "pass123",
                    "rol": "usuario",
                    "permisos": ["odontologia"],
                    "primer_nombre": "Ana",
                    "segundo_nombre": "María",
                    "apellido_1": "López",
                    "apellido_2": "García",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            # Verify stored user has the person fields (inside patch context)
            user = users_store.get_user("nuevo_user")
            assert user is not None
            assert user["primer_nombre"] == "Ana"
            assert user["segundo_nombre"] == "María"
            assert user["apellido_1"] == "López"
            assert user["apellido_2"] == "García"


# =============================================================================
# Tests: Editar usuario (R2)
# =============================================================================


class TestEditarUsuario:
    """POST /auth/usuarios/<username>/editar — requires admin."""

    def test_edit_success(self, app_client, tmp_path):
        """Edit user password, rol, permisos → success flash."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/test_user/editar",
                data={
                    "username": "test_user",
                    "password": "newpass",
                    "rol": "admin",
                    "permisos": ["*"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

            # Verify in store
            updated = users_store.get_user("test_user")
            assert updated is not None
            assert updated["rol"] == "admin"
            assert updated["permisos"] == ["*"]

    def test_edit_password_empty(self, app_client, tmp_path):
        """Password empty → password unchanged, other fields updated."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/test_user/editar",
                data={
                    "username": "test_user",
                    "password": "",
                    "rol": "usuario",
                    "permisos": ["odontologia", "urgencias"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

            # Verify password unchanged (can log in with old password)
            creds = users_store.check_credentials("test_user", "test123")
            assert creds is not None

    def test_edit_self_remove_star(self, app_client, tmp_path):
        """Admin editing own user removing * → error flash, changes NOT saved."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/admin/editar",
                data={
                    "username": "admin",
                    "rol": "admin",
                    "permisos": ["odontologia"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

            # Verify admin still has * in store
            user = users_store.get_user("admin")
            assert user is not None
            assert "*" in user["permisos"]

    def test_edit_non_existent_user(self, app_client, tmp_path):
        """Non-existent user → error flash."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/ghost/editar",
                data={
                    "username": "ghost",
                    "rol": "usuario",
                    "permisos": ["odontologia"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

    def test_edit_unauthenticated(self, app_client):
        """No session → 401."""
        resp = app_client.post(
            "/auth/usuarios/test_user/editar",
            data={"rol": "admin"},
        )
        assert resp.status_code == 401

    def test_edit_non_admin(self, app_client):
        """Session without * → 403 or redirect."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        resp = app_client.post(
            "/auth/usuarios/test_user/editar",
            data={"rol": "admin"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Redirects to React dashboard (no flash)

    def test_edit_person_fields(self, app_client, tmp_path):
        """POST with primer_nombre and apellido_1 → only those fields updated."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/test_user/editar",
                data={
                    "username": "test_user",
                    "rol": "usuario",
                    "permisos": ["odontologia"],
                    "primer_nombre": "Ana",
                    "apellido_1": "López",
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            # Verify person fields updated (inside patch context)
            user = users_store.get_user("test_user")
            assert user is not None
            assert user["primer_nombre"] == "Ana"
            assert user["apellido_1"] == "López"
            # Other person fields preserved
            assert user["segundo_nombre"] == ""
            assert user["apellido_2"] == ""

    def test_edit_without_person_fields(self, app_client, tmp_path):
        """POST without person fields → existing values preserved."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/test_user/editar",
                data={
                    "username": "test_user",
                    "rol": "admin",
                    "permisos": ["*"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            # Verify person fields unchanged (inside patch context)
            user = users_store.get_user("test_user")
            assert user is not None
            assert user["primer_nombre"] == "Test"
            assert user["apellido_1"] == "User"


# =============================================================================
# Tests: Eliminar usuario (R3)
# =============================================================================


class TestEliminarUsuario:
    """POST /auth/usuarios/<username>/eliminar — requires admin."""

    def test_delete_existing_user(self, app_client, tmp_path):
        """Delete normal user → success flash, user removed."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/test_user/eliminar",
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

            # Verify user removed from store
            user = users_store.get_user("test_user")
            assert user is None

    def test_delete_admin_blocked(self, app_client, tmp_path):
        """Delete 'admin' user → error flash, admin NOT removed."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/admin/eliminar",
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

            # Verify admin still exists
            user = users_store.get_user("admin")
            assert user is not None

    def test_delete_non_existent_user(self, app_client, tmp_path):
        """Non-existent user → error flash."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/ghost/eliminar",
                follow_redirects=True,
            )
            assert resp.status_code == 200
            # Redirects to React usuarios page (no flash)

    def test_delete_unauthenticated(self, app_client):
        """No session → 401."""
        resp = app_client.post(
            "/auth/usuarios/test_user/eliminar",
        )
        assert resp.status_code == 401

    def test_delete_non_admin(self, app_client):
        """Session without * → 403 or redirect."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        resp = app_client.post(
            "/auth/usuarios/admin/eliminar",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Redirects to React dashboard (no flash)


# =============================================================================
# Tests: Crear/editar con áreas organizacionales (sdd Empieza)
# =============================================================================


class TestUsuarioAreas:
    """POST /auth/usuarios/crear y /editar pasan request.form.getlist('areas')."""

    def test_create_user_with_areas(self, app_client, tmp_path):
        """POST crear con areas → el usuario las persiste ordenadas."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/usuarios/crear",
                data={
                    "username": "nuevo_user",
                    "password": "pass123",
                    "rol": "facturador",
                    "permisos": ["urgencias"],
                    "primer_nombre": "Ana",
                    "apellido_1": "López",
                    "areas": ["urgencias", "odontologia"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            user = users_store.get_user("nuevo_user")
            assert user is not None
            assert user["areas"] == ["odontologia", "urgencias"]

    def test_edit_user_with_areas_replaces(self, app_client, tmp_path):
        """POST editar con areas → reemplaza las áreas previas (replace-all)."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            # Precondición real: el usuario ya tiene un área persistida
            users_store.create_user(
                "nuevo_user", "pass123", "facturador", ["urgencias"],
                areas=["urgencias"],
            )
            # Editar a otro set
            resp = app_client.post(
                "/auth/usuarios/nuevo_user/editar",
                data={
                    "username": "nuevo_user",
                    "rol": "facturador",
                    "permisos": ["urgencias"],
                    "areas": ["extramural"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            user = users_store.get_user("nuevo_user")
            assert user["areas"] == ["extramural"]

    def test_edit_user_clears_areas(self, app_client, tmp_path):
        """POST editar sin areas (getlist vacío) → limpia las áreas."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            # Precondición real: el usuario ya tiene áreas persistidas
            users_store.create_user(
                "nuevo_user", "pass123", "facturador", ["urgencias"],
                areas=["urgencias", "odontologia"],
            )
            resp = app_client.post(
                "/auth/usuarios/nuevo_user/editar",
                data={
                    "username": "nuevo_user",
                    "rol": "facturador",
                    "permisos": ["urgencias"],
                },
                follow_redirects=True,
            )
            assert resp.status_code == 200

            user = users_store.get_user("nuevo_user")
            assert user["areas"] == []


# =============================================================================
# Tests: Cambiar contraseña propia (self-service)
# =============================================================================


class TestCambiarContrasena:
    """POST /auth/api/cambiar-contrasena — self-service password change."""

    def test_happy_path(self, app_client, tmp_path):
        """Valid old + new password → 200, password updated."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"

            # Verify password was actually changed
            creds = users_store.check_credentials("admin", "newadmin456")
            assert creds is not None
            assert creds["username"] == "admin"

    def test_wrong_old_password(self, app_client, tmp_path):
        """Wrong old password → 400, error message, password unchanged."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "wrong_old",
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("contraseña actual" in e.lower() for e in data["errors"])

            # Verify password was NOT changed
            creds = users_store.check_credentials("admin", "admin123")
            assert creds is not None

    def test_new_password_too_short(self, app_client, tmp_path):
        """New password < 6 chars → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "abc12",
                    "confirm_password": "abc12",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("6 caracteres" in e.lower() or "mínimo" in e.lower() or "6" in e for e in data["errors"])

    def test_confirm_mismatch(self, app_client, tmp_path):
        """New password != confirm → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "newadmin456",
                    "confirm_password": "different456",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("no coinciden" in e.lower() for e in data["errors"])

    def test_missing_fields(self, app_client, tmp_path):
        """Missing old_password → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("requerido" in e.lower() for e in data["errors"])

    def test_missing_all_fields(self, app_client, tmp_path):
        """Empty JSON object → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert len(data["errors"]) > 0

    def test_unauthenticated(self, app_client):
        """No session → 401."""
        resp = app_client.post(
            "/auth/api/cambiar-contrasena",
            json={
                "old_password": "admin123",
                "new_password": "newadmin456",
                "confirm_password": "newadmin456",
            },
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert any("autenticado" in e.lower() for e in data["errors"])

    def test_session_intact_after_change(self, app_client, tmp_path):
        """Session remains authenticated after password change."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            # Change password
            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 200

            # Session should still be valid
            resp2 = app_client.get("/auth/api/status")
            assert resp2.status_code == 200
            status_data = resp2.get_json()
            assert status_data["data"]["authenticated"] is True
            assert status_data["data"]["username"] == "admin"

    def test_empty_old_password_string(self, app_client, tmp_path):
        """Empty string for old_password → 400, campo requerido."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "",
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("requerido" in e.lower() for e in data["errors"])

    def test_empty_new_password_string(self, app_client, tmp_path):
        """Empty string for new_password → 400, campo requerido."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "",
                    "confirm_password": "",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("requerido" in e.lower() for e in data["errors"])

    def test_empty_confirm_password_string(self, app_client, tmp_path):
        """Empty string for confirm_password → 400, campo requerido."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "newadmin456",
                    "confirm_password": "",
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("requerido" in e.lower() for e in data["errors"])

    def test_invalid_json_body(self, app_client, tmp_path):
        """Non-parsable JSON body → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                data="not-json-at-all",
                content_type="application/json",
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("inválido" in e.lower() or "json" in e.lower() for e in data["errors"])

    def test_new_password_same_as_old(self, app_client, tmp_path):
        """New password == old password → 200, re-hash succeeds."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "admin123",
                    "confirm_password": "admin123",
                },
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"

    def test_login_with_new_password(self, app_client, tmp_path):
        """After password change, login with new password works and old fails."""
        with _patched_store(_seed_users()):
            # Login with old password first
            app_client.post("/auth/login", data={
                "username": "admin",
                "password": "admin123",
            })

            # Change password via API
            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "newadmin456",
                    "confirm_password": "newadmin456",
                },
            )
            assert resp.status_code == 200

            # Logout
            app_client.post("/auth/api/logout")

            # Login with NEW password should work
            resp = app_client.post("/auth/api/login", json={
                "user": "admin",
                "pass": "newadmin456",
            })
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"

            # Logout
            app_client.post("/auth/api/logout")

            # Login with OLD password should FAIL
            resp = app_client.post("/auth/api/login", json={
                "user": "admin",
                "pass": "admin123",
            })
            assert resp.status_code == 401
            data = resp.get_json()
            assert data["status"] == "error"

    def test_new_password_too_long(self, app_client, tmp_path):
        """New password > 128 chars → 400, error message."""
        with _patched_store(_seed_users()):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.post(
                "/auth/api/cambiar-contrasena",
                json={
                    "old_password": "admin123",
                    "new_password": "x" * 129,
                    "confirm_password": "x" * 129,
                },
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["status"] == "error"
            assert any("128" in e for e in data["errors"])
