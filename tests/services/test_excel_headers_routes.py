"""Integration tests for app/routes/excel_headers.py POST route.

Covers the fallback paths in the POST endpoint:
- No file uploaded → JSON error (not HTML)
- Invalid file extension → JSON error
"""

from __future__ import annotations

from io import BytesIO

from app import PUBLIC_ENDPOINTS


class TestExcelHeadersRoutePost:
    """Integration tests for /odontologia/ POST endpoint."""

    def _authenticate(self, app_client) -> None:
        """Establece sesión autenticada con permiso odontologia."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"
            sess["permisos"] = ["odontologia"]

    def test_post_no_file_returns_json_error(self, app_client) -> None:
        """POST without file returns JSON error, not HTML."""
        self._authenticate(app_client)

        response = app_client.post(
            "/odontologia/",
            data={},
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data is not None
        assert data["status"] == "error"
        assert isinstance(data["errors"], list)
        assert any("seleccionar" in e.lower() or "archivo" in e.lower() for e in data["errors"])

    def test_post_invalid_extension_returns_json_error(self, app_client) -> None:
        """POST with invalid file extension returns JSON error."""
        self._authenticate(app_client)

        response = app_client.post(
            "/odontologia/",
            data={
                "file_upload": (BytesIO(b"test data"), "test.txt"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data is not None
        assert data["status"] == "error"
        assert isinstance(data["errors"], list)
        assert any("formato" in e.lower() or "permitido" in e.lower() for e in data["errors"])


class TestPublicEndpoints:
    """PUBLIC_ENDPOINTS no longer contains legacy auth endpoint."""

    def test_login_legacy_not_in_public_endpoints(self) -> None:
        """auth.login_legacy is not in PUBLIC_ENDPOINTS."""
        assert "auth.login_legacy" not in PUBLIC_ENDPOINTS

    def test_other_endpoints_still_present(self) -> None:
        """Required endpoints remain in PUBLIC_ENDPOINTS."""
        required = {"auth.api_login", "auth.api_logout", "auth.api_status",
                     "auth.login", "auth.unauthorized_react", "static"}
        for endpoint in required:
            assert endpoint in PUBLIC_ENDPOINTS, f"{endpoint} should still be public"
