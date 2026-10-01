"""Tests para app/services/cruce_produccion/matcher.py."""

from __future__ import annotations

from app.services.cruce_produccion.matcher import (
    ESTADO_PENDIENTE,
    extract_code,
    find_desactualizados,
    find_faltantes,
)
from app.services.monitoreo_carpetas import InvoiceRecord


def _inv(code: str, facturador: str = "F1") -> InvoiceRecord:
    return InvoiceRecord(
        filename=code,
        facturador=facturador,
        full_path=f"/root/{facturador}/{code}",
        status="En revisión",
        invoice_type="FEV",
        invoice_code=code,
    )


class TestExtractCode:
    def test_fev_con_sufijo_matchea(self) -> None:
        assert extract_code("FEV123 FALTA") == "FEV123"

    def test_fev_case_insensitive_upper(self) -> None:
        assert extract_code("fev456 lista") == "FEV456"

    def test_cap_pattern(self) -> None:
        # Núcleo: el número manda, el sufijo _CC123 se ignora.
        assert extract_code("CAP001_CC123") == "CAP001"

    def test_cap_numero_pelado(self) -> None:
        # Caso real de producción: número sin sufijo.
        assert extract_code("CAP541133") == "CAP541133"
        assert extract_code("cap541133") == "CAP541133"

    def test_sin_codigo_none(self) -> None:
        assert extract_code("SIN CODIGO") is None
        assert extract_code(None) is None
        assert extract_code("   ") is None


class TestFindFaltantes:
    def test_solo_faltantes_con_responsable(self) -> None:
        rows = [
            {"numero_factura": "FEV123 FALTA", "responsable": "Ana", "fec_factura": "2026-01-05"},
            {"numero_factura": "FEV999", "responsable": "Luis", "fec_factura": None},
        ]
        result = find_faltantes(rows, [_inv("FEV123")])
        assert result["faltantes"] == [
            {
                "codigo": "FEV999",
                "numero_factura_original": "FEV999",
                "responsable": "Luis",
                "fec_factura": None,
                "estado_novedad": None,
                "facturador": "",
            }
        ]
        assert result["revisar"] == []
        assert result["resumen"] == {
            "total_produccion": 2,
            "total_carpetas": 1,
            "total_faltantes": 1,
            "total_revisar": 0,
        }

    def test_sin_codigo_va_a_revisar(self) -> None:
        rows = [{"numero_factura": "PENDIENTE", "responsable": "Marta", "fec_factura": "2026-01-05"}]
        result = find_faltantes(rows, [])
        assert result["faltantes"] == []
        assert result["revisar"] == [
            {"numero_factura_original": "PENDIENTE", "responsable": "Marta", "fec_factura": "2026-01-05"}
        ]
        assert result["resumen"]["total_revisar"] == 1

    def test_codigo_duplicado_en_produccion_una_vez(self) -> None:
        rows = [
            {"numero_factura": "FEV100", "responsable": "A"},
            {"numero_factura": "FEV100 extra", "responsable": "B"},
        ]
        result = find_faltantes(rows, [])
        assert len(result["faltantes"]) == 1
        assert result["faltantes"][0]["responsable"] == "A"

    def test_cap_pelado_matchea_carpeta_con_sufijo(self) -> None:
        rows = [{"numero_factura": "CAP541133", "responsable": "Mariney"}]
        result = find_faltantes(rows, [_inv("CAP541133_CC7")])
        assert result["faltantes"] == []
        assert result["revisar"] == []
        assert result["resumen"]["total_faltantes"] == 0

    def test_formatos_reales_carpetas(self) -> None:
        # Nombres tal cual aparecen en disco.
        rows = [
            {"numero_factura": "CAP541133", "responsable": "A"},
            {"numero_factura": "FEV12345", "responsable": "B"},
        ]
        facturas = [_inv("CAP541133_CC1006850129"), _inv("FEV12345 RX")]
        result = find_faltantes(rows, facturas)
        assert result["faltantes"] == []
        assert result["revisar"] == []

    def test_faltante_con_novedad_pendiente_s(self) -> None:
        rows = [{"numero_factura": "FEV999", "responsable": "Luis", "fec_factura": "2026-01-05"}]
        novedades = [{"factura": "FEV999 extra", "estado": "S"}]
        result = find_faltantes(rows, [], novedades)
        assert result["faltantes"] == [
            {
                "codigo": "FEV999",
                "numero_factura_original": "FEV999",
                "responsable": "Luis",
                "fec_factura": "2026-01-05",
                "estado_novedad": "S",
                "facturador": "",
            }
        ]

    def test_faltante_con_novedad_resuelta_n(self) -> None:
        rows = [{"numero_factura": "FEV999", "responsable": "Luis", "fec_factura": None}]
        novedades = [{"factura": "FEV999", "estado": "R"}]
        result = find_faltantes(rows, [], novedades)
        assert result["faltantes"][0]["estado_novedad"] == "N"

    def test_sin_novedades_estado_none(self) -> None:
        rows = [{"numero_factura": "FEV999", "responsable": "Luis", "fec_factura": None}]
        result = find_faltantes(rows, [])
        assert result["faltantes"][0]["estado_novedad"] is None
        result2 = find_faltantes(rows, [], None)
        assert result2["faltantes"][0]["estado_novedad"] is None


