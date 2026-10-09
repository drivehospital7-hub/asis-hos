"""Vocabulario de categorías de control-novedades.

El vocabulario vigente son DOS categorías: "Error" y "Notificación".
Reemplaza al R14 de seis categorías (Otros, Soportes de Carpeta, Factura
Abierta, Carpeta no entregada, Factura, FURIPS): los valores heredados ya no
se ofrecen ni se persisten; al crear o actualizar se mapean
("Factura Abierta" → "Notificación", cualquier otro → "Error").

El filtrado (1.4) y la exportación (1.5) siguen siendo literales sobre lo
persistido, por eso sus fixtures conservan valores heredados.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from contextlib import ExitStack

from openpyxl import load_workbook

from app import create_app
from app.services.control_errores_export import build_errores_export_workbook
from app.services.control_errores_service import get_errores, get_opciones

_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})

EXPECTED = ["Error", "Notificación"]
LEGACY = ["Otros", "Soportes de Carpeta", "Factura Abierta", "Carpeta no entregada", "Factura", "FURIPS"]


def _error_fixture(error_id="err-1", tipo_error="Otros", factura="FAC-001", creado_en="2026-05-15T10:30:00"):
    return {
        "id": error_id,
        "factura": factura,
        "refactura": "",
        "creado_en": creado_en,
        "tipo_error": tipo_error,
        "observacion": "Desc",
        "responsable": "JUAN PEREZ",
        "observacion_facturador": "Revisar",
        "estado": "S",
        "validador": "MARIA GOMEZ",
    }


# ---------------------------------------------------------------------------
# 1.1 — Constant vocabulary
# ---------------------------------------------------------------------------

class TestR14SplitConstant:
    """ERROR_TIPO_URGENCIAS is exactly Error + Notificación."""

    def test_error_tipo_urgencias_is_two(self):
        from app.constants import ERROR_TIPO_URGENCIAS

        assert len(ERROR_TIPO_URGENCIAS) == 2

    def test_error_tipo_urgencias_exact_order(self):
        from app.constants import ERROR_TIPO_URGENCIAS

        assert ERROR_TIPO_URGENCIAS == EXPECTED

    def test_named_constants_match_vocabulary(self):
        from app.constants import ERROR_TIPO_ERROR, ERROR_TIPO_NOTIFICACION

        assert [ERROR_TIPO_ERROR, ERROR_TIPO_NOTIFICACION] == EXPECTED

    def test_not_contains_combined(self):
        from app.constants import ERROR_TIPO_URGENCIAS

        assert "Factura y Furips" not in ERROR_TIPO_URGENCIAS

    def test_legacy_values_removed(self):
        from app.constants import ERROR_TIPO_URGENCIAS

        assert not set(LEGACY) & set(ERROR_TIPO_URGENCIAS)


# ---------------------------------------------------------------------------
# 1.1b — normalizar_tipo_error (mapeo de valores heredados)
# ---------------------------------------------------------------------------

class TestNormalizarTipoError:
    """Cualquier valor entrante se lleva a una de las dos categorías vigentes."""

    def test_vigentes_se_conservan(self):
        from app.utils.errores_storage import normalizar_tipo_error

        assert normalizar_tipo_error("Error") == "Error"
        assert normalizar_tipo_error("Notificación") == "Notificación"

    def test_notificacion_sin_tilde_o_con_otra_caja(self):
        from app.utils.errores_storage import normalizar_tipo_error

        assert normalizar_tipo_error("notificacion") == "Notificación"
        assert normalizar_tipo_error("  NOTIFICACIÓN ") == "Notificación"

    def test_factura_abierta_es_notificacion(self):
        from app.utils.errores_storage import normalizar_tipo_error

        assert normalizar_tipo_error("Factura Abierta") == "Notificación"
        assert normalizar_tipo_error("factura  abierta") == "Notificación"

    def test_resto_de_heredados_es_error(self):
        from app.utils.errores_storage import normalizar_tipo_error

        for legacy in ["Otros", "Soportes de Carpeta", "Carpeta no entregada", "Factura", "FURIPS"]:
            assert normalizar_tipo_error(legacy) == "Error"

    def test_vacio_none_o_desconocido_es_error(self):
        from app.utils.errores_storage import normalizar_tipo_error

        assert normalizar_tipo_error("") == "Error"
        assert normalizar_tipo_error(None) == "Error"
        assert normalizar_tipo_error("cualquier cosa") == "Error"


# ---------------------------------------------------------------------------
# 1.2 — get_opciones()
# ---------------------------------------------------------------------------

class TestR14SplitOpciones:
    """get_opciones().tipos_error exposes only Error + Notificación."""

    def test_opciones_exact_two_ordered(self):
        with _APP.test_request_context(), patch(
            "app.services.control_errores_service.users_store.get_facturadores", return_value=[]
        ):
            tipos = get_opciones()["data"]["tipos_error"]
        assert tipos == EXPECTED
        assert len(tipos) == 2

    def test_opciones_omits_legacy(self):
        with _APP.test_request_context(), patch(
            "app.services.control_errores_service.users_store.get_facturadores", return_value=[]
        ):
            tipos = get_opciones()["data"]["tipos_error"]
        assert not set(LEGACY) & set(tipos)
        assert "Factura y Furips" not in tipos


# ---------------------------------------------------------------------------
# 1.2b — route GET /api/control-errores/opciones
# ---------------------------------------------------------------------------

class TestR14SplitOpcionesRoute:
    def test_route_opciones_two_categories(self, app_client):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]
        with patch("app.services.control_errores_service.users_store.get_facturadores", return_value=[]):
            resp = app_client.get("/api/control-errores/opciones")
        assert resp.status_code == 200
        tipos = resp.get_json()["data"]["tipos_error"]
        assert tipos == EXPECTED


# ---------------------------------------------------------------------------
# 1.3 — POST/PUT map legacy values to the two categories
# ---------------------------------------------------------------------------

class TestR14SplitCreateUpdate:
    """POST and PUT never persist a legacy category: it is mapped first."""

    def _login(self, app_client):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["username"] = "val1"
            sess["primer_nombre"] = "Juan"
            sess["apellido_1"] = "Perez"

    def _post(self, app_client, tipo_error):
        with patch("app.services.control_errores_service.crear_error") as mock_crear:
            mock_crear.return_value = {"id": "new-1", "tipo_error": "x", "factura": "FEV-001"}
            payload = {"factura": "FEV-001", "responsable": "LORENY ESPAÑA", "observacion": "x"}
            if tipo_error is not None:
                payload["tipo_error"] = tipo_error
            resp = app_client.post("/api/control-errores", json=payload)
        assert resp.status_code == 200
        return mock_crear.call_args.args[0]

    def test_post_error_and_notificacion_persist_as_is(self, app_client):
        self._login(app_client)
        assert self._post(app_client, "Error") == "Error"
        assert self._post(app_client, "Notificación") == "Notificación"

    def test_post_factura_abierta_persists_as_notificacion(self, app_client):
        self._login(app_client)
        assert self._post(app_client, "Factura Abierta") == "Notificación"

    def test_post_other_legacy_persist_as_error(self, app_client):
        self._login(app_client)
        for legacy in ["Otros", "Soportes de Carpeta", "Carpeta no entregada", "Factura", "FURIPS"]:
            assert self._post(app_client, legacy) == "Error"

    def test_post_without_tipo_defaults_to_error(self, app_client):
        self._login(app_client)
        assert self._post(app_client, None) == "Error"
        assert self._post(app_client, "") == "Error"

    def test_put_legacy_maps_before_update(self, app_client):
        def _fake():
            return {"id": "test-i1", "estado": "S", "tipo_error": "Error", "observacion": "pac", "observacion_facturador": "", "factura": "FAC-001", "responsable": ""}

        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["permisos"] = ["control_urgencias:write"]
            sess["username"] = "val1"
        for enviado, esperado in [("FURIPS", "Error"), ("Factura Abierta", "Notificación"), ("Notificación", "Notificación")]:
            with (
                patch("app.services.control_errores_service.obtener_error", return_value=_fake()),
                patch("app.services.control_errores_service.actualizar_error", return_value={"id": "test-i1", "tipo_error": esperado}) as mock_upd,
            ):
                resp = app_client.put("/api/control-errores/test-i1", json={"tipo_error": enviado})
            assert resp.status_code == 200
            assert mock_upd.call_args.kwargs["tipo_error"] == esperado


# ---------------------------------------------------------------------------
# 1.4 — Filter exact case-sensitive
# ---------------------------------------------------------------------------

class TestR14SplitFilter:
    """R14 S4/S5: ?tipo_error= exact, case-sensitive per literal."""

    def _fixture(self):
        return [
            {"id": "factura-1", "tipo_error": "Factura", "estado": "S", "responsable": "A", "creado_en": "2026-08-10T10:00:00"},
            {"id": "furips-1", "tipo_error": "FURIPS", "estado": "S", "responsable": "A", "creado_en": "2026-08-10T10:00:00"},
            {"id": "otros-1", "tipo_error": "Otros", "estado": "S", "responsable": "A", "creado_en": "2026-08-09T10:00:00"},
            {"id": "abierta-1", "tipo_error": "Factura Abierta", "estado": "S", "responsable": "A", "creado_en": "2026-08-08T10:00:00"},
        ]

    def test_filter_factura_exact(self):
        with _APP.test_request_context(), patch(
            "app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}
        ), patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0):
            result = get_errores(tipo_error="Factura", session={"rol": "validador"})
        assert [e["id"] for e in result["data"]["errores"]] == ["factura-1"]

    def test_filter_furips_exact(self):
        with _APP.test_request_context(), patch(
            "app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}
        ), patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0):
            result = get_errores(tipo_error="FURIPS", session={"rol": "validador"})
        assert [e["id"] for e in result["data"]["errores"]] == ["furips-1"]

    def test_filter_factura_lowercase_zero(self):
        with _APP.test_request_context(), patch(
            "app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}
        ), patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0):
            result = get_errores(tipo_error="factura", session={"rol": "validador"})
        assert result["data"]["errores"] == []

    def test_filter_furips_lowercase_zero(self):
        with _APP.test_request_context(), patch(
            "app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}
        ), patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0):
            result = get_errores(tipo_error="furips", session={"rol": "validador"})
        assert result["data"]["errores"] == []

    def test_filter_combined_zero(self):
        with _APP.test_request_context(), patch(
            "app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}
        ), patch("app.utils.errores_storage.obtener_imagenes_count", return_value=0):
            result = get_errores(tipo_error="Factura y Furips", session={"rol": "validador"})
        assert result["data"]["errores"] == []

    def test_filter_route_factura_and_furips(self, app_client):
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["rol"] = "validador"
            sess["username"] = "val1"
            sess["permisos"] = ["control_urgencias", "control_urgencias:write"]
        with patch("app.utils.errores_storage._leer_datos", return_value={"errores": self._fixture()}), patch(
            "app.utils.errores_storage.obtener_imagenes_count", return_value=0
        ):
            resp = app_client.get("/api/control-errores?tipo_error=Factura")
            assert [e["id"] for e in resp.get_json()["data"]["errores"]] == ["factura-1"]
            resp2 = app_client.get("/api/control-errores?tipo_error=FURIPS")
            assert [e["id"] for e in resp2.get_json()["data"]["errores"]] == ["furips-1"]
            resp3 = app_client.get("/api/control-errores?tipo_error=factura")
            assert resp3.get_json()["data"]["errores"] == []
            resp4 = app_client.get("/api/control-errores?tipo_error=Factura y Furips")
            assert resp4.get_json()["data"]["errores"] == []


# ---------------------------------------------------------------------------
# 1.5 — Export verbatim
# ---------------------------------------------------------------------------

class TestR14SplitExport:
    """R14 S6: export writes tipo_error verbatim, no normalization."""

    def _patch_images(self):
        return patch("app.services.control_errores_export.listar_imagenes", return_value=[])

    def test_export_factura_verbatim(self):
        with self._patch_images(), _APP.app_context():
            buf = build_errores_export_workbook([_error_fixture(tipo_error="Factura")], "http://testserver/")
        wb = load_workbook(BytesIO(buf.read()))
        ws = wb.active
        assert ws.cell(row=2, column=5).value == "Factura"
        assert [c.value for c in ws[1]][4] == "Categoría"

    def test_export_furips_verbatim_upper(self):
        with self._patch_images(), _APP.app_context():
            buf = build_errores_export_workbook([_error_fixture(tipo_error="FURIPS")], "http://testserver/")
        wb = load_workbook(BytesIO(buf.read()))
        ws = wb.active
        assert ws.cell(row=2, column=5).value == "FURIPS"

    def test_export_both_rows_verbatim(self):
        with self._patch_images(), _APP.app_context():
            buf = build_errores_export_workbook(
                [_error_fixture(error_id="e1", tipo_error="Factura"), _error_fixture(error_id="e2", tipo_error="FURIPS")],
                "http://testserver/",
            )
        wb = load_workbook(BytesIO(buf.read()))
        ws = wb.active
        assert ws.cell(row=2, column=5).value == "Factura"
        assert ws.cell(row=3, column=5).value == "FURIPS"

    def test_export_does_not_normalize_casing(self):
        """lowercase inputs stay lowercase — export is verbatim, not Title/upper."""
        with self._patch_images(), _APP.app_context():
            buf = build_errores_export_workbook([_error_fixture(tipo_error="factura")], "http://testserver/")
        wb = load_workbook(BytesIO(buf.read()))
        ws = wb.active
        assert ws.cell(row=2, column=5).value == "factura"
