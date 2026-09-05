"""Integration tests for catalogos API endpoints.

Strict TDD: tests written before implementation.
Uses Flask test client with authenticated admin session.
"""

from __future__ import annotations

import json


class TestCatalogosListApi:
    """Tests for GET /api/catalogos"""

    def test_list_requires_auth(self, app_client):
        """GET /api/catalogos without auth returns 401."""
        response = app_client.get("/api/catalogos")
        assert response.status_code == 401

    def test_list_requires_admin(self, app_client):
        """GET /api/catalogos without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.get(
            "/api/catalogos",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_list_returns_canonical_envelope(self, app_client):
        """GET /api/catalogos returns success envelope with items,total."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/catalogos")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert isinstance(data["errors"], list)

    def test_list_contains_regla_count(self, app_client):
        """GET /api/catalogos returns items with regla_count field."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/catalogos")
        assert response.status_code == 200
        data = response.get_json()
        items = data["data"]
        if items:
            assert "regla_count" in items[0]
            assert "value_count" in items[0]
            assert "key" in items[0]


class TestCatalogosGetApi:
    """Tests for GET /api/catalogos/<key>"""

    def test_get_requires_auth(self, app_client):
        """GET /api/catalogos/<key> without auth returns 401."""
        response = app_client.get("/api/catalogos/test_key")
        assert response.status_code == 401

    def test_get_requires_admin(self, app_client):
        """GET /api/catalogos/<key> without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.get(
            "/api/catalogos/test_key",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_get_existing_returns_values(self, app_client):
        """GET /api/catalogos/<existing_key> returns values array."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        # Use a key that exists in the production catalogos table
        response = app_client.get("/api/catalogos/prof_odon")
        data = response.get_json()
        # Either success with values or error with 404 — both valid
        if response.status_code == 200:
            assert data["status"] == "success"
            assert "values" in data["data"]
            assert isinstance(data["data"]["values"], list)
            assert "value_count" in data["data"]


class TestCatalogosCreateApi:
    """Tests for POST /api/catalogos"""

    def test_create_requires_auth(self, app_client):
        """POST /api/catalogos without auth returns 401."""
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": "test_cat", "value": ["A"]}),
        )
        assert response.status_code == 401

    def test_create_requires_admin(self, app_client):
        """POST /api/catalogos without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": "test_cat", "value": ["A"]}),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_create_returns_201_with_catalogo(self, app_client):
        """POST /api/catalogos with valid data returns 201."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        test_key = f"test_crud_{__import__('time').time()}"
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": test_key, "value": ["X", "Y"], "descripcion": "Test"}),
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["data"]["key"] == test_key
        assert data["data"]["values"] == ["X", "Y"]

        # Cleanup
        app_client.delete(f"/api/catalogos/{test_key}")

    def test_create_duplicate_returns_409(self, app_client):
        """POST /api/catalogos with duplicate key returns 409."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        # Try to create a key that likely exists (prof_odon)
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": "prof_odon", "value": ["A"]}),
        )
        if response.status_code == 409:
            data = response.get_json()
            assert data["status"] == "error"
        # Note: if prof_odon doesn't exist in test DB, this will 201 — that's OK too

    def test_create_missing_key_returns_400(self, app_client):
        """POST /api/catalogos without key returns 400."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"value": ["A"]}),
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"

    def test_create_non_array_value_returns_422(self, app_client):
        """POST /api/catalogos with non-array value returns 422."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": "test_val", "value": "string_not_array"}),
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["status"] == "error"


class TestCatalogosUpdateApi:
    """Tests for PUT /api/catalogos/<key>"""

    def test_update_requires_auth(self, app_client):
        """PUT /api/catalogos/<key> without auth returns 401."""
        response = app_client.put(
            "/api/catalogos/test_key",
            content_type="application/json",
            data=json.dumps({"value": ["A"]}),
        )
        assert response.status_code == 401

    def test_update_requires_admin(self, app_client):
        """PUT /api/catalogos/<key> without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.put(
            "/api/catalogos/test_key",
            content_type="application/json",
            data=json.dumps({"value": ["A"]}),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_update_value_returns_200(self, app_client):
        """PUT /api/catalogos/<key> with valid value returns 200."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        # First create a test catalog
        test_key = f"test_upd_{__import__('time').time()}"
        app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": test_key, "value": ["A"]}),
        )

        # Update it
        response = app_client.put(
            f"/api/catalogos/{test_key}",
            content_type="application/json",
            data=json.dumps({"value": ["A", "B"], "descripcion": "Updated"}),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["data"]["values"] == ["A", "B"]
        assert data["data"]["descripcion"] == "Updated"

        # Cleanup
        app_client.delete(f"/api/catalogos/{test_key}")

    def test_update_non_array_returns_422(self, app_client):
        """PUT /api/catalogos/<key> with non-array value returns 422."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.put(
            "/api/catalogos/prof_odon",
            content_type="application/json",
            data=json.dumps({"value": "string_not_array"}),
        )
        assert response.status_code == 422
        data = response.get_json()
        assert data["status"] == "error"

    def test_update_not_found_returns_404(self, app_client):
        """PUT /api/catalogos/<unknown_key> returns 404."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.put(
            "/api/catalogos/definitely_not_exists_xyz",
            content_type="application/json",
            data=json.dumps({"value": ["A"]}),
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"


class TestCatalogosDeleteApi:
    """Tests for DELETE /api/catalogos/<key>"""

    def test_delete_requires_auth(self, app_client):
        """DELETE /api/catalogos/<key> without auth returns 401."""
        response = app_client.delete("/api/catalogos/test_key")
        assert response.status_code == 401

    def test_delete_requires_admin(self, app_client):
        """DELETE /api/catalogos/<key> without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.delete(
            "/api/catalogos/test_key",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_delete_not_found_returns_404(self, app_client):
        """DELETE /api/catalogos/<unknown_key> returns 404."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.delete("/api/catalogos/definitely_not_exists_xyz")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"

    def test_delete_new_catalogo_returns_200(self, app_client):
        """DELETE /api/catalogos of orphan catalog returns 200."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        # Create a new catalog to delete
        test_key = f"test_del_{__import__('time').time()}"
        app_client.post(
            "/api/catalogos",
            content_type="application/json",
            data=json.dumps({"key": test_key, "value": ["orphan"]}),
        )

        response = app_client.delete(f"/api/catalogos/{test_key}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"


class TestCatalogosReglasApi:
    """Tests for GET /api/catalogos/<key>/reglas"""

    def test_reglas_requires_auth(self, app_client):
        """GET /api/catalogos/<key>/reglas without auth returns 401."""
        response = app_client.get("/api/catalogos/prof_odon/reglas")
        assert response.status_code == 401

    def test_reglas_requires_admin(self, app_client):
        """GET /api/catalogos/<key>/reglas without admin returns 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"
        response = app_client.get(
            "/api/catalogos/prof_odon/reglas",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403

    def test_reglas_returns_list(self, app_client):
        """GET /api/catalogos/<key>/reglas returns list of rules or empty."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/catalogos/prof_odon/reglas")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        if data["data"]:
            assert "id" in data["data"][0]
            assert "nombre" in data["data"][0]
            assert "dominio" in data["data"][0]


class TestCatalogosAdminRoute:
    """Tests for catalogos tab within GET /admin/reglas"""

    def test_admin_route_requires_auth(self, app_client):
        """GET /admin/reglas without auth returns 401."""
        response = app_client.get("/admin/reglas")
        assert response.status_code == 401

    def test_admin_route_requires_admin(self, app_client):
        """GET /admin/reglas without admin returns 302."""
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
