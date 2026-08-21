"""Strict TDD RED tests for bearer-aware integration auth (Phase 2, task 2.1).

The integration endpoint must authenticate session-less requests via a bearer
token tied to a DB validator. Missing/malformed/revoked/expired tokens MUST
return a 401 envelope and MUST NOT persist any record.
"""

from unittest.mock import patch

import pytest


class TestIntegrationAuth:
    """POST /api/integration/control-novedades bearer auth behavior."""

    def _post(self, app_client, headers=None, json_body=None):
        return app_client.post(
            "/api/integration/control-novedades",
            headers=headers or {},
            json=json_body or {},
        )

    def test_missing_token_returns_401(self, app_client):
        """No Authorization header → 401 envelope, nothing persisted."""
        resp = self._post(app_client)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["data"] == {}
        assert len(data["errors"]) > 0

    def test_malformed_token_returns_401(self, app_client):
        """Non-bearer Authorization scheme → 401."""
        resp = self._post(app_client, headers={"Authorization": "Basic abc"})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0

    def test_unknown_token_returns_401(self, app_client):
        """Bearer token that resolves to no user → 401."""
        with patch("app.utils.token_store.get_user_for_token", return_value=None):
            resp = self._post(
                app_client,
                headers={"Authorization": "Bearer unknown-token"},
            )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0

    def test_revoked_token_returns_401(self, app_client):
        """A revoked token must resolve to None → 401."""
        with patch("app.utils.token_store.get_user_for_token", return_value=None):
            resp = self._post(
                app_client,
                headers={"Authorization": "Bearer revoked-token"},
            )
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"

    def test_expired_token_returns_401(self, app_client):
        """An expired token must resolve to None → 401."""
        with patch("app.utils.token_store.get_user_for_token", return_value=None):
            resp = self._post(
                app_client,
                headers={"Authorization": "Bearer expired-token"},
            )
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"

    def test_valid_token_authenticates(self, app_client):
        """A valid bearer token authenticates and reaches the service."""
        fake_user = {
            "id": 1,
            "username": "ana",
            "rol": "validador",
            "permisos": ["control_urgencias", "control_urgencias:write"],
            "primer_nombre": "Ana",
            "segundo_nombre": "",
            "apellido_1": "Valdez",
            "apellido_2": "",
        }
        with (
            patch("app.utils.token_store.get_user_for_token", return_value=fake_user),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = self._post(
                app_client,
                headers={"Authorization": "Bearer valid-token"},
                json_body={"factura": "FAC-1"},
            )
        assert resp.status_code == 201
        assert resp.get_json()["status"] == "success"
        # The service received the synthetic session derived from the token
        assert mock_submit.called


class TestBrowserSessionRegression:
    """Task 2.3: bearer handling MUST NOT alter browser session semantics."""

    def test_session_endpoint_unchanged_with_bearer_handling(self, app_client):
        """A session-authenticated browser POST still works as before."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["primer_nombre"] = "Maria"
            sess["apellido_1"] = "Gomez"
            sess["username"] = "maria"

        with patch("app.services.control_errores_service.crear_error") as mock_crear:
            mock_crear.return_value = {
                "id": "x", "created_by": "maria", "validador": "Maria Gomez",
            }
            resp = app_client.post("/api/control-errores", json={
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "LORENY ESPAÑA",
                "observacion": "test",
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert mock_crear.call_args.kwargs.get("created_by") == "maria"

    def test_non_integration_public_endpoint_still_public(self, app_client):
        """Public endpoints (e.g. auth.api_status) remain accessible without session."""
        resp = app_client.get("/auth/api/status")
        assert resp.status_code == 200
