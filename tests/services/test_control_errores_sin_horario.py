"""T5 — Guard: reject Factura Abierta with Sin horario (defense-in-depth).

Strict TDD AC1-AC4. Service-level guard in add_error().

AC1: Factura Abierta + Sin horario -> error, success False, no crear_error call
AC2: Factura Abierta + real name -> success
AC3: Otros + Sin horario -> success (only Factura Abierta blocked)
AC4: Sin Egreso still routed -> not conflated (Factura Abierta + Sin Egreso succeeds)
"""

from unittest.mock import patch

import pytest

from app import create_app
from app.services.control_errores_service import add_error

_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _sess():
    return {
        "username": "val1",
        "rol": "validador",
        "permisos": ["control_urgencias:write"],
        "primer_nombre": "Maria",
        "apellido_1": "Gomez",
    }


class TestSinHorarioGuard:
    """T5 AC1-AC4."""

    def test_ac1_reject_factura_abierta_sin_horario_no_create(self, caplog):
        """AC1: Factura Abierta + Sin horario -> error, success False, no persistence."""
        caplog.set_level("ERROR")
        data = {
            "tipo_error": "Factura Abierta",
            "factura": "FEV123",
            "responsable": "Sin horario",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            result = add_error(data, session=_sess())

        # Envelope assertions
        assert result["status"] == "error"
        assert result["data"] == {}
        assert result.get("success") is False
        assert result["status"] != "warning"
        assert any("horario" in e.lower() for e in result["errors"])
        assert "No se puede enviar Factura Abierta sin horario" in result["errors"][0]
        # No persistence
        mock_crear.assert_not_called()
        # Logging prefix [BACK][ERROR]
        assert any("[BACK][ERROR] Rechazo Factura Abierta sin horario" in r.message for r in caplog.records)
        # factura in log
        assert any("FEV123" in r.message for r in caplog.records)

    def test_ac1_reject_variants_case_and_spaces(self):
        """AC1 edge: guard is exact after normalize — case/space trimmed still rejected."""
        data = {
            "tipo_error": "Factura Abierta",
            "factura": "FEV124",
            "responsable": "  sin HORARIO  ",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            result = add_error(data, session=_sess())

        assert result["status"] == "error"
        assert result.get("success") is False
        mock_crear.assert_not_called()

    def test_ac2_accept_factura_abierta_real_name(self):
        """AC2: Factura Abierta + real name -> success and creates."""
        data = {
            "tipo_error": "Factura Abierta",
            "factura": "FEV200",
            "responsable": "CARLOS OMAR",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "new-1", "factura": "FEV200"}
            result = add_error(data, session=_sess())

        assert result["status"] == "success"
        assert result["errors"] == []
        assert result["data"]["error"]["id"] == "new-1"
        mock_crear.assert_called_once()
        # Ensure responsable was passed uppercased
        assert mock_crear.call_args.args[4] == "CARLOS OMAR"

    def test_ac3_accept_otros_sin_horario(self):
        """AC3: Otros + Sin horario -> success (only Factura Abierta blocked)."""
        data = {
            "tipo_error": "Otros",
            "factura": "FEV300",
            "responsable": "Sin horario",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "new-2", "factura": "FEV300"}
            result = add_error(data, session=_sess())

        assert result["status"] == "success"
        assert result["status"] != "warning"
        mock_crear.assert_called_once()

    def test_ac4_sin_egreso_not_conflated(self):
        """AC4: Factura Abierta + Sin Egreso -> not blocked by Sin horario guard."""
        data = {
            "tipo_error": "Factura Abierta",
            "factura": "FEV400",
            "responsable": "Sin Egreso",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "new-3", "factura": "FEV400"}
            result = add_error(data, session=_sess())

        # Guard must NOT block Sin Egreso
        assert result["status"] == "success"
        mock_crear.assert_called_once()
        assert mock_crear.call_args.args[4] == "SIN EGRESO"

    def test_ac4_otros_tipo_with_sin_egreso_also_ok(self):
        """AC4 edge: Sin Egreso with other tipo also routes (existing flow)."""
        data = {
            "tipo_error": "Otros",
            "factura": "FEV401",
            "responsable": "Sin Egreso",
            "observacion": "test",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "new-4"}
            result = add_error(data, session=_sess())

        assert result["status"] == "success"
        mock_crear.assert_called_once()

    def test_envelope_never_warning(self):
        """Envelope must never be warning even on reject."""
        data = {
            "tipo_error": "Factura Abierta",
            "factura": "FEV999",
            "responsable": "Sin horario",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            result = add_error(data, session=_sess())

        assert result["status"] != "warning"
        assert result["status"] == "error"
        mock_crear.assert_not_called()
