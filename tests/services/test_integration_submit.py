"""Strict TDD RED tests: end-to-end integration submit + HTTPS/config (Phase 4).

Task 4.1: A POST with a valid bearer token persists a record whose validator
comes from the token (not payload). HTTP-on-LAN surfaces an HTTPS warning.
Task 4.2: non-admin lifecycle operations are denied.
"""

import importlib
import os
from unittest.mock import patch

import pytest

from app.utils import token_store


def _fake_validator_user(username="ana", permisos=None):
    return {
        "id": 1,
        "username": username,
        "rol": "validador",
        "permisos": permisos if permisos is not None else ["control_urgencias", "control_urgencias:write"],
        "primer_nombre": "Ana",
        "segundo_nombre": "",
        "apellido_1": "Valdez",
        "apellido_2": "",
    }


class TestSubmitPermission:
    """D6: control_novedades_submit MUST enforce control_urgencias:write.

    auth.py is immutable (out of scope) and permiso_requerido only reads the
    browser ``session`` — never ``flask.g``. The bearer submit endpoint has no
    browser session, so the write permission is enforced MANUALLY in-route from
    ``g.bearer_user`` (the validator identity resolved by _handle_bearer_auth).
    A token user lacking the write permission → 403 and submit never runs; a
    user with it (or admin '*') → 201.
    """

    def test_token_user_without_write_permission_denied(self, app_client):
        """Token owner without control_urgencias:write → 403, submit not called."""
        with (
            patch(
                "app.utils.token_store.get_user_for_token",
                return_value=_fake_validator_user(
                    permisos=["control_urgencias"],  # no :write
                ),
            ),
            patch("app.routes.integration.submit") as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer no-write-token"},
                json={"factura": "FEV1", "responsable": "X"},
            )

        assert resp.status_code == 403
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["errors"] == ["Permiso denegado"]
        mock_submit.assert_not_called()

    def test_token_user_with_write_permission_succeeds(self, app_client):
        """Token owner with control_urgencias:write → 201 and submit called."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        with (
            patch(
                "app.utils.token_store.get_user_for_token",
                return_value=_fake_validator_user(),
            ),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer write-token"},
                json={"factura": "FEV2", "responsable": "X"},
            )

        assert resp.status_code == 201
        assert resp.get_json()["status"] == "success"
        assert mock_submit.called

    def test_admin_token_user_succeeds(self, app_client):
        """Admin token owner (permiso '*') → 201 (admin bypasses permission check)."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        with (
            patch(
                "app.utils.token_store.get_user_for_token",
                return_value=_fake_validator_user(permisos=["*"]),
            ),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer admin-token"},
                json={"factura": "FEV3", "responsable": "X"},
            )

        assert resp.status_code == 201
        assert resp.get_json()["status"] == "success"
        assert mock_submit.called


