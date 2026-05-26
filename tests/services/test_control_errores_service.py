"""Tests for control_errores_service: update_error() permission logic.

Strict TDD: tests describe the NEW behavior (field-level permissions via
session["permisos"]) before production changes are made. These tests will
fail (RED) against the old code that uses session["ce_authenticated"].
"""

from unittest.mock import patch

import pytest
from flask import session

from app import create_app
from app.services.control_errores_service import update_error, add_error
from app.utils.errores_storage import crear_error, actualizar_error

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


class TestValidadorColumn:
    """Tests: validador column — storage, service composition, and backward compat.
    
    Strict TDD: tests written BEFORE production changes. These will fail (RED)
    until storage and service code is updated.
    """

    # ── Storage: crear_error ──────────────────────────────────────────

    def test_crear_error_stores_validador_key(self):
        """crear_error() MUST store validador key when validador param is passed."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-001",
                observacion="test obs",
                estado="S",
                responsable="Admin",
                validador="Juan Pérez",
            )

        assert error["validador"] == "Juan Pérez"
        mock_write.assert_called_once()

    def test_crear_error_validador_default_empty(self):
        """crear_error() MUST default validador to empty string."""
        with patch("app.utils.errores_storage._escribir_datos") as mock_write:
            error = crear_error(
                tipo_error="OTROS",
                factura="FAC-002",
                observacion="no validador",
                estado="S",
                responsable="Admin",
            )

        assert error["validador"] == ""
        mock_write.assert_called_once()

    # ── Service: add_error composition ────────────────────────────────

    def test_add_error_composes_validador_from_session(self):
        """add_error() MUST compose validador from session['primer_nombre'] + session['apellido_1']."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            session["primer_nombre"] = "Juan"
            session["apellido_1"] = "Pérez"

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "Admin",
                "observacion": "test",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == "Juan Pérez"

    def test_add_error_validador_ignores_client_payload(self):
        """add_error() MUST NOT use validador from client payload — session always wins."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            session["primer_nombre"] = "Maria"
            session["apellido_1"] = "Gomez"

            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-001",
                "responsable": "Admin",
                "validador": "hacker",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == "Maria Gomez"

    def test_add_error_validador_session_keys_missing(self):
        """add_error() MUST handle missing session keys gracefully (empty string fallback)."""
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            # No session keys set — should fall back to empty
            add_error({
                "tipo_error": "OTROS",
                "factura": "FAC-003",
                "responsable": "Admin",
            })

            mock_crear.assert_called_once()
            _call_kwargs = mock_crear.call_args.kwargs
            assert _call_kwargs.get("validador") == ""

    # ── Storage: actualizar_error does NOT touch validador ─────────────

    def test_actualizar_error_does_not_accept_validador(self):
        """actualizar_error() MUST NOT accept a validador parameter."""
        with patch("app.utils.errores_storage._leer_datos") as mock_read, \
             patch("app.utils.errores_storage._escribir_datos") as mock_write:

            mock_read.return_value = {"errores": [{"id": "test-1", "validador": "old"}]}

            result = actualizar_error(
                error_id="test-1",
                estado="N",
            )

            assert result is not None
            # validador should remain unchanged
            assert result.get("validador") == "old"
            # Verify TypeError if validador is passed
            import inspect
            sig = inspect.signature(actualizar_error)
            assert "validador" not in sig.parameters
