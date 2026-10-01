"""Tests para app/services/cruce_produccion/reader.py."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from app.services.cruce_produccion.reader import read_produccion


def _make_workbook(path: Path, headers: list, rows: list[list]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(str(path))
    return path


HEADERS = ["Número Factura", "Responsable Cierra Facturar", "Fec. Factura"]


class TestReadProduccion:
    def test_headers_ok_lee_filas(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            HEADERS,
            [["FEV123 ", "  Ana Pérez ", "2026-01-05"], ["FEV456", None, None]],
        )
        rows, missing = read_produccion(xlsx)
        assert missing == []
        assert rows == [
            {"numero_factura": "FEV123", "responsable": "Ana Pérez", "fec_factura": "2026-01-05"},
            {"numero_factura": "FEV456", "responsable": None, "fec_factura": None},
        ]

    def test_missing_headers_para_error_envelope(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            ["Número Factura", "Otra Columna"],
            [["FEV123", "x"]],
        )
        rows, missing = read_produccion(xlsx)
        assert rows == []
        assert missing == ["Responsable Cierra Facturar", "Fec. Factura"]

    def test_celdas_vacias_none_safe(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            HEADERS,
            [[None, "   ", None], ["", "Juan", "  "]],
        )
        rows, missing = read_produccion(xlsx)
        assert missing == []
        # Fila totalmente vacía se saltea; la de solo-responsable queda.
        assert rows == [{"numero_factura": None, "responsable": "Juan", "fec_factura": None}]

    def test_filas_vacias_finales_no_inflan_revisar(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            HEADERS,
            [["FEV1", "Ana", "2026-02-01"], [None, None, None], ["", "  ", ""]],
        )
        rows, missing = read_produccion(xlsx)
        assert missing == []
        assert rows == [{"numero_factura": "FEV1", "responsable": "Ana", "fec_factura": "2026-02-01"}]

    def test_headers_con_filas_de_titulo_encima(self, tmp_path: Path) -> None:
        """Igual que /procesar: headers en fila 3 con títulos encima."""
        wb = Workbook()
        ws = wb.active
        ws.append(["REPORTE DE PRODUCCIÓN"])
        ws.append(["Generado: hoy"])
        ws.append(HEADERS)
        ws.append(["FEV789", "María", "2026-03-10"])
        xlsx = tmp_path / "prod.xlsx"
        wb.save(str(xlsx))
        rows, missing = read_produccion(xlsx)
        assert missing == []
        assert rows == [{"numero_factura": "FEV789", "responsable": "María", "fec_factura": "2026-03-10"}]

    def test_fec_leida_str_con_strip(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            HEADERS,
            [["FEV1", "Ana", "  2026-01-05  "]],
        )
        rows, missing = read_produccion(xlsx)
        assert missing == []
        assert rows[0]["fec_factura"] == "2026-01-05"

    def test_fec_leida_date_y_datetime_a_isoformat(self, tmp_path: Path) -> None:
        xlsx = _make_workbook(
            tmp_path / "prod.xlsx",
            HEADERS,
            [
                ["FEV1", "Ana", date(2026, 1, 5)],
                ["FEV2", "Luis", datetime(2026, 2, 6, 10, 30)],
            ],
        )
        rows, missing = read_produccion(xlsx)
        assert missing == []
        # openpyxl devuelve celdas de fecha como datetime (medianoche).
        assert rows[0]["fec_factura"].startswith("2026-01-05")
        assert rows[1]["fec_factura"] == "2026-02-06T10:30:00"
