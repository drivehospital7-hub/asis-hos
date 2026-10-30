"""RED TDD notas (S1,S2,S6,S8): flag es_nota, forzado y propiedad created_by."""
from unittest.mock import patch
from app import create_app
from app.services.control_errores_service import add_error, update_error

_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _sess_lectura(username="lector1"):
    return {
        "username": username,
        "primer_nombre": "Lec",
        "apellido_1": "Tor",
        "permisos": ["control_urgencias"],
    }


class TestAddNota:
    def test_add_nota_fuerza_campos(self):
        """Nota lectura: tipo Notificación fijo, estado vacío, sin responsable/refactura."""
        data = {
            "es_nota": True,
            "tipo_error": "Error",
            "factura": "fev-1",
            "observacion": "nota de prueba",
            "responsable": "ALGUIEN",
            "estado": "S",
            "refactura": "X",
        }
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.crear_error") as mock_crear,
        ):
            mock_crear.return_value = {"id": "n1"}
            result = add_error(data, session=_sess_lectura())
        assert result["status"] == "success"
        args, kwargs = mock_crear.call_args
        assert args[0] == "Notificación"
        assert args[3] == ""
        assert args[4] == ""
        assert kwargs.get("refactura") == ""
        assert kwargs.get("es_nota") is True


class TestUpdateNota:
    def test_dueño_edita_nota(self):
        """Dueño con lectura puede editar su nota (factura/observacion)."""
        from flask import session
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["username"] = "lector1"
            mock_get.return_value = {
                "id": "n1", "es_nota": True, "created_by": "lector1",
                "tipo_error": "Notificación",
            }
            mock_upd.return_value = {"id": "n1"}
            result = update_error("n1", {"observacion": "nuevo texto"})
        assert result["status"] == "success"
        mock_upd.assert_called_once()

    def test_ajeno_no_edita_nota(self):
        """Write no edita nota ajena aunque la vea."""
        from flask import session
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias:write"]
            session["username"] = "validador9"
            mock_get.return_value = {
                "id": "n1", "es_nota": True, "created_by": "lector1",
                "tipo_error": "Notificación",
            }
            result = update_error("n1", {"observacion": "hack"})
        assert isinstance(result, tuple) and result[1] == 403
        mock_upd.assert_not_called()

    def test_nota_sin_factura_400(self):
        """Nota sin factura → 400 (el front muestra el error sin recargar)."""
        result = add_error({"es_nota": True, "factura": "", "observacion": "x"}, session=_sess_lectura())
        assert isinstance(result, tuple) and result[1] == 400
        assert result[0]["status"] == "error"

    def test_comun_sin_factura_400(self):
        """Novedad común sin factura → 400 igual que la nota (no más ERR-<id>)."""
        with patch("app.services.control_errores_service.crear_error") as mock_crear:
            result = add_error(
                {"tipo_error": "Error", "factura": "", "observacion": "x",
                 "estado": "S", "responsable": "ALGUIEN"},
                session={"username": "v", "primer_nombre": "V", "apellido_1": "A",
                          "permisos": ["control_urgencias:write"]},
            )
        assert isinstance(result, tuple) and result[1] == 400
        assert result[0]["errors"] == ["Factura requerida"]
        mock_crear.assert_not_called()


class TestDeleteSessionKwarg:
    def test_admin_borra_comun_con_session_kwarg(self):
        """La ruta llama delete_error(id, session=dict) — el kwarg debe existir."""
        from app.services.control_errores_service import delete_error
        with (
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.eliminar_error") as mock_del,
        ):
            mock_get.return_value = {"id": "x", "created_by": "otro"}
            mock_del.return_value = True
            result = delete_error("x", session={"username": "admin1", "permisos": ["*"]})
        assert result["status"] == "success"
        mock_del.assert_called_once_with("x")
