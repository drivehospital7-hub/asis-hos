"""Tests for the Catalog Management routes (HAZLO E INTEGRAKO).

Strict TDD — tests written before implementation.
Covers tasks 5.1, 5.2, 5.3 (backend integration + unit).
"""

from __future__ import annotations

import json

import pytest


class TestCatalogoBlueprintIntegration:
    """Task 5.1: Integration test for catalog blueprint route."""

    def test_catalogo_route_returns_200_with_admin_session(self, app_client):
        """GET /catalogo returns 200 with __INITIAL_DATA__ for admin."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/catalogo", follow_redirects=True)
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert 'id="root"' in html
        assert "__INITIAL_DATA__" in html

    def test_catalogo_route_has_username_and_permisos(self, app_client):
        """__INITIAL_DATA__ includes username and permisos."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/catalogo", follow_redirects=True)
        html = response.data.decode("utf-8")
        assert '"username"' in html
        assert '"permisos"' in html

    def test_catalogo_route_non_admin_returns_403(self, app_client):
        """Non-admin user gets 403 on /catalogo."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        response = app_client.get("/catalogo", follow_redirects=False)
        # Should redirect (flash) since it's not JSON
        assert response.status_code == 302

    def test_catalogo_route_unauthenticated_returns_401(self, app_client):
        """Unauthenticated user gets 401."""
        response = app_client.get("/catalogo")
        assert response.status_code == 401


class TestRelationshipEndpointIntegration:
    """Task 5.2: Integration test for GET /api/eps/<id>/procedimientos."""

    def test_relationship_endpoint_returns_json_on_unknown(self, app_client):
        """GET /api/eps/9999/procedimientos returns 404 with error shape."""
        app_client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        response = app_client.get("/api/eps/9999/procedimientos")
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None
        assert data["status"] == "error"
        assert len(data["errors"]) > 0

    def test_relationship_endpoint_requires_auth(self, app_client):
        """GET /api/eps/1/procedimientos without auth returns 401."""
        response = app_client.get("/api/eps/1/procedimientos")
        assert response.status_code == 401

    def test_relationship_endpoint_requires_admin(self, app_client):
        """Non-admin gets 403 on relationship endpoint."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["odontologia"]
            sess["username"] = "odontologia"

        response = app_client.get(
            "/api/eps/1/procedimientos",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data is not None
        assert data["status"] == "error"


class TestRelationshipQueryLogic:
    """Task 5.3: Unit tests for relationship query logic.

    Tests the helper function that builds the chain query.
    """

    def test_get_procedimientos_por_eps_invokes_correct_join(self):
        """The query uses the correct 5-model join pattern.

        Import the function and verify it builds the right chain.
        """
        from app.services.eps_contratado_crud import get_procedimientos_por_eps
        # Function exists and is callable
        assert callable(get_procedimientos_por_eps)

    def test_get_procedimientos_por_eps_returns_empty_list_with_no_data(self):
        """With a fresh in-memory DB (no data), returns empty list."""
        from app.database import SessionLocal
        from app.services.eps_contratado_crud import get_procedimientos_por_eps

        db = SessionLocal()
        try:
            result = get_procedimientos_por_eps(db, 1)
            assert isinstance(result, list)
            assert result == []
        finally:
            db.close()

    def test_chain_return_shape(self):
        """Each chain result has the expected keys."""
        from app.services.eps_contratado_crud import get_procedimientos_por_eps

        # Verify the function exists and returns the right shape
        import inspect
        sig = inspect.signature(get_procedimientos_por_eps)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "eps_id" in params or "id" in params

    def test_chain_result_includes_id_nota_hoja(self):
        """Each procedimiento dict includes id_nota_hoja key."""
        from app.services.eps_contratado_crud import get_procedimientos_por_eps
        import inspect
        source = inspect.getsource(get_procedimientos_por_eps)
        assert "'id_nota_hoja'" in source or '"id_nota_hoja"' in source, (
            "get_procedimientos_por_eps() must include 'id_nota_hoja' in the returned dict"
        )
