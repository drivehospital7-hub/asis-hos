"""Integration tests for app/routes/procesar.py POST route.

Covers the unified endpoint behavior:
- No file uploaded → JSON error (not HTML)
- Invalid file extension → JSON error
- Semaphore timeout → 503
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

import pytest


class TestProcesarRoutePost:
    """Integration tests for /procesar/ POST endpoint."""

    def _authenticate(self, app_client, permisos: list[str] | None = None) -> None:
        """Establece sesión autenticada."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"
            sess["permisos"] = permisos or ["procesar"]

    def test_post_no_file_returns_json_error(self, app_client) -> None:
        """POST without file returns JSON error, not HTML."""
        self._authenticate(app_client)

        response = app_client.post(
            "/procesar/",
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
            "/procesar/",
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

    def test_post_semaphore_timeout_returns_503(self, app_client) -> None:
        """POST returns 503 when semaphore is exhausted."""
        self._authenticate(app_client)
        app_client.application.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

        with patch(
            "app.services.exporter.acquire_semaphore"
        ) as mock_acquire:
            mock_acquire.return_value = False

            response = app_client.post(
                "/procesar/",
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
