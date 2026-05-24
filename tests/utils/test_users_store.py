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
    },
    {
        "username": "odontologia",
        "password_hash": generate_password_hash("odonto123"),
        "rol": "usuario",
        "permisos": ["odontologia"],
    },
    {
        "username": "auditor",
        "password_hash": generate_password_hash("auditor123"),
        "rol": "usuario",
        "permisos": ["odontologia", "urgencias"],
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
