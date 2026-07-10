"""Integration tests for GET /auth/api/users/facturadores.

Spec R2: dynamic facturadores endpoint used by control-errores,
carga masiva, and abiertas-urgencias.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app.utils import users_store


def _seed_with_facturadores(tmp_path):
    """Create users.json with 2 facturadores in a temp path."""
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
            "username": "jperez",
            "password_hash": generate_password_hash("pass123"),
            "rol": "facturador",
            "permisos": ["control_urgencias"],
            "primer_nombre": "JUAN",
            "segundo_nombre": "FELIPE",
            "apellido_1": "PEREZ",
            "apellido_2": "GOMEZ",
        },
        {
            "username": "mlopez",
            "password_hash": generate_password_hash("pass123"),
            "rol": "facturador",
            "permisos": ["control_urgencias", "cruce_facturas"],
            "primer_nombre": "MARIA",
            "segundo_nombre": "",
            "apellido_1": "LOPEZ",
            "apellido_2": "",
        },
    ]
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
    return users_file


def _seed_without_facturadores(tmp_path):
    """Create users.json with NO facturadores in a temp path."""
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
    ]
    users_file = tmp_path / "users.json"
    users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")
    return users_file


class TestApiFacturadores:
    """GET /auth/api/users/facturadores — 3 spec scenarios."""

    def test_success_with_facturadores(self, app_client, tmp_path):
        """Authenticated, 2 facturadores → status success, 2 entries."""
        users_file = _seed_with_facturadores(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.get("/auth/api/users/facturadores")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"
            assert data["errors"] == []

            facturadores = data["data"]["facturadores"]
            assert len(facturadores) == 2

            # Verify structure of each facturador entry
            usernames = [f["username"] for f in facturadores]
            assert "jperez" in usernames
            assert "mlopez" in usernames

            for f in facturadores:
                assert f["rol"] == "facturador"
                assert "nombre_completo" in f
                assert "primer_nombre" in f
                assert "segundo_nombre" in f
                assert "apellido_1" in f
                assert "apellido_2" in f

            # Verify nombres_completos map
            nombres_completos = data["data"]["responsables_nombres_completos"]
            assert "JUAN PEREZ" in nombres_completos
            assert nombres_completos["JUAN PEREZ"] == "JUAN FELIPE PEREZ GOMEZ"
            assert "MARIA LOPEZ" in nombres_completos
            assert nombres_completos["MARIA LOPEZ"] == "MARIA LOPEZ"

    def test_empty_when_no_facturadores(self, app_client, tmp_path):
        """Authenticated, 0 facturadores → empty lists in response."""
        users_file = _seed_without_facturadores(tmp_path)
        with patch.object(users_store, "USERS_FILE", users_file):
            with app_client.session_transaction() as sess:
                sess["ce_authenticated"] = True
                sess["permisos"] = ["*"]
                sess["username"] = "admin"

            resp = app_client.get("/auth/api/users/facturadores")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "success"
            assert data["data"]["facturadores"] == []
            assert data["data"]["responsables_nombres_completos"] == {}
            assert data["errors"] == []

    def test_unauthenticated_returns_401(self, app_client):
        """No session → 401 JSON (X-Requested-With) or redirect."""
        # Without X-Requested-With → redirect to login
        resp = app_client.get("/auth/api/users/facturadores")
        # The endpoint uses @login_requerido which checks request.is_json
        # or X-Requested-With header to decide between JSON vs redirect
        assert resp.status_code in (302, 401)

    def test_unauthenticated_returns_json_when_xhr(self, app_client):
        """No session + X-Requested-With → 401 JSON error."""
        resp = app_client.get(
            "/auth/api/users/facturadores",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data is not None
        assert data["status"] == "error"
        assert data["data"] == {}
        assert any("autenticado" in e.lower() for e in data["errors"])
