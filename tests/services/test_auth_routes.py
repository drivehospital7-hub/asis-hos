"""Integration tests for auth routes (login, logout, CRUD, permissions).

Strict TDD: Tests written BEFORE implementation. These serve as the RED phase
for Task 3 (routes). All scenarios from spec.md R2 and R3 are covered.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from werkzeug.security import generate_password_hash

from app.utils import users_store


def _seed_users(tmp_path):
    """Create a test users.json with known users in a temp path."""
    users = [
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
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
    return users_file


# =============================================================================
# Tests: Login
# =============================================================================


class TestLogin:
    """Existing login behavior — no regression."""

    def test_login_success(self, app_client):
        """Valid credentials → redirect to React dashboard."""
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
        users_file = _seed_users(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
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
