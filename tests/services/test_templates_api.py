"""Integration tests for GET /auth/api/templates.

Strict TDD: Tests written BEFORE implementation. All scenarios from spec.md
R3 (API endpoint) are covered.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils import templates_store


def _seed_templates(tmp_path):
    """Create a test templates.json with known templates in a temp path."""
    templates = [
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
    templates_file = tmp_path / "templates.json"
    templates_file.write_text(json.dumps(templates, indent=2), encoding="utf-8")
    return templates_file


# =============================================================================
# Tests: GET /auth/api/templates
# =============================================================================


class TestTemplatesAPI:
    """GET /auth/api/templates — requires admin."""

    def test_list_templates_as_admin(self, app_client, tmp_path):
        """Admin authenticated, 3 templates exist → 200 with templates."""
        templates_file = _seed_templates(tmp_path)
        with patch.object(templates_store, "TEMPLATES_FILE", templates_file):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.get("/auth/api/templates")
            assert resp.status_code == 200

            data = resp.get_json()
            assert data["status"] == "success"
            assert len(data["data"]["templates"]) == 3
            assert data["errors"] == []

            nombres = {t["nombre"] for t in data["data"]["templates"]}
            assert nombres == {"odontologia", "urgencias", "auditor"}

    def test_list_templates_unauthenticated(self, app_client):
        """No session → 401."""
        resp = app_client.get("/auth/api/templates")
        assert resp.status_code == 401

    def test_list_templates_non_admin(self, app_client):
        """Session without * permiso → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        resp = app_client.get(
            "/auth/api/templates",
            content_type="application/json",
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "Permiso denegado" in data["errors"][0]

    def test_list_templates_empty(self, app_client, tmp_path):
        """No templates in file → returns empty list."""
        templates_file = tmp_path / "templates.json"
        templates_file.write_text("[]", encoding="utf-8")
        with patch.object(templates_store, "TEMPLATES_FILE", templates_file):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.get("/auth/api/templates")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["data"]["templates"] == []
