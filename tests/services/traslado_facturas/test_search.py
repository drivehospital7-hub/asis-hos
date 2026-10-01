"""Tests for traslado search_service: parse_codigos + buscar."""

from __future__ import annotations

import pytest

from app.services.monitoreo_carpetas import InvoiceRecord
from app.services.traslado_facturas.search_service import buscar, parse_codigos


def _inv(code: str, root: str = "/roots/Raiz", facturador: str = "Juan") -> InvoiceRecord:
    return InvoiceRecord(
        filename=f"{code}.pdf",
        facturador=facturador,
        full_path=f"{root}/{facturador}/{code}",
        status="En revisión",
        invoice_type="FEV",
        invoice_code=code,
    )


class TestParseCodigos:
    def test_separadores_mixtos(self) -> None:
        cadena = "FEV001,FEV002 FEV003\nFEV004;FEV005\tFEV006"
        assert parse_codigos(cadena) == [
            "FEV001", "FEV002", "FEV003", "FEV004", "FEV005", "FEV006",
        ]

    def test_dedup_preserva_orden(self) -> None:
        assert parse_codigos("FEV002, FEV001, FEV002, FEV001") == ["FEV002", "FEV001"]

    def test_ignora_fragmentos_sin_codigo(self) -> None:
        assert parse_codigos("hola, mundo, FEV007, 123") == ["FEV007"]

    def test_nucleo_cap_y_case(self) -> None:
        assert parse_codigos("cap001_cc123, fev9") == ["CAP001", "FEV9"]

    def test_vacio_y_none(self) -> None:
        assert parse_codigos("") == []
        assert parse_codigos(None) == []
        assert parse_codigos("   ,,, \n ") == []


class TestBuscar:
    def test_encontradas_y_no_encontradas(self) -> None:
        facturas = [_inv("FEV001"), _inv("FEV002")]
        result = buscar(["FEV001", "FEV999"], facturas)
        assert result["encontradas"] == [{
            "codigo": "FEV001",
            "full_path": "/roots/Raiz/Juan/FEV001",
            "facturador": "Juan",
        }]
        assert result["no_encontradas"] == ["FEV999"]

    def test_primera_coincidencia_ante_duplicados(self) -> None:
        facturas = [_inv("FEV001", facturador="Ana"), _inv("FEV001", facturador="Luis")]
        result = buscar(["FEV001"], facturas)
        assert len(result["encontradas"]) == 1
        assert result["encontradas"][0]["facturador"] == "Ana"

    def test_filtro_por_raices(self) -> None:
        facturas = [_inv("FEV001", root="/roots/A"), _inv("FEV002", root="/roots/B")]
        result = buscar(["FEV001", "FEV002"], facturas, roots=["/roots/A"])
        assert [e["codigo"] for e in result["encontradas"]] == ["FEV001"]
        assert result["no_encontradas"] == ["FEV002"]

    def test_sin_filtro_trae_todo(self) -> None:
        facturas = [_inv("FEV001", root="/roots/A"), _inv("FEV002", root="/roots/B")]
        result = buscar(["FEV001", "FEV002"], facturas)
        assert len(result["encontradas"]) == 2
        assert result["no_encontradas"] == []


class TestSplitRoots:
    """Partición cubiertas/no-cubiertas por prefijo bajo watcher-roots."""

    def test_cubiertas_bajo_watcher(self) -> None:
        from app.services.traslado_facturas.search_service import split_roots

        cub, nocub = split_roots(["/r/A", "/r/A/sub", "/otra/B"], ["/r/A"])
        assert cub == ["/r/A", "/r/A/sub"]
        assert nocub == ["/otra/B"]

    def test_sin_watcher_todo_no_cubierto(self) -> None:
        from app.services.traslado_facturas.search_service import split_roots

        assert split_roots(["/r/A"], []) == ([], ["/r/A"])
        assert split_roots(["/r/A"], None) == ([], ["/r/A"])

    def test_separador_windows(self) -> None:
        from app.services.traslado_facturas.search_service import split_roots

        cub, nocub = split_roots(["C:\\data\\X", "C:/otra"], ["C:/data"])
        assert cub == ["C:\\data\\X"]
        assert nocub == ["C:/otra"]

    def test_buscar_sobre_facturas_combinadas(self) -> None:
        """buscar recibe cache+frescas ya mergeadas y filtra por pedidas."""
        facturas = [_inv("FEV001", root="/cache/R"), _inv("FEV002", root="/free/S")]
        result = buscar(
            ["FEV001", "FEV002"], facturas, roots=["/cache/R", "/free/S"]
        )
        assert [e["codigo"] for e in result["encontradas"]] == ["FEV001", "FEV002"]
        assert result["no_encontradas"] == []
