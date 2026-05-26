"""Integration tests: PUT /api/control-errores/<id> with session permissions.

Strict TDD: tests describe the NEW behavior. These will fail (RED) against
the old route decorator that requires "control_urgencias:write".
"""

from unittest.mock import patch

import pytest

from app.services.control_errores_service import (
    obtener_error,
    actualizar_error,
)


def _fake_error() -> dict:
    return {
        "id": "test-i1",
        "estado": "S",
        "tipo_error": "OTROS",
        "observacion": "paciente",
        "observacion_facturador": "",
        "factura": "FAC-001",
        "responsable": "",
    }


# Patch the storage layer for ALL tests in this module to avoid
# needing actual JSON files on disk.
@pytest.fixture(autouse=True)
def _mock_storage():
    with (
        patch("app.services.control_errores_service.obtener_error") as mock_get,
        patch("app.services.control_errores_service.actualizar_error") as mock_upd,
    ):
        mock_get.return_value = _fake_error()
        mock_upd.return_value = {
            "id": "test-i1",
            "estado": "R",
            "tipo_error": "X",
            "observacion_facturador": "ok",
        }
        yield


class TestPutEndpointPermissions:
    """Integration tests: PUT endpoint with different session states."""

    # ── Urgencias user (control_urgencias only) ──────────────────────

    def test_put_200_urgencias_allowed_estado(self, app_client):
        """Urgencias user PUT 'estado' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_200_urgencias_allowed_obs_facturador(self, app_client):
        """Urgencias user PUT 'observacion_facturador' → 200."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"observacion_facturador": "todo ok"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_put_403_urgencias_prohibited_field(self, app_client):
        """Urgencias user PUT 'tipo_error' → 403 with field name in body."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "tipo_error" in data["errors"][0]

    def test_put_403_urgencias_mixed_payload(self, app_client):
        """Urgencias user PUT allowed+prohibited → 403, no changes applied."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"estado": "R", "responsable": "Juan"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "responsable" in data["errors"][0]

    def test_put_403_urgencias_observacion(self, app_client):
        """Urgencias user PUT 'observacion' → 403."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias"]
            sess["username"] = "urgencias"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"observacion": "nuevo texto"},
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert "observacion" in data["errors"][0]

    # ── Auditor user (control_urgencias:write) ───────────────────────

    def test_put_200_auditor_all_fields(self, app_client):
        """Auditor user PUT 'tipo_error' → 200 (full write)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = [
                "control_urgencias",
                "control_urgencias:write",
                "facturas_abiertas",
                "facturas_abiertas:write",
            ]
            sess["username"] = "auditor"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X", "responsable": "Maria"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"
        data = resp.get_json()
        assert data["status"] == "success"

    # ── Admin user (*) ───────────────────────────────────────────────

    def test_put_200_admin_all_fields(self, app_client):
        """Admin user PUT any field → 200 (full write)."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X", "observacion": "cambio admin"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    # ── Regression: legacy flag ──────────────────────────────────────

    def test_put_403_no_permisos(self, app_client):
        """User with ce_authenticated but no permisos → 403 for prohibited fields."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            # No permisos key
            sess["username"] = "legacy"

        resp = app_client.put(
            "/api/control-errores/test-i1",
            json={"tipo_error": "X"},
        )
        assert resp.status_code == 403


class TestValidadorIntegration:
    """Integration tests: validador column behavior via POST/GET flow."""

    def test_post_creates_with_validador(self, app_client):
        """POST /api/control-errores with valid session MUST create entry with validador."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Juan"
            sess["apellido_1"] = "Pérez"

        resp = app_client.post("/api/control-errores", json={
            "tipo_error": "OTROS",
            "factura": "FAC-001",
            "responsable": "Admin",
            "observacion": "test validador",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["error"]["validador"] == "Juan Pérez"

    def test_post_validador_ignores_client_payload_integration(self, app_client):
        """POST with validador in payload MUST use session value, not payload."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Maria"
            sess["apellido_1"] = "Gomez"

        resp = app_client.post("/api/control-errores", json={
            "tipo_error": "OTROS",
            "factura": "FAC-002",
            "responsable": "Admin",
            "observacion": "test",
            "validador": "hacker",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["error"]["validador"] == "Maria Gomez"
        assert data["data"]["error"]["validador"] != "hacker"
