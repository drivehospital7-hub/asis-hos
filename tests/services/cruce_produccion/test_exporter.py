"""Tests para app/services/cruce_produccion/exporter.py."""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app.services.cruce_produccion.exporter import (
    build_cruce_export_workbook,
    cache_cruce_result,
    get_cached_cruce_result,
)

FALTANTES = [
    {
        "codigo": "FEV999",
        "numero_factura_original": "FEV999",
        "responsable": "Luis",
        "fec_factura": "2026-01-05",
        "estado_novedad": "S",
        "facturador": "",
    }
]
REVISAR = [{"numero_factura_original": "PENDIENTE", "responsable": "Marta", "fec_factura": "2026-02-01"}]


class TestBuildWorkbook:
    def test_dos_hojas_con_headers_y_datos(self) -> None:
        buffer = build_cruce_export_workbook(FALTANTES, REVISAR)
        assert isinstance(buffer, BytesIO)
        wb = load_workbook(buffer)
        assert wb.sheetnames == ["Faltantes", "Revisar", "Soportes no actualizados"]
        ws_f = wb["Faltantes"]
        assert [c.value for c in ws_f[1]] == [
            "Código",
            "Número Factura Original",
            "Responsable",
            "Fec. Factura",
            "Estado Novedad",
            "Facturador",
        ]
        assert [c.value for c in ws_f[2]] == ["FEV999", "FEV999", "Luis", "2026-01-05", "S", None]
        ws_r = wb["Revisar"]
        assert [c.value for c in ws_r[1]] == [
            "Número Factura Original",
            "Responsable",
            "Fec. Factura",
        ]
        assert [c.value for c in ws_r[2]] == ["PENDIENTE", "Marta", "2026-02-01"]
        ws_d = wb["Soportes no actualizados"]
        assert [c.value for c in ws_d[1]] == [
            "Código",
            "Facturador",
            "Ruta carpeta",
            "Mtime carpeta",
            "Estado novedad",
            "Motivo",
            "Fecha estado",
        ]
        assert ws_d.max_row == 1

    def test_tercera_hoja_con_desactualizados(self) -> None:
        des = [
            {
                "codigo": "FEV123",
                "facturador": "Fact1",
                "full_path": "/root/Fact1/FEV123",
                "mtime_carpeta": "2026-01-02T10:00:00",
                "estado_novedad": "S",
                "motivo": "Novedad pendiente",
                "fecha_estado": None,
            }
        ]
        buffer = build_cruce_export_workbook([], [], des)
        wb = load_workbook(buffer)
        assert wb.sheetnames == ["Faltantes", "Revisar", "Soportes no actualizados"]
        ws_d = wb["Soportes no actualizados"]
        assert [c.value for c in ws_d[2]] == [
            "FEV123", "Fact1", "/root/Fact1/FEV123", "2026-01-02T10:00:00",
            "S", "Novedad pendiente", None,
        ]

    def test_vacio_solo_headers(self) -> None:
        buffer = build_cruce_export_workbook([], [])
        wb = load_workbook(buffer)
        assert wb.sheetnames == ["Faltantes", "Revisar", "Soportes no actualizados"]
        assert wb["Faltantes"].max_row == 1
        assert wb["Revisar"].max_row == 1
        assert wb["Soportes no actualizados"].max_row == 1


class TestExportStoreRoundTrip:
    def test_cache_put_get_round_trip(self) -> None:
        export_id = cache_cruce_result(FALTANTES, REVISAR)
        assert get_cached_cruce_result(export_id) == {
            "faltantes": FALTANTES,
            "revisar": REVISAR,
            "desactualizados": [],
        }

    def test_cache_con_desactualizados_round_trip(self) -> None:
        des = [{"codigo": "FEV123", "motivo": "Novedad pendiente"}]
        export_id = cache_cruce_result(FALTANTES, REVISAR, des)
        assert get_cached_cruce_result(export_id) == {
            "faltantes": FALTANTES,
            "revisar": REVISAR,
            "desactualizados": des,
        }

    def test_cache_id_invalido_none(self) -> None:
        assert get_cached_cruce_result("no-existe") is None
