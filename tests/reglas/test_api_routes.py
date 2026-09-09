"""Integration tests for reglas API endpoints.

Strict TDD: tests written before implementation.
Uses Flask test client with authenticated admin session.
"""

from __future__ import annotations

import json


class TestReglasApiList:
    """Tests for GET /api/reglas"""

    def test_list_rules_requires_auth(self, app_client):
        """GET /api/reglas without auth returns 401."""
        response = app_client.get("/api/reglas")
        assert response.status_code == 401

    def test_list_rules_requires_admin(self, app_client):
        """GET /api/reglas without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.get(
            "/api/reglas",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data["status"] == "error"

    def test_list_rules_returns_canonical_envelope(self, app_client):
        """GET /api/reglas returns success envelope."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/reglas")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert isinstance(data["errors"], list)


class TestReglasApiCreate:
    """Tests for POST /api/reglas"""

    def test_create_rule_requires_auth(self, app_client):
        """POST /api/reglas without auth returns 401."""
        response = app_client.post(
            "/api/reglas",
            content_type="application/json",
            data=json.dumps({"nombre": "Test", "dominio": "odontologia"}),
        )
        assert response.status_code == 401

    def test_create_rule_requires_admin(self, app_client):
        """POST /api/reglas without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.post(
            "/api/reglas",
            content_type="application/json",
            data=json.dumps({"nombre": "Test", "dominio": "odontologia"}),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403


class TestReglasApiGet:
    """Tests for GET /api/reglas/<id>"""

    def test_get_rule_not_found_returns_404_envelope(self, app_client):
        """GET /api/reglas/9999 returns 404 with error envelope."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/reglas/9999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0


class TestReglasApiUpdate:
    """Tests for PUT /api/reglas/<id>"""

    def test_update_rule_requires_auth(self, app_client):
        """PUT /api/reglas/1 without auth returns 401."""
        response = app_client.put(
            "/api/reglas/1",
            content_type="application/json",
            data=json.dumps({"nombre": "Updated"}),
        )
        assert response.status_code == 401


class TestReglasApiDelete:
    """Tests for DELETE /api/reglas/<id>"""

    def test_delete_rule_requires_auth(self, app_client):
        """DELETE /api/reglas/1 without auth returns 401."""
        response = app_client.delete("/api/reglas/1")
        assert response.status_code == 401


class TestReglasApiEvidence:
    """Tests for GET /api/evidencias"""

    def test_evidence_requires_auth(self, app_client):
        """GET /api/evidencias without auth returns 401."""
        response = app_client.get("/api/evidencias")
        assert response.status_code == 401

    def test_evidence_returns_canonical_envelope(self, app_client):
        """GET /api/evidencias returns success envelope for admin."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/evidencias")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "items" in data["data"]
        assert "total" in data["data"]


class TestReglasApiAudit:
    """Tests for GET /api/auditoria"""

    def test_audit_requires_auth(self, app_client):
        """GET /api/auditoria without auth returns 401."""
        response = app_client.get("/api/auditoria")
        assert response.status_code == 401

    def test_audit_returns_canonical_envelope(self, app_client):
        """GET /api/auditoria returns success envelope for admin."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/auditoria")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"


class TestReglasApiSimulator:
    """Tests for POST /api/reglas/simular"""

    def test_simulate_requires_auth(self, app_client):
        """POST /api/reglas/simular without auth returns 401."""
        response = app_client.post("/api/reglas/simular")
        assert response.status_code == 401


class TestReglasApiExceptions:
    """Tests for GET /api/reglas/<id>/excepciones"""

    def test_exceptions_requires_auth(self, app_client):
        """GET /api/reglas/1/excepciones without auth returns 401."""
        response = app_client.get("/api/reglas/1/excepciones")
        assert response.status_code == 401


class TestReglasAdminRoute:
    """Tests for GET /admin/reglas"""

    def test_admin_route_requires_auth(self, app_client):
        """GET /admin/reglas without auth returns 401."""
        response = app_client.get("/admin/reglas")
        assert response.status_code == 401

    def test_admin_route_requires_admin(self, app_client):
        """GET /admin/reglas without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.get("/admin/reglas", follow_redirects=False)
        assert response.status_code == 302

    def test_admin_route_returns_html_with_root(self, app_client):
        """GET /admin/reglas returns HTML with root div for admin."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/admin/reglas", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="root"' in html


def _create_rule_via_api(app_client, nombre: str) -> dict:
    """Login as admin and create an active rule with one condition via the API."""
    app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    payload = {
        "nombre": nombre,
        "descripcion": "Publish integration test",
        "dominio": "odontologia",
        "severidad": "alta",
        "condiciones": [{
            "tipo": "atomic",
            "operador": "eq",
            "fuente_datos": "campo_prueba",
            "valor_esperado": "X",
        }],
        "excepciones": [{
            "tipo_efecto": "skip",
            "condicion_json": {"factura": "EX-1"},
        }],
    }
    response = app_client.post(
        "/api/reglas",
        content_type="application/json",
        data=json.dumps(payload),
    )
    assert response.status_code == 201, response.get_json()
    rule = response.get_json()["data"]
    assert rule["estado"] == "active"
    return rule


class TestReglasApiDuplicate:
    """Tests for POST /api/reglas/<id>/duplicar"""

    def test_duplicate_requires_auth(self, app_client):
        """POST /duplicar without auth returns 401."""
        response = app_client.post("/api/reglas/1/duplicar")
        assert response.status_code == 401

    def test_duplicate_requires_admin(self, app_client):
        """POST /duplicar without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.post(
            "/api/reglas/1/duplicar",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_duplicate_returns_independent_active_rule(self, app_client):
        """Duplicating a rule returns a new active rule."""
        rule = _create_rule_via_api(app_client, f"Duplicate OK {__import__('time').time()}")
        response = app_client.post(f"/api/reglas/{rule['id']}/duplicar")

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["errors"] == []
        assert data["data"]["id"] != rule["id"]
        assert data["data"]["estado"] == "active"
        assert data["data"]["nombre"] == f"{rule['nombre']} (copia)"
        assert data["data"]["condiciones"][0]["fuente_datos"] == "campo_prueba"
        assert data["data"]["excepciones"][0]["condicion_json"] == {"factura": "EX-1"}
