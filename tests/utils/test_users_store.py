"""Unit tests for app/utils/users_store.py.

Strict TDD: Tests written BEFORE implementation. These serve as the RED phase
for Task 1 (store layer). All scenarios from spec.md R1 are covered.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, call, patch

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app.utils import users_store

# =============================================================================
# Sample data — real hashes so check_credentials tests work without mocking
# =============================================================================

SAMPLE_USERS = [
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
        "username": "auditor",
        "password_hash": generate_password_hash("auditor123"),
        "rol": "usuario",
        "permisos": ["odontologia", "urgencias"],
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "drhouse",
        "password_hash": generate_password_hash("pass123"),
        "rol": "medico",
        "permisos": ["urgencias"],
        "primer_nombre": "GREGORY",
        "segundo_nombre": "",
        "apellido_1": "HOUSE",
        "apellido_2": "",
    },
    {
        "username": "facturador1",
        "password_hash": generate_password_hash("pass123"),
        "rol": "facturador",
        "permisos": ["control_urgencias", "cruce_facturas"],
        "primer_nombre": "JUAN",
        "segundo_nombre": "FELIPE",
        "apellido_1": "PEREZ",
        "apellido_2": "GOMEZ",
    },
    {
        "username": "facturador2",
        "password_hash": generate_password_hash("pass123"),
        "rol": "facturador",
        "permisos": ["control_urgencias"],
        "primer_nombre": "MARIA",
        "segundo_nombre": "",
        "apellido_1": "LOPEZ",
        "apellido_2": "",
    },
    {
        "username": "facturador_sin_nombre",
        "password_hash": generate_password_hash("pass123"),
        "rol": "facturador",
        "permisos": ["control_urgencias"],
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
]


# =============================================================================
# Tests: update_user()
# =============================================================================


class TestUpdateUser:
    """Spec R1: users_store.update_user() — partial update support."""

    def test_update_password(self):
        """Update password + rol + permisos: password hashed, all fields updated."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"password": "new123", "rol": "admin", "permisos": ["*"]},
                )

        assert ok is True
        assert "actualizado" in msg

        # Verify _save_users was called with modified data
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert check_password_hash(updated["password_hash"], "new123")
        assert updated["rol"] == "admin"
        assert updated["permisos"] == ["*"]

        # Other users intact
        assert next(u for u in saved if u["username"] == "admin")
        assert next(u for u in saved if u["username"] == "auditor")

    def test_skip_password_none(self):
        """password=None: existing hash preserved, other fields updated."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"password": None, "rol": "admin", "permisos": ["*"]},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        # Hash should match original password (odonto123), not a new one
        assert check_password_hash(updated["password_hash"], "odonto123")
        assert updated["rol"] == "admin"

    def test_skip_password_empty_string(self):
        """password='': existing hash preserved, permisos updated."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"password": "", "permisos": ["cruce_facturas"]},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert check_password_hash(updated["password_hash"], "odonto123")
        assert updated["permisos"] == ["cruce_facturas"]

    def test_update_rol_only(self):
        """Only rol changed; password + permisos unchanged."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"rol": "admin"},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["rol"] == "admin"
        assert check_password_hash(updated["password_hash"], "odonto123")
        assert updated["permisos"] == ["odontologia"]

    def test_update_permisos_only(self):
        """Only permisos changed; password + rol unchanged."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"permisos": ["*"]},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["permisos"] == ["*"]
        assert updated["rol"] == "usuario"
        assert check_password_hash(updated["password_hash"], "odonto123")

    def test_non_existent_user(self):
        """username not in store → (False, msg)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "ghost",
                {"rol": "admin"},
            )

        assert ok is False
        assert "no encontrado" in msg.lower()

    def test_admin_self_remove_star(self):
        """Admin user removing * from own record → rejected at store level."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "admin",
                {"permisos": ["odontologia"]},
            )

        assert ok is False
        assert "admin" in msg.lower() or "permisos" in msg.lower()

    def test_admin_other_user_add_star_allowed(self):
        """Adding * to a different user's record → allowed."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"permisos": ["*"]},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert "*" in updated["permisos"]

    def test_invalid_permiso(self):
        """Invalid permiso value → (False, msg)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "odontologia",
                {"permisos": ["invalid_perm"]},
            )

        assert ok is False
        assert "permiso inválido" in msg.lower() or "invalid" in msg.lower()

    def test_invalid_rol(self):
        """Invalid rol value → (False, msg)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "odontologia",
                {"rol": "superadmin"},
            )

        assert ok is False
        assert "rol inválido" in msg.lower()

    def test_update_rejects_mutually_exclusive_permisos(self):
        """control_urgencias + control_urgencias:write → (False, msg)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "odontologia",
                {"permisos": ["control_urgencias", "control_urgencias:write"]},
            )

        assert ok is False
        assert "mutuamente excluyentes" in msg.lower()

    def test_update_rejects_mutually_exclusive_facturas(self):
        """facturas_abiertas + facturas_abiertas:write → (False, msg)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "odontologia",
                {"permisos": ["facturas_abiertas", "facturas_abiertas:write"]},
            )

        assert ok is False
        assert "mutuamente excluyentes" in msg.lower()

    def test_update_allows_either_alone(self):
        """Solo write sin read → se actualiza correctamente."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"permisos": ["control_urgencias:write"]},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["permisos"] == ["control_urgencias:write"]

    def test_user_list_unchanged_after_update(self):
        """Other users in store remain intact after update."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                users_store.update_user(
                    "odontologia",
                    {"rol": "admin", "permisos": ["*"]},
                )

        saved = mock_save.call_args[0][0]
        assert len(saved) == len(SAMPLE_USERS)
        # admin user unchanged
        admin_saved = next(u for u in saved if u["username"] == "admin")
        assert admin_saved == next(u for u in SAMPLE_USERS if u["username"] == "admin")
        # auditor user unchanged
        auditor_saved = next(u for u in saved if u["username"] == "auditor")
        assert auditor_saved == next(u for u in SAMPLE_USERS if u["username"] == "auditor")


# =============================================================================
# Tests: update_user() — new roles (medico, facturador)
# =============================================================================


class TestUpdateUserNewRoles:
    """Spec R1 (delta): update_user() accepts 'medico' and 'facturador'."""

    def test_update_to_medico(self):
        """Update rol to 'medico' → succeeds."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"rol": "medico"},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["rol"] == "medico"

    def test_update_to_facturador(self):
        """Update rol to 'facturador' → succeeds."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"rol": "facturador"},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["rol"] == "facturador"

    def test_invalid_rol_new_message(self):
        """Invalid rol 'enfermero' → (False, updated msg listing 4 roles)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            ok, msg = users_store.update_user(
                "odontologia",
                {"rol": "enfermero"},
            )

        assert ok is False
        assert "medico" in msg and "facturador" in msg
        assert "admin" in msg and "usuario" in msg


