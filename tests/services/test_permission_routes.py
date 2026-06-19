"""Integration tests for permission decorators on route files.

Covers Phase 2 changes: procesar, cronogramas, derechos, procedimientos,
notas_api, and import_csv decorator updates.
"""

from __future__ import annotations

from unittest.mock import patch


# =============================================================================
# Permission helper
# =============================================================================


def _login(app_client, permisos: list[str] | None = None) -> None:
    """Set up an authenticated session with given permisos."""
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["username"] = "testuser"
        sess["permisos"] = permisos or ["*"]


# =============================================================================
# Tests: /procesar — @permiso_requerido("procesar")
# =============================================================================


class TestProcesarPermission:
    """GET /procesar/ requires 'procesar' permission."""

    def test_procesar_with_permiso(self, app_client):
        """User with 'procesar' can access GET /procesar/."""
        _login(app_client, ["procesar"])
        resp = app_client.get("/procesar/")
        assert resp.status_code == 200

    def test_procesar_without_permiso(self, app_client):
        """User without 'procesar' gets XHR 403."""
        _login(app_client, ["control_urgencias"])
        resp = app_client.get(
            "/procesar/",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data is not None
        assert data["status"] == "error"

    def test_procesar_admin_bypass(self, app_client):
        """Admin (*) can access GET /procesar/."""
        _login(app_client, ["*"])
        resp = app_client.get("/procesar/")
        assert resp.status_code == 200

    def test_procesar_write_grants_access(self, app_client):
        """User with 'procesar:write' can access (expanded to 'procesar')."""
        _login(app_client, ["procesar:write"])
        resp = app_client.get("/procesar/")
        assert resp.status_code == 200


# =============================================================================
# Tests: /cronograma-bacteriologas — @permiso_requerido("cronograma_bacteriologas")
# =============================================================================


class TestCronogramaBacteriologasPermission:
    """Access requires 'cronograma_bacteriologas' permission."""

    def test_with_permiso(self, app_client):
        """User with 'cronograma_bacteriologas' can access."""
        _login(app_client, ["cronograma_bacteriologas"])
        resp = app_client.get("/cronograma-bacteriologas/")
        assert resp.status_code == 200

    def test_without_permiso(self, app_client):
        """User without permiso gets XHR 403."""
        _login(app_client, ["procesar"])
        resp = app_client.get(
            "/cronograma-bacteriologas/api",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_admin_bypass(self, app_client):
        """Admin (*) can access."""
        _login(app_client, ["*"])
        resp = app_client.get("/cronograma-bacteriologas/")
        assert resp.status_code == 200


# =============================================================================
# Tests: /cronograma-urgencias — @permiso_requerido("cronograma_urgencias")
# =============================================================================


class TestCronogramaUrgenciasPermission:
    """Access requires 'cronograma_urgencias' permission."""

    def test_with_permiso(self, app_client):
        """User with 'cronograma_urgencias' can access."""
        _login(app_client, ["cronograma_urgencias"])
        resp = app_client.get("/cronograma-urgencias/")
        assert resp.status_code == 200

    def test_without_permiso(self, app_client):
        """User without permiso gets XHR 403 on API."""
        _login(app_client, ["procesar"])
        resp = app_client.get(
            "/cronograma-urgencias/api?mes=1&anio=2025",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_admin_bypass(self, app_client):
        """Admin (*) can access."""
        _login(app_client, ["*"])
        resp = app_client.get("/cronograma-urgencias/")
        assert resp.status_code == 200


# =============================================================================
# Tests: /derechos — @permiso_requerido("derechos") added
# =============================================================================


class TestDerechosPermission:
    """Procesar and texto endpoints require 'derechos' permission."""

    def test_procesar_with_permiso(self, app_client):
        """User with 'derechos' can POST /derechos/procesar."""
        _login(app_client, ["derechos"])
        resp = app_client.post(
            "/derechos/procesar",
            json={"ruta": "/nonexistent/path"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        # 400 because path doesn't exist — but permiso passed
        assert resp.status_code in (200, 400)

    def test_procesar_without_permiso(self, app_client):
        """User without 'derechos' gets 403."""
        _login(app_client, ["procesar"])
        resp = app_client.post(
            "/derechos/procesar",
            json={"ruta": "/test"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_texto_without_permiso(self, app_client):
        """User without 'derechos' gets 403 on GET /derechos/texto."""
        _login(app_client, ["procesar"])
        resp = app_client.get(
            "/derechos/texto",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403


# =============================================================================
# Tests: /api/eps (notas_api) — @admin_requerido added
# =============================================================================


class TestNotasApiPermission:
    """Previously unprotected endpoints now require admin."""

    def test_list_eps_with_admin(self, app_client):
        """Admin can access GET /api/eps."""
        _login(app_client, ["*"])
        resp = app_client.get(
            "/api/eps",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 200

    def test_list_eps_without_admin(self, app_client):
        """Non-admin gets 403 on GET /api/eps."""
        _login(app_client, ["procesar"])
        resp = app_client.get(
            "/api/eps",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_procedimientos_with_admin(self, app_client):
        """Admin can access GET /api/procedimientos."""
        _login(app_client, ["*"])
        resp = app_client.get(
            "/api/procedimientos",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 200

    def test_notas_hoja_without_admin(self, app_client):
        """Non-admin gets 403 on GET /api/notas-hoja."""
        _login(app_client, ["procesar"])
        resp = app_client.get(
            "/api/notas-hoja",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_eps_procedimientos_still_protected(self, app_client):
        """eps/<id>/procedimientos was already protected — still works."""
        _login(app_client, ["*"])
        resp = app_client.get("/api/eps/9999/procedimientos")
        assert resp.status_code == 404  # EPS 9999 doesn't exist, but permiso passed


# =============================================================================
# Tests: /api/import (import_csv) — @admin_requerido added
# =============================================================================


class TestImportCsvPermission:
    """Previously unprotected endpoints now require admin."""

    def test_import_eps_without_admin(self, app_client):
        """Non-admin gets 403 on POST /api/import/eps."""
        _login(app_client, ["procesar"])
        resp = app_client.post(
            "/api/import/eps",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403

    def test_import_eps_with_admin(self, app_client):
        """Admin can POST /api/import/eps (will 400 — no file)."""
        _login(app_client, ["*"])
        resp = app_client.post(
            "/api/import/eps",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        # 400 because no file — but permiso passed
        assert resp.status_code == 400
