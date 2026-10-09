"""Avisos de novedades para Revisor de Soportes.

Cubre: sellado del aviso en el almacén (novedad lista / reasignada / para uno
mismo), el endpoint GET /api/integration/control-novedades/nuevas y el ping.
Ninguna prueba toca la red ni el JSON real: el almacén va a ``tmp_path`` y
``urlopen`` / ``notificar_cambios`` se parchean.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.services.control_errores_service import update_error
from app.services.integration_service import query_nuevas
from app.utils import errores_storage, revisor_ping

_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})

_VALIDADOR = {
    "ce_authenticated": True,
    "username": "ana",
    "rol": "validador",
    "permisos": ["control_urgencias"],
    "primer_nombre": "Ana",
    "segundo_nombre": "",
    "apellido_1": "Valdez",
    "apellido_2": "",
}


@pytest.fixture()
def almacen(tmp_path):
    """Almacén aislado; ``ping`` es el mock de ``notificar_cambios``."""
    archivo = tmp_path / "control_errores.json"
    archivo.write_text(json.dumps({"errores": []}), encoding="utf-8")
    with (
        patch.object(errores_storage, "DATA_DIR", tmp_path),
        patch.object(errores_storage, "ERRORES_FILE", archivo),
        patch.object(errores_storage.revisor_ping, "notificar_cambios") as ping,
    ):
        yield ping


def _crear(**kwargs):
    base = {
        "tipo_error": "Error",
        "factura": "FEV1",
        "observacion": "FALTA SOPORTE",
        "estado": "S",
        "responsable": "LORENY ESPAÑA",
        "validador": "ANA VALDEZ",
        "created_by": "ana",
    }
    base.update(kwargs)
    return errores_storage.crear_error(**base)


def _guardado(error_id):
    return errores_storage.obtener_error(error_id)


# ---------------------------------------------------------------------------
# 1. Sellado del aviso al crear
# ---------------------------------------------------------------------------

class TestAvisoAlCrear:
    def test_con_responsable_y_descripcion_sella_y_avisa(self, almacen):
        nuevo = _crear(validador="Ana  Valdez")

        assert nuevo["aviso_motivo"] == "nueva"
        assert nuevo["aviso_por"] == "ANA VALDEZ"
        assert nuevo["aviso_en"] >= nuevo["creado_en"]
        assert _guardado(nuevo["id"])["aviso_en"] == nuevo["aviso_en"]
        almacen.assert_called_once()

    def test_fila_vacia_de_la_web_no_sella(self, almacen):
        nuevo = _crear(observacion="", responsable="")

        assert "aviso_en" not in nuevo
        almacen.assert_not_called()

    def test_sin_descripcion_no_sella(self, almacen):
        nuevo = _crear(observacion="  ")

        assert "aviso_en" not in nuevo
        almacen.assert_not_called()

    def test_reportarse_a_uno_mismo_sella_pero_no_avisa(self, almacen):
        nuevo = _crear(responsable="ANA VALDEZ", validador="Ana  Valdez")

        assert nuevo["aviso_motivo"] == "nueva"
        assert errores_storage.es_autoaviso(nuevo) is True
        almacen.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Sellado del aviso al editar
# ---------------------------------------------------------------------------

class TestAvisoAlEditar:
    def test_flujo_web_descripcion_y_luego_responsable(self, almacen):
        fila = _crear(observacion="", responsable="")

        errores_storage.actualizar_error(fila["id"], observacion="FALTA EPICRISIS", actor="ANA VALDEZ")
        assert "aviso_en" not in _guardado(fila["id"])
        almacen.assert_not_called()

        errores_storage.actualizar_error(fila["id"], responsable="LORENY ESPAÑA", actor="ANA VALDEZ")
        guardado = _guardado(fila["id"])
        assert guardado["aviso_motivo"] == "nueva"
        assert guardado["aviso_por"] == "ANA VALDEZ"
        almacen.assert_called_once()

    def test_flujo_web_responsable_y_luego_descripcion(self, almacen):
        fila = _crear(observacion="", responsable="")

        errores_storage.actualizar_error(fila["id"], responsable="LORENY ESPAÑA", actor="ANA VALDEZ")
        assert "aviso_en" not in _guardado(fila["id"])

        errores_storage.actualizar_error(fila["id"], observacion="FALTA EPICRISIS", actor="ANA VALDEZ")
        assert _guardado(fila["id"])["aviso_motivo"] == "nueva"
        almacen.assert_called_once()

    def test_editar_otros_campos_no_vuelve_a_avisar(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], observacion="TEXTO CORREGIDO", actor="ANA VALDEZ")
        errores_storage.actualizar_error(nuevo["id"], tipo_error="Notificación")
        errores_storage.actualizar_error(nuevo["id"], factura="FEV2")

        guardado = _guardado(nuevo["id"])
        assert guardado["aviso_en"] == nuevo["aviso_en"]
        assert "cambio_en" not in guardado
        almacen.assert_not_called()

    def test_mismo_responsable_con_otra_caja_no_es_reasignacion(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], responsable="  loreny   españa ", actor="ANA VALDEZ")

        assert _guardado(nuevo["id"])["aviso_en"] == nuevo["aviso_en"]
        almacen.assert_not_called()

    def test_cambio_de_responsable_es_reasignada(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="LUZ MORA")

        guardado = _guardado(nuevo["id"])
        assert guardado["aviso_motivo"] == "reasignada"
        assert guardado["aviso_por"] == "LUZ MORA"
        assert guardado["aviso_en"] > nuevo["aviso_en"]
        almacen.assert_called_once()

    def test_registro_heredado_sin_aviso_reasignado(self, almacen, tmp_path):
        heredado = {
            "id": "viejo-1", "tipo_error": "Otros", "factura": "FEV9",
            "observacion": "OBS", "estado": "S", "responsable": "LORENY ESPAÑA",
            "validador": "ANA VALDEZ", "creado_en": "2026-08-01T10:00:00.000001",
        }
        (tmp_path / "control_errores.json").write_text(
            json.dumps({"errores": [heredado]}, ensure_ascii=False), encoding="utf-8"
        )

        errores_storage.actualizar_error("viejo-1", estado="N")
        assert "aviso_en" not in _guardado("viejo-1")

        errores_storage.actualizar_error("viejo-1", responsable="CARLOS MEZA", actor="ANA VALDEZ")
        assert _guardado("viejo-1")["aviso_motivo"] == "reasignada"
        almacen.assert_called_once()

    def test_reasignarse_a_uno_mismo_no_genera_aviso_entregable(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="Carlos Meza")

        guardado = _guardado(nuevo["id"])
        assert guardado["aviso_motivo"] == "reasignada"
        assert errores_storage.es_autoaviso(guardado) is True
        # Igual se avisa a Revisor: el responsable anterior debe perder su aviso.
        assert guardado["cambio_en"] >= guardado["aviso_en"]
        almacen.assert_called_once()

    def test_quitar_el_responsable_no_sella_aviso_pero_si_cambio(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], responsable="", actor="ANA VALDEZ")

        guardado = _guardado(nuevo["id"])
        assert guardado["aviso_en"] == nuevo["aviso_en"]
        assert "cambio_en" in guardado
        almacen.assert_called_once()


class TestCambioDeNovedadAvisada:
    """Resolver, reabrir o reasignar una novedad ya avisada sella ``cambio_en``."""

    def test_resolver_sella_cambio_y_avisa(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], estado="N")

        guardado = _guardado(nuevo["id"])
        assert guardado["estado"] == "N"
        assert guardado["cambio_en"] > nuevo["aviso_en"]
        assert guardado["aviso_en"] == nuevo["aviso_en"]
        almacen.assert_called_once()

    def test_reabrir_vuelve_a_sellar_cambio(self, almacen):
        nuevo = _crear()
        errores_storage.actualizar_error(nuevo["id"], estado="N")
        primero = _guardado(nuevo["id"])["cambio_en"]
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], estado="S")

        assert _guardado(nuevo["id"])["cambio_en"] > primero
        almacen.assert_called_once()

    def test_guardar_el_mismo_estado_no_es_cambio(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], estado="S")

        assert "cambio_en" not in _guardado(nuevo["id"])
        almacen.assert_not_called()

    def test_reasignar_sella_aviso_y_cambio(self, almacen):
        nuevo = _crear()
        almacen.reset_mock()

        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="LUZ MORA")

        guardado = _guardado(nuevo["id"])
        assert guardado["aviso_motivo"] == "reasignada"
        assert guardado["cambio_en"] >= guardado["aviso_en"]
        almacen.assert_called_once()

    def test_novedad_nunca_avisada_no_sella_cambio(self, almacen):
        fila = _crear(observacion="", responsable="")

        errores_storage.actualizar_error(fila["id"], estado="N")

        assert "cambio_en" not in _guardado(fila["id"])
        almacen.assert_not_called()

    def test_primer_aviso_en_una_edicion_no_cuenta_como_cambio(self, almacen):
        fila = _crear(observacion="FALTA X", responsable="")

        errores_storage.actualizar_error(fila["id"], responsable="LORENY ESPAÑA", actor="ANA VALDEZ")

        guardado = _guardado(fila["id"])
        assert guardado["aviso_motivo"] == "nueva"
        assert "cambio_en" not in guardado
        almacen.assert_called_once()


class TestEliminarNovedadAvisada:
    def _eliminados(self, tmp_path):
        data = json.loads((tmp_path / "control_errores.json").read_text(encoding="utf-8"))
        return data.get("eliminados", [])

    def test_eliminar_avisada_deja_anotacion_y_avisa(self, almacen, tmp_path):
        nuevo = _crear()
        almacen.reset_mock()

        assert errores_storage.eliminar_error(nuevo["id"]) is True

        eliminados = self._eliminados(tmp_path)
        assert [e["id"] for e in eliminados] == [nuevo["id"]]
        assert set(eliminados[0]) == {"id", "eliminado_en"}
        assert _guardado(nuevo["id"]) is None
        almacen.assert_called_once()

    def test_eliminar_resuelta_avisada_tambien_se_anota(self, almacen, tmp_path):
        nuevo = _crear()
        errores_storage.actualizar_error(nuevo["id"], estado="N")
        almacen.reset_mock()

        errores_storage.eliminar_error(nuevo["id"])

        assert [e["id"] for e in self._eliminados(tmp_path)] == [nuevo["id"]]
        almacen.assert_called_once()

    def test_eliminar_no_avisada_no_deja_anotacion(self, almacen, tmp_path):
        fila = _crear(observacion="", responsable="")

        assert errores_storage.eliminar_error(fila["id"]) is True

        assert self._eliminados(tmp_path) == []
        almacen.assert_not_called()

    def test_eliminar_inexistente_no_hace_nada(self, almacen, tmp_path):
        assert errores_storage.eliminar_error("no-existe") is False
        assert self._eliminados(tmp_path) == []
        almacen.assert_not_called()

    def test_las_anotaciones_viejas_se_descartan(self, almacen, tmp_path):
        nuevo = _crear()
        archivo = tmp_path / "control_errores.json"
        data = json.loads(archivo.read_text(encoding="utf-8"))
        vieja = (datetime.now() - timedelta(days=31)).isoformat()
        reciente = (datetime.now() - timedelta(days=29)).isoformat()
        data["eliminados"] = [
            {"id": "muy-vieja", "eliminado_en": vieja},
            {"id": "reciente", "eliminado_en": reciente},
        ]
        archivo.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        errores_storage.eliminar_error(nuevo["id"])

        assert [e["id"] for e in self._eliminados(tmp_path)] == ["reciente", nuevo["id"]]

    def test_las_demas_escrituras_conservan_las_anotaciones(self, almacen, tmp_path):
        borrada = _crear(factura="A")
        errores_storage.eliminar_error(borrada["id"])

        otra = _crear(factura="B")
        errores_storage.actualizar_error(otra["id"], estado="N")

        assert [e["id"] for e in self._eliminados(tmp_path)] == [borrada["id"]]


class TestServicioPasaElActor:
    def _put(self, data, registro):
        with (
            _APP.test_request_context(),
            patch("app.services.control_errores_service.session", {
                "permisos": ["control_urgencias:write"],
                "primer_nombre": "Luz", "apellido_1": "Mora",
            }),
            patch("app.services.control_errores_service.obtener_error", return_value=registro),
            patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]),
            patch("app.services.control_errores_service.actualizar_error", return_value=registro) as mock_upd,
        ):
            update_error("x1", data)
        return mock_upd.call_args.kwargs

    def test_actor_viaja_al_cambiar_responsable_u_observacion(self):
        registro = {"id": "x1", "estado": "S"}

        assert self._put({"responsable": "CARLOS MEZA"}, registro)["actor"] == "LUZ MORA"
        assert self._put({"observacion": "algo"}, registro)["actor"] == "LUZ MORA"

    def test_actor_no_viaja_en_otras_ediciones(self):
        registro = {"id": "x1", "estado": "S"}

        assert "actor" not in self._put({"estado": "N"}, registro)
        assert "actor" not in self._put({"tipo_error": "Error"}, registro)


# ---------------------------------------------------------------------------
# 3. query_nuevas
# ---------------------------------------------------------------------------

def _antes_de(error):
    """Un cursor justo antes del aviso de ``error``."""
    return (datetime.fromisoformat(error["aviso_en"]) - timedelta(seconds=1)).isoformat()


class TestQueryNuevas:
    def test_sin_desde_devuelve_solo_el_cursor_inicial(self, almacen):
        _crear()

        envelope, status = query_nuevas(None, None, _VALIDADOR)

        assert status == 200
        data = envelope["data"]
        assert data["novedades"] == []
        assert data["cursor"] == data["ahora"]
        assert data["hay_mas"] is False
        datetime.fromisoformat(data["cursor"])

    def test_devuelve_los_posteriores_al_cursor_en_orden(self, almacen):
        primero = _crear(factura="FEV1")
        segundo = _crear(factura="FEV2")
        tercero = _crear(factura="FEV3")

        envelope, status = query_nuevas(primero["aviso_en"], None, _VALIDADOR)

        assert status == 200
        data = envelope["data"]
        assert [n["factura"] for n in data["novedades"]] == ["FEV2", "FEV3"]
        assert data["cursor"] == tercero["aviso_en"]
        assert data["hay_mas"] is False
        assert segundo["aviso_en"] < tercero["aviso_en"]

    def test_forma_del_aviso(self, almacen):
        nuevo = _crear(tipo_error="Notificación", refactura="R-1")

        aviso = query_nuevas(_antes_de(nuevo), None, _VALIDADOR)[0]["data"]["novedades"][0]

        assert aviso == {
            "aviso_id": f"{nuevo['id']}@{nuevo['aviso_en']}",
            "id": nuevo["id"],
            "motivo": "nueva",
            "clase": "notificacion",
            "tipo_error": "Notificación",
            "factura": "FEV1",
            "refactura": "R-1",
            "observacion": "FALTA SOPORTE",
            "responsable": "LORENY ESPAÑA",
            "reportado_por": "ANA VALDEZ",
            "validador": "ANA VALDEZ",
            "created_by": "ana",
            "estado": "S",
            "creado_en": nuevo["creado_en"],
            "aviso_en": nuevo["aviso_en"],
        }

    def test_clase_segun_categoria_incluso_heredada(self, almacen):
        base = _crear(tipo_error="Error", factura="A")
        _crear(tipo_error="Factura Abierta", factura="B")
        _crear(tipo_error="Otros", factura="C")

        novedades = query_nuevas(_antes_de(base), None, _VALIDADOR)[0]["data"]["novedades"]

        assert {n["factura"]: n["clase"] for n in novedades} == {
            "A": "error", "B": "notificacion", "C": "error",
        }

    def test_reasignacion_genera_otro_aviso_con_otro_aviso_id(self, almacen):
        nuevo = _crear()
        cursor = query_nuevas(_antes_de(nuevo), None, _VALIDADOR)[0]["data"]["cursor"]
        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="LUZ MORA")

        novedades = query_nuevas(cursor, None, _VALIDADOR)[0]["data"]["novedades"]

        assert len(novedades) == 1
        assert novedades[0]["motivo"] == "reasignada"
        assert novedades[0]["responsable"] == "CARLOS MEZA"
        assert novedades[0]["reportado_por"] == "LUZ MORA"
        assert novedades[0]["id"] == nuevo["id"]
        assert novedades[0]["aviso_id"] != f"{nuevo['id']}@{nuevo['aviso_en']}"

    def test_omite_resueltas_y_las_de_uno_mismo_pero_avanza_el_cursor(self, almacen):
        base = _crear(factura="A")
        resuelta = _crear(factura="B")
        errores_storage.actualizar_error(resuelta["id"], estado="N")
        propia = _crear(factura="C", responsable="ANA VALDEZ", validador="ANA VALDEZ")

        data = query_nuevas(base["aviso_en"], None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert data["cursor"] == propia["aviso_en"]

    def test_limite_pagina_y_el_cursor_continua(self, almacen):
        creados = [_crear(factura=f"FEV{i}") for i in range(5)]

        pagina1 = query_nuevas(_antes_de(creados[0]), "2", _VALIDADOR)[0]["data"]
        pagina2 = query_nuevas(pagina1["cursor"], "2", _VALIDADOR)[0]["data"]
        pagina3 = query_nuevas(pagina2["cursor"], "2", _VALIDADOR)[0]["data"]

        assert [n["factura"] for n in pagina1["novedades"]] == ["FEV0", "FEV1"]
        assert pagina1["hay_mas"] is True
        assert [n["factura"] for n in pagina2["novedades"]] == ["FEV2", "FEV3"]
        assert pagina2["hay_mas"] is True
        assert [n["factura"] for n in pagina3["novedades"]] == ["FEV4"]
        assert pagina3["hay_mas"] is False

    def test_sin_avisos_nuevos_conserva_el_cursor(self, almacen):
        nuevo = _crear()

        data = query_nuevas(nuevo["aviso_en"], None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert data["cursor"] == nuevo["aviso_en"]

    @pytest.mark.parametrize("desde", ["ayer", "2026-13-40", "2026-10-09T10:00:00-05:00"])
    def test_desde_invalido_es_400(self, almacen, desde):
        envelope, status = query_nuevas(desde, None, _VALIDADOR)

        assert status == 400
        assert envelope["status"] == "error"
        assert "desde" in envelope["errors"][0]

    @pytest.mark.parametrize("limite", ["0", "501", "muchos", "-3"])
    def test_limite_invalido_es_400(self, almacen, limite):
        envelope, status = query_nuevas("2026-10-09T10:00:00", limite, _VALIDADOR)

        assert status == 400
        assert "limite" in envelope["errors"][0]

    def test_token_de_facturador_solo_ve_lo_suyo(self, almacen):
        base = _crear(factura="A", responsable="LORENY ESPAÑA")
        _crear(factura="B", responsable="CARLOS MEZA")
        facturador = dict(_VALIDADOR, rol="facturador", username="loreny")
        usuario = {"primer_nombre": "Loreny", "segundo_nombre": "", "apellido_1": "España", "apellido_2": ""}

        with patch("app.services.control_errores_service.users_store.get_user", return_value=usuario):
            novedades = query_nuevas(_antes_de(base), None, facturador)[0]["data"]["novedades"]

        assert [n["factura"] for n in novedades] == ["A"]


class TestQueryNuevasCambiosYEliminadas:
    def test_sin_desde_trae_las_tres_listas_vacias(self, almacen):
        data = query_nuevas(None, None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert data["cambios_estado"] == []
        assert data["eliminadas"] == []

    def test_resolver_sale_en_cambios_estado(self, almacen):
        nuevo = _crear()
        cursor = query_nuevas(_antes_de(nuevo), None, _VALIDADOR)[0]["data"]["cursor"]
        errores_storage.actualizar_error(nuevo["id"], estado="N")
        cambio_en = _guardado(nuevo["id"])["cambio_en"]

        data = query_nuevas(cursor, None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert data["cambios_estado"] == [{
            "id": nuevo["id"],
            "estado": "N",
            "responsable": "LORENY ESPAÑA",
            "cambiado_en": cambio_en,
        }]
        assert data["cursor"] == cambio_en
        # Ya consumido: la siguiente consulta no lo repite.
        assert query_nuevas(data["cursor"], None, _VALIDADOR)[0]["data"]["cambios_estado"] == []

    def test_reabrir_informa_estado_pendiente(self, almacen):
        nuevo = _crear()
        errores_storage.actualizar_error(nuevo["id"], estado="N")
        cursor = _guardado(nuevo["id"])["cambio_en"]
        errores_storage.actualizar_error(nuevo["id"], estado="S")

        cambios = query_nuevas(cursor, None, _VALIDADOR)[0]["data"]["cambios_estado"]

        assert [(c["id"], c["estado"]) for c in cambios] == [(nuevo["id"], "S")]

    def test_reasignar_sale_como_aviso_y_como_cambio(self, almacen):
        nuevo = _crear()
        cursor = nuevo["aviso_en"]
        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="LUZ MORA")

        data = query_nuevas(cursor, None, _VALIDADOR)[0]["data"]

        assert [n["motivo"] for n in data["novedades"]] == ["reasignada"]
        assert [(c["id"], c["responsable"]) for c in data["cambios_estado"]] == [(nuevo["id"], "CARLOS MEZA")]

    def test_reasignarse_a_uno_mismo_informa_el_cambio_sin_aviso(self, almacen):
        nuevo = _crear()
        errores_storage.actualizar_error(nuevo["id"], responsable="CARLOS MEZA", actor="CARLOS MEZA")

        data = query_nuevas(nuevo["aviso_en"], None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert [c["responsable"] for c in data["cambios_estado"]] == ["CARLOS MEZA"]

    def test_eliminar_sale_en_eliminadas(self, almacen):
        nuevo = _crear()
        cursor = nuevo["aviso_en"]
        errores_storage.eliminar_error(nuevo["id"])

        data = query_nuevas(cursor, None, _VALIDADOR)[0]["data"]

        assert data["novedades"] == []
        assert data["cambios_estado"] == []
        assert [e["id"] for e in data["eliminadas"]] == [nuevo["id"]]
        assert data["cursor"] == data["eliminadas"][0]["eliminado_en"]

    def test_resolver_y_eliminar_antes_de_consultar(self, almacen):
        base = _crear(factura="BASE")
        nuevo = _crear(factura="X")
        errores_storage.actualizar_error(nuevo["id"], estado="N")
        errores_storage.eliminar_error(nuevo["id"])

        data = query_nuevas(base["aviso_en"], None, _VALIDADOR)[0]["data"]

        # El registro ya no existe: solo queda la eliminación.
        assert data["novedades"] == []
        assert data["cambios_estado"] == []
        assert [e["id"] for e in data["eliminadas"]] == [nuevo["id"]]

    def test_el_limite_cuenta_las_tres_listas_y_respeta_el_orden(self, almacen):
        a = _crear(factura="A")
        b = _crear(factura="B")
        errores_storage.actualizar_error(a["id"], estado="N")
        errores_storage.eliminar_error(b["id"])
        c = _crear(factura="C")

        desde = _antes_de(a)
        vistos = []
        for _ in range(10):
            data = query_nuevas(desde, "2", _VALIDADOR)[0]["data"]
            vistos += [("aviso", n["factura"]) for n in data["novedades"]]
            vistos += [("cambio", x["id"]) for x in data["cambios_estado"]]
            vistos += [("eliminada", x["id"]) for x in data["eliminadas"]]
            desde = data["cursor"]
            if not data["hay_mas"]:
                break

        # B se eliminó antes de consultar, así que su aviso ya no existe.
        assert sorted(vistos) == sorted([
            ("aviso", "C"),
            ("cambio", a["id"]),
            ("eliminada", b["id"]),
        ])
        assert c["aviso_en"] == desde

    def test_token_de_facturador_no_ve_cambios_ajenos(self, almacen):
        propia = _crear(factura="A", responsable="LORENY ESPAÑA")
        ajena = _crear(factura="B", responsable="CARLOS MEZA")
        errores_storage.actualizar_error(propia["id"], estado="N")
        errores_storage.actualizar_error(ajena["id"], estado="N")
        facturador = dict(_VALIDADOR, rol="facturador", username="loreny")
        usuario = {"primer_nombre": "Loreny", "segundo_nombre": "", "apellido_1": "España", "apellido_2": ""}

        with patch("app.services.control_errores_service.users_store.get_user", return_value=usuario):
            cambios = query_nuevas(ajena["aviso_en"], None, facturador)[0]["data"]["cambios_estado"]

        assert [c["id"] for c in cambios] == [propia["id"]]


# ---------------------------------------------------------------------------
# 4. Ruta GET /api/integration/control-novedades/nuevas
# ---------------------------------------------------------------------------

class TestRutaNuevas:
    URL = "/api/integration/control-novedades/nuevas"

    def _get(self, app_client, permisos, query=""):
        usuario = {
            "id": 1, "username": "revisor", "rol": "validador", "permisos": permisos,
            "primer_nombre": "Revisor", "segundo_nombre": "", "apellido_1": "Soportes", "apellido_2": "",
        }
        with patch("app.utils.token_store.get_user_for_token", return_value=usuario):
            return app_client.get(self.URL + query, headers={"Authorization": "Bearer valid-token"})

    def test_sin_token_es_401(self, app_client):
        assert app_client.get(self.URL).status_code == 401

    def test_token_invalido_es_401(self, app_client):
        with patch("app.utils.token_store.get_user_for_token", return_value=None):
            resp = app_client.get(self.URL, headers={"Authorization": "Bearer nope"})
        assert resp.status_code == 401

    def test_permiso_ajeno_es_403(self, app_client):
        assert self._get(app_client, ["procesar"]).status_code == 403

    def test_permiso_de_solo_lectura_basta(self, app_client, almacen):
        nuevo = _crear()

        resp = self._get(app_client, ["control_urgencias"], f"?desde={_antes_de(nuevo)}&limite=10")

        assert resp.status_code == 200
        cuerpo = resp.get_json()
        assert cuerpo["status"] == "success"
        assert cuerpo["errors"] == []
        assert [n["id"] for n in cuerpo["data"]["novedades"]] == [nuevo["id"]]

    def test_desde_invalido_es_400(self, app_client, almacen):
        assert self._get(app_client, ["control_urgencias"], "?desde=ayer").status_code == 400

    def test_no_acuna_cookie_de_sesion(self, app_client, almacen):
        resp = self._get(app_client, ["control_urgencias"])
        assert "Set-Cookie" not in resp.headers


# ---------------------------------------------------------------------------
# 5. Ping a Revisor
# ---------------------------------------------------------------------------

def _esperar_ping():
    for hilo in threading.enumerate():
        if hilo.name == "revisor-ping":
            hilo.join(timeout=5)


@pytest.fixture()
def ping_env(monkeypatch):
    monkeypatch.setenv("REVISOR_PING_URL", "http://192.0.2.10:5050/novedades/ping")
    monkeypatch.setenv("REVISOR_PING_CLAVE", "clave-de-prueba")
    yield
    _esperar_ping()


class TestRevisorPing:
    def test_sin_url_no_hace_nada(self, monkeypatch):
        monkeypatch.delenv("REVISOR_PING_URL", raising=False)
        with patch("app.utils.revisor_ping.urllib.request.urlopen") as urlopen:
            revisor_ping.notificar_cambios()
            _esperar_ping()
        urlopen.assert_not_called()

    def test_url_que_no_es_http_se_ignora(self, monkeypatch):
        monkeypatch.setenv("REVISOR_PING_URL", "file:///c:/windows/win.ini")
        with patch("app.utils.revisor_ping.urllib.request.urlopen") as urlopen:
            revisor_ping.notificar_cambios()
            _esperar_ping()
        urlopen.assert_not_called()

    def test_envia_post_vacio_con_clave_y_timeout(self, ping_env):
        with patch("app.utils.revisor_ping.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = MagicMock()
            revisor_ping.notificar_cambios()
            _esperar_ping()

        urlopen.assert_called_once()
        request = urlopen.call_args.args[0]
        assert request.full_url == "http://192.0.2.10:5050/novedades/ping"
        assert request.get_method() == "POST"
        assert request.data == b""
        assert request.get_header("X-revisor-clave") == "clave-de-prueba"
        assert urlopen.call_args.kwargs["timeout"] == 2

    def test_un_fallo_de_red_no_se_propaga_ni_filtra_la_clave(self, ping_env, caplog):
        caplog.set_level("INFO")
        with patch("app.utils.revisor_ping.urllib.request.urlopen", side_effect=OSError("sin ruta")):
            revisor_ping.notificar_cambios()
            _esperar_ping()

        assert any("Ping a Revisor falló" in r.message for r in caplog.records)
        assert not any("clave-de-prueba" in r.getMessage() for r in caplog.records)
        # El estado queda limpio: un ping posterior vuelve a salir.
        with patch("app.utils.revisor_ping.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = MagicMock()
            revisor_ping.notificar_cambios()
            _esperar_ping()
        urlopen.assert_called_once()

    def test_rafaga_se_agrupa_en_dos_envios(self, ping_env):
        en_vuelo = threading.Event()
        soltar = threading.Event()
        llamadas = []

        def lento(*args, **kwargs):
            llamadas.append(1)
            en_vuelo.set()
            soltar.wait(timeout=5)
            return MagicMock()

        with patch("app.utils.revisor_ping.urllib.request.urlopen", side_effect=lento):
            revisor_ping.notificar_cambios()
            assert en_vuelo.wait(timeout=5)
            for _ in range(20):
                revisor_ping.notificar_cambios()
            soltar.set()
            _esperar_ping()

        assert len(llamadas) == 2

    def test_guardar_no_espera_al_ping(self, ping_env, tmp_path):
        soltar = threading.Event()
        archivo = tmp_path / "control_errores.json"
        archivo.write_text(json.dumps({"errores": []}), encoding="utf-8")
        with (
            patch.object(errores_storage, "DATA_DIR", tmp_path),
            patch.object(errores_storage, "ERRORES_FILE", archivo),
            patch("app.utils.revisor_ping.urllib.request.urlopen", side_effect=lambda *a, **k: soltar.wait(5)),
        ):
            nuevo = _crear()
            # crear_error ya volvió y persistió aunque el ping siga colgado.
            assert errores_storage.obtener_error(nuevo["id"]) is not None
            soltar.set()
            _esperar_ping()
