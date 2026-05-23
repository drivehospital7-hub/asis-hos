"""Tests for control_errores_service: update_error() permission logic.

Strict TDD: tests describe the NEW behavior (field-level permissions via
session["permisos"]) before production changes are made. These tests will
fail (RED) against the old code that uses session["ce_authenticated"].
"""

from unittest.mock import patch

import pytest
from flask import session

from app import create_app
from app.services.control_errores_service import update_error

# Application fixture for test request context
_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _fake_error() -> dict:
    return {
        "id": "test-1",
        "estado": "S",
        "tipo_error": "OTROS",
        "observacion": "paciente",
        "observacion_facturador": "",
        "factura": "FAC-001",
        "responsable": "",
    }


class TestUpdateErrorPermissions:
    """Unit tests for field-level write permissions in update_error()."""

    # ── Full write permission scenarios ──────────────────────────────

    def test_admin_star_can_update_any_field(self):
        """User with '*' (admin) MUST be able to update any field."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["*"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "Juan"}

            result = update_error("test-1", {"responsable": "Juan", "tipo_error": "X"})

        assert result["status"] == "success"
        assert result["data"]["error"]["id"] == "test-1"
        mock_upd.assert_called_once()

    def test_write_perm_can_update_any_field(self):
        """User with 'control_urgencias:write' MUST be able to update any field."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["urgencias", "control_urgencias:write"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "responsable": "Maria"}

            result = update_error("test-1", {"responsable": "Maria"})

        assert result["status"] == "success"
        assert result["data"]["error"]["id"] == "test-1"
        mock_upd.assert_called_once()

    # ── Partial write (control_urgencias) — allowed fields ───────────

    def test_limited_allowed_estado(self):
        """User with 'control_urgencias' MUST be allowed to update 'estado'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "estado": "R"}

            result = update_error("test-1", {"estado": "R"})

        assert result["status"] == "success"
        assert result["data"]["error"]["estado"] == "R"
        mock_upd.assert_called_once()

    def test_limited_allowed_observacion_facturador(self):
        """User with 'control_urgencias' MUST be allowed to update 'observacion_facturador'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "observacion_facturador": "Ok"}

            result = update_error("test-1", {"observacion_facturador": "Ok"})

        assert result["status"] == "success"
        assert result["data"]["error"]["observacion_facturador"] == "Ok"
        mock_upd.assert_called_once()

    # ── Partial write — prohibited fields ────────────────────────────

    def test_limited_rejects_prohibited_field(self):
        """User with 'control_urgencias' MUST get 403 for 'tipo_error'."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"tipo_error": "X"})

        # Expect a tuple (dict, 403)
        assert isinstance(result, tuple)
        assert result[1] == 403
        assert result[0]["status"] == "error"
        assert "tipo_error" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_mixed_payload(self):
        """User with 'control_urgencias' MUST reject payload with mixed allowed+prohibited."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"estado": "R", "responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "responsable" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    def test_limited_rejects_observacion(self):
        """User with 'control_urgencias' MUST NOT edit 'observacion' directly."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["ce_authenticated"] = True
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"observacion": "nuevo texto"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "observacion" in result[0]["errors"][0]
        mock_upd.assert_not_called()

    # ── Regression: legacy flag should not affect outcome ────────────

    def test_legacy_flag_ignored_when_has_write_perm(self):
        """ce_authenticated=False MUST NOT block when permisos has :write."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["ce_authenticated"] = False
            session["permisos"] = ["control_urgencias:write"]
            mock_get.return_value = _fake_error()
            mock_upd.return_value = {"id": "test-1", "tipo_error": "X"}

            result = update_error("test-1", {"tipo_error": "X"})

        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_no_permisos_restricts_fields(self):
        """No permisos in session MUST restrict to estado/observacion_facturador."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["ce_authenticated"] = True
            # No session["permisos"] set — key doesn't exist
            mock_get.return_value = _fake_error()

            result = update_error("test-1", {"responsable": "Juan"})

        assert isinstance(result, tuple)
        assert result[1] == 403
        assert "responsable" in result[0]["errors"][0]
        mock_upd.assert_not_called()