def _inv_mtime(code: str, mtime: float | None) -> InvoiceRecord:
    inv = _inv(code)
    inv.mtime = mtime
    return inv


def _nov(
    factura: str,
    estado: str,
    ultima: str | None = None,
    actualizado: str | None = None,
    creado: str | None = None,
) -> dict:
    nov: dict = {"factura": factura, "estado": estado}
    if ultima is not None:
        nov["ultima_modificacion_estado"] = ultima
    if actualizado is not None:
        nov["actualizado_en"] = actualizado
    if creado is not None:
        nov["creado_en"] = creado
    return nov


class TestFindDesactualizados:
    def test_solo_codigos_filtra_carpetas(self) -> None:
        facturas = [
            _inv_mtime("FEV100", 1_700_000_000.0),
            _inv_mtime("FEV200", 1_700_000_000.0),
        ]
        novedades = [
            _nov("FEV100", "S", "2026-01-01T10:00:00"),
            _nov("FEV200", "S", "2026-01-01T10:00:00"),
        ]
        result = find_desactualizados(facturas, novedades, solo_codigos={"FEV100"})
        assert [d["codigo"] for d in result["desactualizados"]] == ["FEV100"]
        assert result["resumen"] == {"total_desactualizados": 1}

    def test_estado_pendiente_es_s(self) -> None:
        assert ESTADO_PENDIENTE == "S"

    def test_pendiente_marca(self) -> None:
        facturas = [_inv_mtime("FEV123", 1_700_000_000.0)]
        novedades = [_nov("FEV123 extra", "S", "2026-01-01T10:00:00")]
        result = find_desactualizados(facturas, novedades)
        assert len(result["desactualizados"]) == 1
        entry = result["desactualizados"][0]
        assert entry["codigo"] == "FEV123"
        assert entry["facturador"] == "F1"
        assert entry["full_path"] == "/root/F1/FEV123"
        assert entry["mtime_carpeta"] is not None
        assert entry["estado_novedad"] == "S"
        assert entry["motivo"] == "Novedad pendiente"
        assert entry["fecha_estado"] == "2026-01-01T10:00:00"
        assert result["resumen"] == {"total_desactualizados": 1}

    def test_pendiente_marca_sin_mtime(self) -> None:
        facturas = [_inv_mtime("FEV123", None)]
        novedades = [_nov("FEV123", "S")]
        result = find_desactualizados(facturas, novedades)
        assert len(result["desactualizados"]) == 1
        assert result["desactualizados"][0]["mtime_carpeta"] is None

    def test_resuelta_posterior_marca(self) -> None:
        facturas = [_inv_mtime("FEV200", 1_700_000_000.0)]  # 2023-11-14
        novedades = [_nov("FEV200", "R", "2026-05-01T12:00:00")]
        result = find_desactualizados(facturas, novedades)
        assert len(result["desactualizados"]) == 1
        entry = result["desactualizados"][0]
        assert entry["motivo"] == "Resuelta después de modificar carpeta"
        assert entry["estado_novedad"] == "R"
        assert result["resumen"] == {"total_desactualizados": 1}

    def test_resuelta_anterior_no_marca(self) -> None:
        facturas = [_inv_mtime("FEV300", 1_800_000_000.0)]  # 2027-01-15
        novedades = [_nov("FEV300", "R", "2026-05-01T12:00:00")]
        result = find_desactualizados(facturas, novedades)
        assert result == {
            "desactualizados": [],
            "resumen": {"total_desactualizados": 0},
        }

    def test_sin_mtime_no_marca_por_resuelta(self) -> None:
        facturas = [_inv_mtime("FEV400", None)]
        novedades = [_nov("FEV400", "R", "2026-05-01T12:00:00")]
        result = find_desactualizados(facturas, novedades)
        assert result["desactualizados"] == []
        assert result["resumen"] == {"total_desactualizados": 0}

    def test_fallback_actualizado_en(self) -> None:
        facturas = [_inv_mtime("FEV500", 1_700_000_000.0)]
        novedades = [_nov("FEV500", "R", actualizado="2026-05-01T12:00:00")]
        result = find_desactualizados(facturas, novedades)
        assert len(result["desactualizados"]) == 1
        assert result["desactualizados"][0]["fecha_estado"] == "2026-05-01T12:00:00"

    def test_fecha_invalida_no_marca(self) -> None:
        facturas = [_inv_mtime("FEV600", 1_700_000_000.0)]
        novedades = [_nov("FEV600", "R", "no-es-fecha")]
        result = find_desactualizados(facturas, novedades)
        assert result["desactualizados"] == []

    def test_sin_novedad_no_marca(self) -> None:
        facturas = [_inv_mtime("FEV700", 1_700_000_000.0)]
        result = find_desactualizados(facturas, [_nov("FEV999", "S")])
        assert result["desactualizados"] == []

    def test_dedup_por_codigo(self) -> None:
        facturas = [
            _inv_mtime("FEV800", 1_700_000_000.0),
            _inv_mtime("FEV800", 1_700_000_000.0),
        ]
        novedades = [
            _nov("FEV800", "S", "2026-01-01T10:00:00"),
            _nov("FEV800", "S", "2026-02-02T10:00:00"),
        ]
        result = find_desactualizados(facturas, novedades)
        assert len(result["desactualizados"]) == 1
        # Primera novedad relevante.
        assert result["desactualizados"][0]["fecha_estado"] == "2026-01-01T10:00:00"
