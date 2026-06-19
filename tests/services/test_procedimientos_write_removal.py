"""Tests para eliminación de endpoints de escritura de procedimientos.

Cubre: Task 2.1 (eliminar procedimientos_crud.py) y Task 2.2 (410 Gone en routes).
"""

from __future__ import annotations

import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ─── Task 2.1: procedimientos_crud.py eliminado ────────────────────────


class TestProcedimientosCrudDeleted:
    """Verifica que procedimientos_crud.py fue eliminado."""

    def test_file_does_not_exist(self):
        """El archivo procedimientos_crud.py DEBE no existir."""
        crud_path = (
            Path(__file__).parent.parent.parent
            / "app" / "services" / "procedimientos_crud.py"
        )
        assert not crud_path.exists(), (
            f"procedimientos_crud.py NO debe existir, pero se encontró en {crud_path}"
        )

    def test_cannot_import_procedimientos_crud(self):
        """Importar procedimientos_crud DEBE lanzar ModuleNotFoundError."""
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("app.services.procedimientos_crud")


# ─── Task 2.2: Routes retornan 410 Gone ────────────────────────────────


class TestProcedimientosWriteRoutesGone:
    """Verifica que POST/PUT/DELETE en /procedimientos retornan 410 Gone."""

    GONE_MESSAGE = "Este endpoint ya no está disponible"

    def test_post_returns_410_gone_without_auth(self, app_client):
        """POST /procedimientos DEBE retornar 410 sin autenticación."""
        response = app_client.post("/procedimientos", json={
            "eps": "EMSSANAR",
            "codigo_cups": "890201",
            "tarifa": 45000,
        })
        assert response.status_code == 410, (
            f"Esperado 410, recibido {response.status_code}"
        )
        data = response.get_json()
        assert data["status"] == "error"
        assert self.GONE_MESSAGE in data["errors"][0]

    def test_put_returns_410_gone_without_auth(self, app_client):
        """PUT /procedimientos/<id> DEBE retornar 410 sin autenticación."""
        response = app_client.put("/procedimientos/1", json={
            "eps": "EMSSANAR",
            "codigo_cups": "890201",
            "tarifa": 50000,
        })
        assert response.status_code == 410, (
            f"Esperado 410, recibido {response.status_code}"
        )
        data = response.get_json()
        assert data["status"] == "error"
        assert self.GONE_MESSAGE in data["errors"][0]

    def test_delete_returns_410_gone_without_auth(self, app_client):
        """DELETE /procedimientos/<id> DEBE retornar 410 sin autenticación."""
        response = app_client.delete("/procedimientos/1")
        assert response.status_code == 410, (
            f"Esperado 410, recibido {response.status_code}"
        )
        data = response.get_json()
        assert data["status"] == "error"
        assert self.GONE_MESSAGE in data["errors"][0]

    def test_post_returns_410_even_with_admin_session(self, app_client):
        """Incluso con sesión admin, POST retorna 410."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "testadmin"
            sess["permisos"] = ["*"]
        response = app_client.post("/procedimientos", json={"eps": "TEST"})
        assert response.status_code == 410

    def test_get_eps_endpoint_requires_admin_session(self, app_client):
        """GET /procedimientos/eps sin sesión DEBE retornar 401."""
        response = app_client.get("/procedimientos/eps")
        assert response.status_code == 401, (
            f"GET /procedimientos/eps sin auth debería 401. Status: {response.status_code}"
        )

    def test_get_eps_route_is_registered(self, app_client):
        """La ruta GET /procedimientos/eps DEBE existir en el mapa de URLs."""
        from flask import current_app
        with app_client.application.app_context():
            adapter = current_app.url_map.bind("")
            # Debe resolver correctamente
            rule = adapter.match("/procedimientos/eps", method="GET")
            assert rule is not None
            assert rule[0] == "procedimientos.list_eps"

    def test_get_procedimientos_requires_admin_session(self, app_client):
        """GET /procedimientos sin sesión DEBE retornar 401."""
        response = app_client.get("/procedimientos?eps=EMSSANAR")
        assert response.status_code == 401, (
            f"GET /procedimientos sin auth debería 401. Status: {response.status_code}"
        )

    def test_get_procedimientos_route_is_registered(self, app_client):
        """GET /procedimientos DEBE estar registrado."""
        from flask import current_app
        with app_client.application.app_context():
            adapter = current_app.url_map.bind("")
            rule = adapter.match("/procedimientos", method="GET")
            assert rule is not None
            assert rule[0] == "procedimientos.list_procedimientos"

    def test_response_format_matches_convention(self, app_client):
        """La respuesta 410 DEBE seguir el formato del proyecto."""
        response = app_client.post("/procedimientos", json={"eps": "TEST"})
        data = response.get_json()
        assert "status" in data
        assert "data" in data
        assert "errors" in data
        assert data["status"] == "error"
        assert data["data"] == {}
        assert isinstance(data["errors"], list)
        assert len(data["errors"]) >= 1