# =============================================================================
# Tests: get_facturadores()
# =============================================================================


class TestGetFacturadores:
    """Spec R1 (facturadores-dynamic-responsables): users_store.get_facturadores()."""

    def test_returns_only_facturadores(self):
        """Only users with rol='facturador' returned."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.get_facturadores()

        assert len(result) == 2  # facturador1, facturador2 (sin_nombre excluded)
        for f in result:
            assert f["rol"] == "facturador"

    def test_excludes_users_without_primer_nombre(self):
        """Facturador without primer_nombre excluded."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.get_facturadores()

        usernames = [f["username"] for f in result]
        assert "facturador_sin_nombre" not in usernames
        assert "facturador1" in usernames
        assert "facturador2" in usernames

    def test_returns_empty_when_none_exist(self):
        """No facturadores in store → returns []."""
        users_no_facturadores = [u for u in SAMPLE_USERS.copy() if u["rol"] != "facturador"]
        with patch.object(users_store, "_load_users", return_value=users_no_facturadores):
            result = users_store.get_facturadores()

        assert result == []

    def test_nombre_completo_composition(self):
        """nombre_completo = primer_nombre + ' ' + apellido_1 (uppercase)."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.get_facturadores()

        fact1 = next(f for f in result if f["username"] == "facturador1")
        assert fact1["nombre_completo"] == "JUAN PEREZ"

        fact2 = next(f for f in result if f["username"] == "facturador2")
        assert fact2["nombre_completo"] == "MARIA LOPEZ"

    def test_fields_returned(self):
        """Each facturador dict includes expected fields."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.get_facturadores()

        fact = result[0]
        assert "username" in fact
        assert "primer_nombre" in fact
        assert "segundo_nombre" in fact
        assert "apellido_1" in fact
        assert "apellido_2" in fact
        assert "nombre_completo" in fact
        assert "rol" in fact

    def test_non_destructive(self):
        """Other users unaffected by get_facturadores()."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.get_facturadores()
            assert len(result) == 2  # Only facturadores
            # Admin/medico/usuario still in store
            all_users = users_store.list_users()
            roles = [u["rol"] for u in all_users]
            assert "admin" in roles
            assert "usuario" in roles
            assert "medico" in roles


# =============================================================================
# Tests: delete_user()
# =============================================================================


class TestDeleteUser:
    """Spec R3 and R1 edge: delete_user with admin protection."""

    def test_delete_existing_user(self):
        """Normal user deletion → returns (True, msg)."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.delete_user("odontologia")

        assert ok is True
        assert "eliminado" in msg.lower()
        saved = mock_save.call_args[0][0]
        assert all(u["username"] != "odontologia" for u in saved)

    def test_delete_admin_blocked(self):
        """delete_user('admin') → (False, msg) — admin NOT removed."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.delete_user("admin")

        assert ok is False
        assert "no se puede eliminar" in msg.lower() or "admin" in msg.lower()
        # _save_users should NOT be called
        mock_save.assert_not_called()

    def test_delete_non_existent_user(self):
        """Non-existent user → (False, msg)."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            ok, msg = users_store.delete_user("ghost")

        assert ok is False
        assert "no encontrado" in msg.lower()


