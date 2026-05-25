"""Unit tests for app/utils/templates_store.py.

Strict TDD: Tests written BEFORE implementation. All scenarios from spec.md
R1 (CRUD) and R2 (default seeding) are covered.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.constants.base import DEFAULT_TEMPLATES


# =============================================================================
# Sample data
# =============================================================================

SAMPLE_TEMPLATES = [
    {
        "nombre": "odontologia",
        "descripcion": "Solo módulo de odontología",
        "permisos": ["odontologia"],
    },
    {
        "nombre": "urgencias",
        "descripcion": "Urgencias + control + facturas abiertas (solo lectura)",
        "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
    },
    {
        "nombre": "auditor",
        "descripcion": "Control urgencias + facturas abiertas + equipos básicos (con modificación)",
        "permisos": [
            "control_urgencias",
            "control_urgencias:write",
            "facturas_abiertas",
            "facturas_abiertas:write",
            "equipos_basicos",
        ],
    },
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def templates_store():
    """Import templates_store module (fresh per test)."""
    import importlib
    from app.utils import templates_store
    importlib.reload(templates_store)
    return templates_store


# =============================================================================
# Tests: list_templates()
# =============================================================================


class TestListTemplates:
    """Spec R1: list_templates() returns all templates."""

    def test_list_templates(self, templates_store):
        """list_templates() returns copies of all templates."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            result = templates_store.list_templates()

        assert len(result) == 3
        assert result[0]["nombre"] == "odontologia"
        assert result[1]["nombre"] == "urgencias"
        assert result[2]["nombre"] == "auditor"

    def test_list_templates_returns_copies(self, templates_store):
        """Modifying returned list does not affect internal state."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            result = templates_store.list_templates()
            result.append({"nombre": "hacked"})

            # Call again — should NOT include "hacked"
            result2 = templates_store.list_templates()
            assert len(result2) == 3
            assert all(t["nombre"] != "hacked" for t in result2)


# =============================================================================
# Tests: get_template()
# =============================================================================


class TestGetTemplate:
    """Spec R1: get_template() returns a template by nombre."""

    def test_get_template_exists(self, templates_store):
        """Existing template → returns full dict."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            result = templates_store.get_template("odontologia")

        assert result is not None
        assert result["nombre"] == "odontologia"
        assert "descripcion" in result
        assert result["permisos"] == ["odontologia"]

    def test_get_template_missing(self, templates_store):
        """Non-existent template → returns None."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            result = templates_store.get_template("ghost")

        assert result is None

    def test_get_template_returns_copy(self, templates_store):
        """Modifying returned dict does not affect internal state."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            result = templates_store.get_template("odontologia")
            result["nombre"] = "hacked"

            # Call again — should still be original
            result2 = templates_store.get_template("odontologia")
            assert result2["nombre"] == "odontologia"


# =============================================================================
# Tests: create_template()
# =============================================================================


