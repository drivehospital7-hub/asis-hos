"""RED TDD notas (S1,S2,S6,S8): flag es_nota, forzado y propiedad created_by."""
from unittest.mock import patch
from app import create_app
from app.services.control_errores_service import add_error, update_error, get_errores

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

    def test_ajeno_si_observa_nota(self):
        """Cualquiera con acceso puede poner observacion_facturador en nota ajena."""
        from flask import session
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["username"] = "lector2"
            mock_get.return_value = {
                "id": "n1", "es_nota": True, "created_by": "lector1",
                "tipo_error": "Notificación",
            }
            mock_upd.return_value = {"id": "n1"}
            result = update_error("n1", {"observacion_facturador": "visto"})
        assert result["status"] == "success"
        assert mock_upd.call_args.kwargs == {"observacion_facturador": "visto"}

    def test_ajeno_no_cambia_estado_nota(self):
        """observacion abierta no habilita estado/responsable en notas ajenas."""
        from flask import session
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.obtener_error") as mock_get,
            patch("app.services.control_errores_service.actualizar_error") as mock_upd,
        ):
            session["permisos"] = ["control_urgencias"]
            session["username"] = "lector2"
            mock_get.return_value = {
                "id": "n1", "es_nota": True, "created_by": "lector1",
                "tipo_error": "Notificación",
            }
            result = update_error("n1", {"estado": "N", "observacion_facturador": "x"})
        assert isinstance(result, tuple) and result[1] == 403
        mock_upd.assert_not_called()


class TestNotasVisiblesFacturador:
    def test_facturador_ve_notas_ajenas_y_solo_sus_comunes(self):
        """El filtro de propietario no debe esconder notas (sin responsable)."""
        fixture = [
            {"id": "n1", "tipo_error": "Notificación", "estado": "",
             "responsable": "", "created_by": "otro",
             "creado_en": "2026-10-01T10:00:00", "es_nota": True},
            {"id": "n2", "tipo_error": "Notificación", "estado": "",
             "responsable": "", "created_by": "ana1",
             "creado_en": "2026-10-01T10:30:00", "es_nota": True},
            {"id": "c1", "tipo_error": "Error", "estado": "S",
             "responsable": "ANA LUZ", "created_by": "ana1",
             "creado_en": "2026-10-01T11:00:00"},
            {"id": "c2", "tipo_error": "Error", "estado": "S",
             "responsable": "PEDRO", "created_by": "pedro",
             "creado_en": "2026-10-01T12:00:00"},
        ]
        sess = {"rol": "facturador", "username": "ana1",
                "primer_nombre": "Ana", "apellido_1": "Luz",
                "permisos": ["control_urgencias"]}
        with (
            _APP.test_request_context(),
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": fixture}),
            patch("app.utils.errores_storage.obtener_imagenes_count",
                  return_value=0),
            patch("app.services.control_errores_service.users_store.get_user",
                  return_value={"primer_nombre": "Ana", "apellido_1": "Luz",
                                "rol": "facturador"}),
        ):
            result = get_errores(session=sess)
        assert result["status"] == "success"
        ids = {e["id"] for e in result["data"]["errores"]}
        assert ids == {"n2", "c1"}

    def test_validador_ve_todas_las_notas(self):
        """Sin filtro de propietario se ven todas las notas."""
        fixture = [
            {"id": "n1", "tipo_error": "Notificación", "estado": "",
             "responsable": "", "created_by": "otro",
             "creado_en": "2026-10-01T10:00:00", "es_nota": True},
            {"id": "n2", "tipo_error": "Notificación", "estado": "",
             "responsable": "", "created_by": "ana1",
             "creado_en": "2026-10-01T10:30:00", "es_nota": True},
        ]
        sess = {"rol": "validador", "username": "val1",
                "primer_nombre": "V", "apellido_1": "A",
                "permisos": ["control_urgencias:write"]}
        with (
            _APP.test_request_context(),
            patch("app.utils.errores_storage._leer_datos",
                  return_value={"errores": fixture}),
            patch("app.utils.errores_storage.obtener_imagenes_count",
                  return_value=0),
        ):
            result = get_errores(session=sess)
        assert result["status"] == "success"
        ids = {e["id"] for e in result["data"]["errores"]}
        assert ids == {"n1", "n2"}