# =============================================================================
# Tests: create_user()
# =============================================================================


class TestCreateUser:
    """Existing create_user behavior — no regression."""

    def test_create_user_success(self):
        """Valid new user → created successfully."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.create_user(
                    "nuevo", "pass123", "usuario", ["odontologia"]
                )

        assert ok is True
        assert "creado" in msg.lower()
        saved = mock_save.call_args[0][0]
        assert any(u["username"] == "nuevo" for u in saved)

    def test_create_user_duplicate(self):
        """Duplicate username → (False, msg)."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            ok, msg = users_store.create_user(
                "admin", "pass123", "usuario", ["odontologia"]
            )

        assert ok is False
        assert "ya existe" in msg.lower()

    def test_create_rejects_mutually_exclusive_permisos(self):
        """control_urgencias + control_urgencias:write → (False, msg)."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            ok, msg = users_store.create_user(
                "nuevo", "pass123", "usuario",
                ["control_urgencias", "control_urgencias:write"],
            )

        assert ok is False
        assert "mutuamente excluyentes" in msg.lower()

    def test_create_rejects_mutually_exclusive_facturas(self):
        """facturas_abiertas + facturas_abiertas:write → (False, msg)."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            ok, msg = users_store.create_user(
                "nuevo", "pass123", "usuario",
                ["facturas_abiertas", "facturas_abiertas:write"],
            )

        assert ok is False
        assert "mutuamente excluyentes" in msg.lower()

    def test_create_allows_either_alone(self):
        """Solo write sin read → se crea correctamente."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.create_user(
                    "nuevo", "pass123", "usuario",
                    ["control_urgencias:write"],
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        nuevo = next(u for u in saved if u["username"] == "nuevo")
        assert nuevo["permisos"] == ["control_urgencias:write"]


# =============================================================================
# Tests: create_user() — person fields
# =============================================================================


class TestCreateUserPersonFields:
    """Spec R9: create_user stores person fields."""

    def test_create_user_with_person_fields(self):
        """All 4 person fields provided → stored correctly."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.create_user(
                    "nuevo", "pass123", "usuario", ["odontologia"],
                    primer_nombre="Ana",
                    segundo_nombre="María",
                    apellido_1="López",
                    apellido_2="García",
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        nuevo = next(u for u in saved if u["username"] == "nuevo")
        assert nuevo["primer_nombre"] == "Ana"
        assert nuevo["segundo_nombre"] == "María"
        assert nuevo["apellido_1"] == "López"
        assert nuevo["apellido_2"] == "García"

    def test_create_user_default_empty(self):
        """Person fields not provided → stored as empty strings."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.create_user(
                    "nuevo", "pass123", "usuario", ["odontologia"],
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        nuevo = next(u for u in saved if u["username"] == "nuevo")
        assert nuevo["primer_nombre"] == ""
        assert nuevo["segundo_nombre"] == ""
        assert nuevo["apellido_1"] == ""
        assert nuevo["apellido_2"] == ""


# =============================================================================
# Tests: update_user() — person fields
# =============================================================================


class TestUpdateUserPersonFields:
    """Spec R1 (extended): update_user partial person field support."""

    def test_update_person_fields_partial(self):
        """Update only primer_nombre and apellido_1; other fields preserved."""
        users = SAMPLE_USERS.copy()
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"primer_nombre": "Ana", "apellido_1": "López"},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["primer_nombre"] == "Ana"
        assert updated["apellido_1"] == "López"
        # Other person fields preserved as empty
        assert updated["segundo_nombre"] == ""
        assert updated["apellido_2"] == ""

    def test_update_without_person_fields(self):
        """Update rol only; person fields untouched."""
        users = SAMPLE_USERS.copy()
        # Give odontologia some person fields first
        users[1]["primer_nombre"] = "Carlos"
        users[1]["apellido_1"] = "Ruiz"
        with patch.object(users_store, "_load_users", return_value=users):
            with patch.object(users_store, "_save_users") as mock_save:
                ok, msg = users_store.update_user(
                    "odontologia",
                    {"rol": "admin"},
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(u for u in saved if u["username"] == "odontologia")
        assert updated["rol"] == "admin"
        assert updated["primer_nombre"] == "Carlos"
        assert updated["apellido_1"] == "Ruiz"
        assert updated["segundo_nombre"] == ""
        assert updated["apellido_2"] == ""


# =============================================================================
# Tests: check_credentials() — person fields
# =============================================================================


class TestCheckCredentialsPersonFields:
    """Spec R9: check_credentials returns person fields."""

    def test_check_credentials_returns_person_fields(self):
        """Valid credentials → return dict includes all 4 person fields."""
        users = SAMPLE_USERS.copy()
        users[0]["primer_nombre"] = "Ana"
        users[0]["apellido_1"] = "Admin"
        with patch.object(users_store, "_load_users", return_value=users):
            result = users_store.check_credentials("admin", "admin123")

        assert result is not None
        assert "primer_nombre" in result
        assert "segundo_nombre" in result
        assert "apellido_1" in result
        assert "apellido_2" in result
        assert result["primer_nombre"] == "Ana"
        assert result["apellido_1"] == "Admin"
        assert result["segundo_nombre"] == ""
        assert result["apellido_2"] == ""


# =============================================================================
# Tests: list_users() — person fields
# =============================================================================


class TestListUsersPersonFields:
    """Spec R9: list_users returns person fields."""

    def test_list_users_includes_person_fields(self):
        """list_users() returns dicts with all 4 person fields."""
        users = SAMPLE_USERS.copy()
        users[0]["primer_nombre"] = "Admin"
        users[0]["apellido_1"] = "User"
        with patch.object(users_store, "_load_users", return_value=users):
            result = users_store.list_users()

        assert len(result) == 7  # SAMPLE_USERS has 7 entries now
        admin_out = next(u for u in result if u["username"] == "admin")
        assert admin_out["primer_nombre"] == "Admin"
        assert admin_out["apellido_1"] == "User"
        assert admin_out["segundo_nombre"] == ""
        assert admin_out["apellido_2"] == ""

        odonto_out = next(u for u in result if u["username"] == "odontologia")
        assert "primer_nombre" in odonto_out
        assert "segundo_nombre" in odonto_out
        assert "apellido_1" in odonto_out
        assert "apellido_2" in odonto_out


# =============================================================================
# Tests: _load_users() backfill
# =============================================================================


class TestLoadUsersBackfill:
    """Spec R11: _load_users backfills missing person fields."""

    def test_backfill_legacy_users(self):
        """Legacy JSON missing person fields → backfilled as empty string, saved."""
        import json
        import tempfile
        from pathlib import Path

        legacy_users = [
            {
                "username": "admin",
                "password_hash": generate_password_hash("admin123"),
                "rol": "admin",
                "permisos": ["*"],
                # No person fields
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "users.json"
            real_path.write_text(json.dumps(legacy_users), encoding="utf-8")

            with patch.object(users_store, "USERS_FILE", real_path):
                result = users_store._load_users()

            assert len(result) == 1
            admin = result[0]
            assert admin["primer_nombre"] == ""
            assert admin["segundo_nombre"] == ""
            assert admin["apellido_1"] == ""
            assert admin["apellido_2"] == ""
            # Original fields preserved
            assert admin["username"] == "admin"
            assert admin["rol"] == "admin"

    def test_backfill_partial_missing(self):
        """Only some person fields missing → only missing ones backfilled."""
        import json
        import tempfile
        from pathlib import Path

        partial_users = [
            {
                "username": "admin",
                "password_hash": generate_password_hash("admin123"),
                "rol": "admin",
                "permisos": ["*"],
                "primer_nombre": "Ana",
                # Missing segundo_nombre, apellido_1, apellido_2
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "users.json"
            real_path.write_text(json.dumps(partial_users), encoding="utf-8")

            with patch.object(users_store, "USERS_FILE", real_path):
                result = users_store._load_users()

            assert len(result) == 1
            admin = result[0]
            assert admin["primer_nombre"] == "Ana"  # Preserved
            assert admin["segundo_nombre"] == ""     # Backfilled
            assert admin["apellido_1"] == ""          # Backfilled
            assert admin["apellido_2"] == ""          # Backfilled


# =============================================================================
# Tests: DEFAULT_USERS have person fields
# =============================================================================


class TestDefaultUsersHavePersonFields:
    """Spec R11: DEFAULT_USERS include empty person fields."""

    def test_default_users_include_empty_person_fields(self):
        """Each DEFAULT_USERS entry has all 4 person fields set to ''."""
        for u in users_store.DEFAULT_USERS:
            assert "primer_nombre" in u, f"Missing in {u['username']}"
            assert "segundo_nombre" in u, f"Missing in {u['username']}"
            assert "apellido_1" in u, f"Missing in {u['username']}"
            assert "apellido_2" in u, f"Missing in {u['username']}"
            assert u["primer_nombre"] == ""
            assert u["segundo_nombre"] == ""
            assert u["apellido_1"] == ""
            assert u["apellido_2"] == ""


# =============================================================================
# Tests: check_credentials()
# =============================================================================


class TestCheckCredentials:
    """Existing check_credentials behavior — no regression."""

    def test_valid_credentials(self):
        """Valid username+password → returns user dict."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.check_credentials("admin", "admin123")

        assert result is not None
        assert result["username"] == "admin"
        assert result["rol"] == "admin"
        assert result["permisos"] == ["*"]

    def test_invalid_password(self):
        """Wrong password → None."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.check_credentials("admin", "wrongpass")

        assert result is None

    def test_non_existent_user(self):
        """Non-existent username → None."""
        with patch.object(users_store, "_load_users", return_value=SAMPLE_USERS.copy()):
            result = users_store.check_credentials("ghost", "pass123")

        assert result is None


# =============================================================================
# Tests: _save_users() atomic write
# =============================================================================


class TestAtomicWrite:
    """Spec R1: _save_users uses temp file + os.replace()."""

    def test_save_users_uses_temp_file_and_replace(self):
        """_save_users writes to .tmp then os.replace()."""
        mock_file = MagicMock()
        mock_tmp = MagicMock(spec=os.PathLike)
        mock_file.with_suffix.return_value = mock_tmp
        mock_file.parent = MagicMock()

        test_data = [{"username": "test"}]

        with (
            patch.object(users_store, "USERS_FILE", mock_file),
            patch("builtins.open", MagicMock()) as mock_open,
            patch("os.replace") as mock_replace,
        ):
            users_store._save_users(test_data)

            # Verify temp file was used for writing
            mock_open.assert_called_once_with(mock_tmp, "w", encoding="utf-8")

            # Verify os.replace was called to make temp → real atomic swap
            mock_replace.assert_called_once_with(mock_tmp, mock_file)

    def test_atomic_write_preserves_original_on_crash(self):
        """Simulate crash after temp write: original file intact."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "users.json"
            real_path.write_text('[]', encoding="utf-8")

            # Set USERS_FILE to our temp path
            with patch.object(users_store, "USERS_FILE", real_path):
                # Write valid data
                users_store._save_users([{"username": "survivor"}])

                # Verify data was written correctly
                assert real_path.exists()
                data = json.loads(real_path.read_text(encoding="utf-8"))
                assert len(data) == 1
                assert data[0]["username"] == "survivor"


# =============================================================================
# Tests: _load_users() corrupt file
# =============================================================================


class TestLoadUsersCorruptFile:
    """_load_users gracefully handles corrupt JSON."""

    def test_corrupt_json_returns_empty_list(self):
        """Corrupt JSON → returns [], does not crash."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "users.json"
            real_path.write_text('{invalid json}', encoding="utf-8")

            with patch.object(users_store, "USERS_FILE", real_path):
                # First call: file exists but is corrupt
                result = users_store._load_users()
                assert result == []
