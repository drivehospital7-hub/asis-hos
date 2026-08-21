"""Tests para el export a Excel de Control de Errores (servicio + ruta)."""

from contextlib import ExitStack
from io import BytesIO
from unittest.mock import patch

from openpyxl import load_workbook

from app import create_app
from app.services.control_errores_export import (
    HEADERS,
    build_errores_export_workbook,
    filename_export,
)

_APP = create_app({"TESTING": True, "SECRET_KEY": "test-secret-key"})


def _error_fixture(error_id="err-1", factura="FAC-001", creado_en="2026-05-15T10:30:00",
                   estado="S", validador="MARIA GOMEZ"):
    """Un error mínimo con los campos que el export lee."""
    return {
        "id": error_id,
        "factura": factura,
        "creado_en": creado_en,
        "tipo_error": "Otros",
        "observacion": "Descripción con acentos",
        "responsable": "JUAN PEREZ",
        "observacion_facturador": "Revisar",
        "estado": estado,
        "validador": validador,
    }


class TestFilenameExport:
    def test_mes_valido_deriva_nombre(self):
        assert filename_export("2026-05") == "control-errores-May-2026.xlsx"

    def test_mes_invalido_usa_fecha_actual(self):
        name = filename_export(None)
        assert name.startswith("control-errores-")
        assert name.endswith(".xlsx")


class TestBuildWorkbook:
    def test_headers_y_fila_con_hipervinculos(self):
        with patch(
            "app.services.control_errores_export.listar_imagenes",
            return_value=["file_1.pdf", "image_2.jpg"],
        ):
            buffer = build_errores_export_workbook([_error_fixture()], "http://testserver/")

        wb = load_workbook(BytesIO(buffer.read()))
        ws = wb.active

        assert [c.value for c in ws[1]] == HEADERS
        assert ws["A1"].font.bold is True
        assert ws["K1"].font.bold is True

        row = [c.value for c in ws[2]]
        assert row[0] == "MARIA GOMEZ"       # Validador
        assert row[1] == "FAC-001"           # Factura
        assert row[2] == "15/05/2026"        # Creado dd/mm/yyyy
        assert row[3] == "Otros"             # Categoría
        assert row[7] == "Pendiente"         # Estado
        assert row[8] == "Abrir PDF"         # Adjunto 1
        assert row[9] == "Abrir imagen"      # Adjunto 2
        assert row[10] is None               # Adjunto 3 vacío

        cell9 = ws.cell(row=2, column=9)
        assert cell9.hyperlink.target == "http://testserver/api/control-errores/err-1/imagenes/file_1.pdf"
        assert cell9.style == "Hyperlink"

        cell10 = ws.cell(row=2, column=10)
        assert cell10.hyperlink.target == "http://testserver/api/control-errores/err-1/imagenes/image_2.jpg"

        assert ws.cell(row=2, column=11).hyperlink is None

    def test_estado_resuelto_y_fecha_bruta(self):
        with patch(
            "app.services.control_errores_export.listar_imagenes",
            return_value=[],
        ):
            buffer = build_errores_export_workbook(
                [_error_fixture(estado="N", creado_en="fecha-rara")],
                "http://testserver/",
            )

        wb = load_workbook(BytesIO(buffer.read()))
        ws = wb.active
        row = [c.value for c in ws[2]]
        assert row[7] == "Resuelto"
        assert row[2] == "fecha-rara"

    def test_hipervinculo_escapada_nombre_con_espacios(self):
        with patch(
            "app.services.control_errores_export.listar_imagenes",
            return_value=["mi archivo.pdf"],
        ):
            buffer = build_errores_export_workbook([_error_fixture()], "http://testserver/")

        wb = load_workbook(BytesIO(buffer.read()))
        ws = wb.active
        cell = ws.cell(row=2, column=9)
        assert cell.hyperlink.target == (
            "http://testserver/api/control-errores/err-1/imagenes/mi%20archivo.pdf"
        )


def _login(app_client):
    with app_client.session_transaction() as sess:
        sess["ce_authenticated"] = True
        sess["rol"] = "validador"
        sess["username"] = "val1"
        sess["permisos"] = ["control_urgencias", "control_urgencias:write"]


def _patch_export_pipeline(fixture, stack: ExitStack, adjuntos=None):
    """Parchea el pipeline completo que la ruta usa (storage + adjuntos)."""
    stack.enter_context(patch("app.utils.errores_storage._leer_datos",
                              return_value={"errores": fixture}))
    stack.enter_context(patch("app.utils.errores_storage.obtener_imagenes_count",
                              return_value=0))
    stack.enter_context(patch("app.services.control_errores_export.listar_imagenes",
                              return_value=adjuntos if adjuntos is not None else []))


class TestExportRoute:
    def test_requiere_autenticacion(self, app_client):
        resp = app_client.get(
            "/api/control-errores/export",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["data"] == {}
        assert len(data["errors"]) > 0

    def test_devuelve_xlsx_valido(self, app_client):
        _login(app_client)
        fixture = [_error_fixture()]
        with ExitStack() as stack:
            _patch_export_pipeline(fixture, stack, adjuntos=["file_1.pdf"])
            resp = app_client.get("/api/control-errores/export?mes=2026-05")

        assert resp.status_code == 200
        assert resp.content_type.startswith("application/vnd.openxmlformats")
        assert "control-errores-May-2026.xlsx" in resp.headers["Content-Disposition"]

        wb = load_workbook(BytesIO(resp.data))
        ws = wb.active
        assert [c.value for c in ws[1]] == HEADERS
        assert ws["A2"].value == "MARIA GOMEZ"
        assert ws["B2"].value == "FAC-001"
        assert ws["I2"].hyperlink.target == (
            "http://localhost/api/control-errores/err-1/imagenes/file_1.pdf"
        )

    def test_filtro_por_mes(self, app_client):
        _login(app_client)
        fixture = [
            _error_fixture(error_id="may", factura="FAC-MAY", creado_en="2026-05-15T10:00:00"),
            _error_fixture(error_id="jun", factura="FAC-JUN", creado_en="2026-06-02T10:00:00"),
        ]
        with ExitStack() as stack:
            _patch_export_pipeline(fixture, stack)
            resp = app_client.get("/api/control-errores/export?mes=2026-05")

        assert resp.status_code == 200
        wb = load_workbook(BytesIO(resp.data))
        ws = wb.active
        facturas = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
        assert facturas == ["FAC-MAY"]

    def test_sin_datos_devuelve_error_400(self, app_client):
        _login(app_client)
        fixture = [_error_fixture(creado_en="2026-06-02T10:00:00")]
        with ExitStack() as stack:
            _patch_export_pipeline(fixture, stack)
            resp = app_client.get("/api/control-errores/export?mes=2026-05")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0