class TestEndToEndSubmit:
    def test_valid_token_persists_record_with_validator_from_token(self, app_client):
        """Full POST flow: token auth + forced category + validator from token."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer valid-token"},
                json={
                    "factura": "FEV123",
                    "observacion": "falta soporte",
                    "responsable": "LORENY ESPAÑA",
                    "tipo_error": "Factura Abierta",  # MUST be forced
                },
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        # The record's validator is the token owner, not any payload field
        assert data["data"]["error"]["validador"] == "Ana Valdez"
        # submit was called with the synthetic session derived from the token
        assert mock_submit.called
        synth_session = mock_submit.call_args.args[1]
        assert synth_session["username"] == "ana"
        assert synth_session["ce_authenticated"] is True
        assert synth_session["primer_nombre"] == "Ana"
        assert synth_session["apellido_1"] == "Valdez"

    def test_batch_payload_forwarded_to_submit(self, app_client):
        """A list payload {'novedades': [...]} is forwarded to submit unchanged."""
        batch = {
            "novedades": [
                {"factura": "FEV1", "observacion": "obs 1", "responsable": "X"},
                {"factura": "FEV2", "observacion": "obs 2", "responsable": "Y"},
            ]
        }
        batch_envelope = {
            "status": "success",
            "data": {"procesadas": 2, "rechazadas": 0, "resultados": []},
            "errors": [],
        }
        with (
            patch(
                "app.utils.token_store.get_user_for_token",
                return_value=_fake_validator_user(),
            ),
            patch(
                "app.routes.integration.submit",
                return_value=(batch_envelope, 200),
            ) as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer batch-token"},
                json=batch,
            )

        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"
        assert resp.get_json()["data"]["procesadas"] == 2
        assert mock_submit.called
        assert mock_submit.call_args.args[0] == batch
        assert mock_submit.call_args.args[1]["username"] == "ana"

    def test_unauthorized_token_nothing_persisted(self, app_client):
        """Unknown token → 401 and submit never called."""
        with (
            patch("app.utils.token_store.get_user_for_token", return_value=None),
            patch("app.routes.integration.submit") as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer nope"},
                json={"factura": "X", "responsable": "Y"},
            )

        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"
        mock_submit.assert_not_called()


class TestNoSessionCookie:
    """R3-1: a bearer integration request MUST NOT mint a persisted session
    cookie (the endpoint is session-less; the synthetic identity lives only in
    ``flask.g`` for the duration of the request)."""

    def test_valid_bearer_request_sets_no_session_cookie(self, app_client):
        """A valid bearer submit response MUST NOT carry a Set-Cookie header and
        must not leave an authenticated session behind."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer no-cookie-token"},
                json={"factura": "FEV1", "responsable": "X"},
            )

        assert resp.status_code == 201
        # The session-less endpoint must NOT emit an authenticated session cookie
        assert "Set-Cookie" not in resp.headers
        # submit still received the synthetic identity built from the bearer user
        assert mock_submit.called
        synth_session = mock_submit.call_args.args[1]
        assert synth_session["ce_authenticated"] is True
        assert synth_session["username"] == "ana"

    def test_no_authenticated_session_leaks_after_bearer_request(self, app_client):
        """After a valid bearer submit, a fresh request without a session cookie
        to a protected endpoint must still be rejected (no session persisted)."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ),
        ):
            app_client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer no-cookie-token-2"},
                json={"factura": "FEV2", "responsable": "X"},
            )

        # A follow-up protected API request without a session cookie must be 401:
        # the bearer request must NOT have leaked an authenticated session.
        resp = app_client.get(
            "/api/control-errores",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["status"] == "error"


class TestHttpsEnforcement:
    """Verify the temporary LAN HTTP exception and the HTTPS enforcement mode."""

    @staticmethod
    def _client_for_requirement(monkeypatch, required):
        """Build a non-TESTING client after applying the environment setting."""
        import app.constants.base as base_module
        import app.routes.integration as integration_module
        from app import create_app

        if required is None:
            monkeypatch.delenv("INTEGRATION_HTTPS_REQUIRED", raising=False)
        else:
            monkeypatch.setenv("INTEGRATION_HTTPS_REQUIRED", required)
        importlib.reload(base_module)
        importlib.reload(integration_module)

        app = create_app()
        app.config["TESTING"] = False
        return app.test_client()

    @pytest.fixture(autouse=True)
    def _restore_https_requirement(self, monkeypatch):
        original = os.environ.get("INTEGRATION_HTTPS_REQUIRED")
        yield
        if original is None:
            monkeypatch.delenv("INTEGRATION_HTTPS_REQUIRED", raising=False)
        else:
            monkeypatch.setenv("INTEGRATION_HTTPS_REQUIRED", original)
        import app.constants.base as base_module
        import app.routes.integration as integration_module
        importlib.reload(base_module)
        importlib.reload(integration_module)

    @pytest.mark.parametrize("required", [None, "false"], ids=["default", "false"])
    def test_non_https_submit_allowed_when_https_not_required(self, monkeypatch, required):
        """HTTP is allowed when the setting is unset or explicitly false."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        client = self._client_for_requirement(monkeypatch, required)
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer http-token"},
                json={
                    "factura": "FEV-H",
                    "observacion": "falta soporte",
                    "responsable": "X",
                },
                environ_overrides={"wsgi.url_scheme": "http"},
            )

        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json()["status"] == "success"
        assert mock_submit.called

    def test_non_https_submit_rejected_when_https_required(self, monkeypatch):
        """HTTP is rejected with a clear JSON error when TLS is required."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        client = self._client_for_requirement(monkeypatch, "true")
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer http-token"},
                json={
                    "factura": "FEV-H",
                    "observacion": "falta soporte",
                    "responsable": "X",
                },
                environ_overrides={"wsgi.url_scheme": "http"},
            )

        assert resp.status_code == 403
        data = resp.get_json()
        assert data["status"] == "error"
        assert any("HTTPS" in e for e in data["errors"])
        mock_submit.assert_not_called()

    def test_https_submit_allowed_when_https_required(self, monkeypatch):
        """HTTPS remains allowed when TLS enforcement is enabled."""
        persisted = {"id": "rec-1", "validador": "Ana Valdez", "created_by": "ana"}
        client = self._client_for_requirement(monkeypatch, "true")
        with (
            patch("app.utils.token_store.get_user_for_token",
                  return_value=_fake_validator_user()),
            patch(
                "app.routes.integration.submit",
                return_value=({"status": "success", "data": {"error": persisted}, "errors": []}, 201),
            ) as mock_submit,
        ):
            resp = client.post(
                "/api/integration/control-novedades",
                headers={"Authorization": "Bearer https-token"},
                json={
                    "factura": "FEV-S",
                    "observacion": "falta soporte",
                    "responsable": "X",
                },
                environ_overrides={"wsgi.url_scheme": "https"},
            )

        assert resp.status_code == 201, resp.get_json()
        assert resp.get_json()["status"] == "success"
        assert mock_submit.called


class TestNonAdminLifecycleDenied:
    def test_non_admin_cannot_list_tokens(self, app_client):
        """Non-admin session listing tokens → 403, no tokens exposed."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["username"] = "val1"

        resp = app_client.get(
            "/api/integration/tokens",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["status"] == "error"

    def test_non_admin_cannot_issue_token(self, app_client):
        """Non-admin session issuing a token → 403, no token created."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["username"] = "val1"

        with patch("app.utils.token_store.issue_token") as mock_issue:
            resp = app_client.post(
                "/api/integration/tokens",
                json={"username": "ana"},
            )

        assert resp.status_code == 403
        mock_issue.assert_not_called()

    def test_admin_can_issue_token(self, app_client):
        """Admin session issuing a token → plaintext returned once."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        with patch(
            "app.utils.token_store.issue_token",
            return_value=("raw-secret", {"id": 1, "username": "ana"}),
        ):
            resp = app_client.post(
                "/api/integration/tokens",
                json={"username": "ana"},
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["token"] == "raw-secret"

    def test_admin_can_issue_permanent_token(self, app_client):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        with patch(
            "app.utils.token_store.issue_token",
            return_value=("raw-secret", {"id": 1, "username": "ana", "expires_at": None}),
        ) as mock_issue:
            resp = app_client.post(
                "/api/integration/tokens",
                json={"username": "ana", "permanent": True},
            )

        assert resp.status_code == 201
        mock_issue.assert_called_once_with("ana", permanent=True)

    def test_issue_token_rejects_non_boolean_permanent(self, app_client):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        with patch("app.utils.token_store.issue_token") as mock_issue:
            resp = app_client.post(
                "/api/integration/tokens",
                json={"username": "ana", "permanent": "true"},
            )

        assert resp.status_code == 400
        assert resp.get_json() == {
            "status": "error",
            "data": {},
            "errors": ["Campo inválido: permanent debe ser booleano"],
        }
        mock_issue.assert_not_called()

    def test_admin_can_rotate_token(self, app_client):
        """Admin session rotating a token → new plaintext returned once."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        with patch(
            "app.utils.token_store.rotate_token",
            return_value=("new-secret", {"id": 2, "username": "ana"}),
        ):
            resp = app_client.post("/api/integration/tokens/1/rotate")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["token"] == "new-secret"

    def test_admin_can_revoke_token(self, app_client):
        """Admin session revoking a token → revoked confirmed."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["*"]
            sess["username"] = "admin"

        with patch("app.utils.token_store.revoke_token", return_value=True):
            resp = app_client.post("/api/integration/tokens/1/revoke")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["data"]["revoked"] is True

    def test_non_admin_cannot_rotate_token(self, app_client):
        """Non-admin rotation → 403, no rotation performed."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["username"] = "val1"

        with patch("app.utils.token_store.rotate_token") as mock_rotate:
            resp = app_client.post(
                "/api/integration/tokens/1/rotate",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

        assert resp.status_code == 403
        mock_rotate.assert_not_called()
