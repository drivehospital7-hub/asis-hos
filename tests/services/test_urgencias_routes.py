"""Integration tests for app/routes/urgencias.py POST route.

Covers the uncovered paths in the POST endpoint:
- No file uploaded → HTML render (not JSON)
- Invalid file extension → error template context
- Semaphore timeout → 503
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest


class TestUrgenciasRoutePost:
    """Integration tests for /urgencias/ POST endpoint."""

    def _authenticate(self, app_client) -> None:
        """Establece sesión autenticada con permiso urgencias."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"
            sess["permisos"] = ["urgencias"]

    def test_post_no_file_returns_html(self, app_client) -> None:
        """POST without file returns HTML template (not JSON)."""
        self._authenticate(app_client)

        response = app_client.post(
            "/urgencias/",
            data={},
            content_type="multipart/form-data",
        )

        # With no file, the route renders HTML with error context
        assert response.status_code == 200
        assert "text/html" in response.content_type, (
            f"Should return HTML, got {response.content_type}"
        )
        # The rendered template should mention the upload error
        html = response.data.decode("utf-8", errors="replace").lower()
        assert "seleccionar" in html or "archivo" in html, (
            f"HTML should mention file selection error: {html[:500]}"
        )

    def test_post_invalid_extension_returns_html(self, app_client) -> None:
        """POST with invalid file extension returns HTML error context."""
        self._authenticate(app_client)

        response = app_client.post(
            "/urgencias/",
            data={
                "file_upload": (BytesIO(b"test data"), "test.txt"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        assert "text/html" in response.content_type, (
            f"Should return HTML, got {response.content_type}"
        )
        html = response.data.decode("utf-8", errors="replace").lower()
        assert "formato" in html or "permitido" in html, (
            f"HTML should mention invalid format: {html[:500]}"
        )

    def test_post_semaphore_timeout_returns_503(self, app_client) -> None:
        """POST returns 503 when semaphore is exhausted."""
        self._authenticate(app_client)
        app_client.application.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

        with patch(
            "app.services.exporter.acquire_semaphore"
        ) as mock_acquire:
            mock_acquire.return_value = False

            response = app_client.post(
                "/urgencias/",
                data={
                    "file_upload": (BytesIO(b"test"), "test.xlsx"),
                },
                content_type="multipart/form-data",
            )

            assert response.status_code == 503, (
                f"Expected 503, got {response.status_code}: {response.data[:500]}"
            )
            data = response.get_json()
            assert data is not None
            assert data["status"] == "error"
            assert any(
                "Servidor ocupado" in e for e in data.get("errors", [])
            ), f"503 should mention 'Servidor ocupado': {data}"