class TestCreateTemplate:
    """Spec R1: create_template() creates a new template."""

    def test_create_template_success(self, templates_store):
        """Valid new template → returns (True, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.create_template(
                    "mi_perfil", "Mi perfil personalizado", ["odontologia"]
                )

        assert ok is True
        assert "creada" in msg.lower() or "mi_perfil" in msg.lower()
        saved = mock_save.call_args[0][0]
        assert any(t["nombre"] == "mi_perfil" for t in saved)

    def test_create_template_duplicate(self, templates_store):
        """Duplicate nombre → returns (False, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.create_template(
                "odontologia", "Duplicado", ["odontologia"]
            )

        assert ok is False
        assert "ya existe" in msg.lower()

    def test_create_template_validates_permisos(self, templates_store):
        """Invalid permiso value → returns (False, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.create_template(
                "test", "Test", ["invalid_perm"]
            )

        assert ok is False
        assert "permiso inválido" in msg.lower() or "invalid" in msg.lower()

    def test_create_template_minimal(self, templates_store):
        """Template with single permiso → created successfully."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.create_template(
                    "solo_odonto", "Solo odontología", ["odontologia"]
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        entry = next(t for t in saved if t["nombre"] == "solo_odonto")
        assert entry["permisos"] == ["odontologia"]


# =============================================================================
# Tests: update_template()
# =============================================================================


class TestUpdateTemplate:
    """Spec R1: update_template() partial update."""

    def test_update_template_nombre(self, templates_store):
        """Update nombre → template renamed."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.update_template(
                    "odontologia", {"nombre": "odonto_v2"}
                )

        assert ok is True
        assert "actualizada" in msg.lower() or "odonto_v2" in msg.lower()
        saved = mock_save.call_args[0][0]
        renamed = next(t for t in saved if t["nombre"] == "odonto_v2")
        assert renamed is not None
        assert all(t["nombre"] != "odontologia" for t in saved)

    def test_update_template_permisos(self, templates_store):
        """Update permisos → permisos replaced."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.update_template(
                    "odontologia", {"permisos": ["odontologia", "equipos_basicos"]}
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(t for t in saved if t["nombre"] == "odontologia")
        assert updated["permisos"] == ["odontologia", "equipos_basicos"]

    def test_update_template_descripcion(self, templates_store):
        """Update descripcion → descripcion replaced."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.update_template(
                    "odontologia", {"descripcion": "Nueva descripción"}
                )

        assert ok is True
        saved = mock_save.call_args[0][0]
        updated = next(t for t in saved if t["nombre"] == "odontologia")
        assert updated["descripcion"] == "Nueva descripción"

    def test_update_template_missing(self, templates_store):
        """Non-existent template → returns (False, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.update_template(
                "ghost", {"nombre": "nuevo"}
            )

        assert ok is False
        assert "no encontrada" in msg.lower()

    def test_update_template_validates_permisos(self, templates_store):
        """Update with invalid permiso → returns (False, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.update_template(
                "odontologia", {"permisos": ["invalid_perm"]}
            )

        assert ok is False
        assert "permiso inválido" in msg.lower() or "invalid" in msg.lower()


# =============================================================================
# Tests: delete_template()
# =============================================================================


class TestDeleteTemplate:
    """Spec R1/R4: delete_template with default protection."""

    def test_delete_template_custom(self, templates_store):
        """Non-default template → removed successfully."""
        templates = SAMPLE_TEMPLATES.copy() + [{"nombre": "mi_perfil", "descripcion": "...", "permisos": ["odontologia"]}]
        with patch.object(templates_store, "_load_templates", return_value=templates):
            with patch.object(templates_store, "_save_templates") as mock_save:
                ok, msg = templates_store.delete_template("mi_perfil")

        assert ok is True
        assert "eliminada" in msg.lower()
        saved = mock_save.call_args[0][0]
        assert all(t["nombre"] != "mi_perfil" for t in saved)

    def test_delete_template_default_blocked(self, templates_store):
        """Default template (odontologia) → blocked with error message."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.delete_template("odontologia")

        assert ok is False
        assert "no se puede eliminar" in msg.lower()
        assert "odontologia" in msg  # nombre should appear in message

    def test_delete_template_default_blocked_urgencias(self, templates_store):
        """Default template (urgencias) → blocked."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.delete_template("urgencias")

        assert ok is False
        assert "no se puede eliminar" in msg.lower()
        assert "urgencias" in msg

    def test_delete_template_default_blocked_auditor(self, templates_store):
        """Default template (auditor) → blocked."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.delete_template("auditor")

        assert ok is False
        assert "no se puede eliminar" in msg.lower()
        assert "auditor" in msg

    def test_delete_template_missing(self, templates_store):
        """Non-existent template → returns (False, msg)."""
        with patch.object(templates_store, "_load_templates", return_value=SAMPLE_TEMPLATES.copy()):
            ok, msg = templates_store.delete_template("ghost")

        assert ok is False
        assert "no encontrada" in msg.lower()


# =============================================================================
# Tests: _ensure_default_templates() - first boot seeding
# =============================================================================


class TestDefaultSeeding:
    """Spec R2: Default templates created on first boot."""

    def test_default_templates_seeded_on_first_load(self, templates_store):
        """No file exists → _load_templates() creates 3 defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "templates.json"
            assert not templates_path.exists()

            with patch.object(templates_store, "TEMPLATES_FILE", templates_path):
                result = templates_store._load_templates()

            assert len(result) == 3
            nombres = {t["nombre"] for t in result}
            assert nombres == {"odontologia", "urgencias", "auditor"}
            # File should now exist
            assert templates_path.exists()

    def test_existing_file_not_overwritten(self, templates_store):
        """File exists → loaded without creating duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "templates.json"
            # Write pre-existing data
            existing = [{"nombre": "custom", "descripcion": "...", "permisos": ["odontologia"]}]
            templates_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

            with patch.object(templates_store, "TEMPLATES_FILE", templates_path):
                result = templates_store._load_templates()

            assert len(result) == 1
            assert result[0]["nombre"] == "custom"


# =============================================================================
# Tests: corrupt file handling
# =============================================================================


class TestCorruptFile:
    """Spec EC: _load_templates() handles corrupt JSON."""

    def test_corrupt_json_returns_empty_list(self, templates_store):
        """Corrupt JSON → returns [], logged error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_path = Path(tmpdir) / "templates.json"
            templates_path.write_text("{invalid json}", encoding="utf-8")

            with patch.object(templates_store, "TEMPLATES_FILE", templates_path):
                result = templates_store._load_templates()

            assert result == []


# =============================================================================
# Tests: atomic write pattern
# =============================================================================


class TestAtomicWrite:
    """Spec R1: _save_templates uses temp file + os.replace()."""

    def test_save_templates_uses_temp_and_replace(self, templates_store):
        """_save_templates writes to .tmp then os.replace()."""
        mock_file = MagicMock()
        mock_tmp = MagicMock(spec=os.PathLike)
        mock_file.with_suffix.return_value = mock_tmp
        mock_file.parent = MagicMock()

        test_data = [{"nombre": "test", "descripcion": "...", "permisos": ["odontologia"]}]

        with (
            patch.object(templates_store, "TEMPLATES_FILE", mock_file),
            patch("builtins.open", MagicMock()) as mock_open,
            patch("os.replace") as mock_replace,
        ):
            templates_store._save_templates(test_data)

            # Verify temp file was used for writing
            mock_open.assert_called_once_with(mock_tmp, "w", encoding="utf-8")

            # Verify os.replace was called to make temp → real atomic swap
            mock_replace.assert_called_once_with(mock_tmp, mock_file)

    def test_atomic_write_preserves_data(self, templates_store):
        """Real temp file: save then load returns saved data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_path = Path(tmpdir) / "templates.json"

            with patch.object(templates_store, "TEMPLATES_FILE", real_path):
                templates_store._save_templates(SAMPLE_TEMPLATES)

            assert real_path.exists()
            data = json.loads(real_path.read_text(encoding="utf-8"))
            assert len(data) == 3
            assert data[0]["nombre"] == "odontologia"


# =============================================================================
# Tests: DEFAULT_TEMPLATES_NAMES helper
# =============================================================================


class TestDefaultTemplateNames:
    """DEFAULT_TEMPLATES_NAMES frozenset matches constant data."""

    def test_default_names_match_constant(self, templates_store):
        """DEFAULT_TEMPLATES_NAMES contains all names from DEFAULT_TEMPLATES."""
        expected = {t["nombre"] for t in DEFAULT_TEMPLATES}
        assert templates_store.DEFAULT_TEMPLATES_NAMES == expected

    def test_default_names_is_frozenset(self, templates_store):
        """DEFAULT_TEMPLATES_NAMES is a frozenset."""
        assert isinstance(templates_store.DEFAULT_TEMPLATES_NAMES, frozenset)
