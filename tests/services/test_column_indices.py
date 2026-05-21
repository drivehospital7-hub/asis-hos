"""Tests para app/services/transversales/column_indices.py."""

from __future__ import annotations

import pytest

from app.services.transversales.column_indices import get_column_indices


class TestGetColumnIndices:
    """Tests para get_column_indices."""

    def test_mapea_headers_conocidos(self) -> None:
        """Debe mapear headers conocidos a sus índices."""
        headers = [
            "Número Factura",
            "Vlr. Subsidiado",
            "Vlr. Procedimiento",
            "Tipo Procedimiento",
        ]
        required = {
            "numero_factura": "Número Factura",
            "vlr_subsidiado": "Vlr. Subsidiado",
            "vlr_procedimiento": "Vlr. Procedimiento",
            "tipo_procedimiento": "Tipo Procedimiento",
        }

        indices, missing = get_column_indices(headers, required)

        assert missing == []
        assert indices["numero_factura"] == 0
        assert indices["vlr_subsidiado"] == 1
        assert indices["vlr_procedimiento"] == 2
        assert indices["tipo_procedimiento"] == 3

    def test_headers_no_encontrados_son_none(self) -> None:
        """Headers no encontrados deben ser None y listados como faltantes."""
        headers = ["Columna Rara", "Otra Columna"]
        required = {
            "numero_factura": "Número Factura",
            "vlr_subsidiado": "Vlr. Subsidiado",
        }

        indices, missing = get_column_indices(headers, required)

        assert indices["numero_factura"] is None
        assert indices["vlr_subsidiado"] is None
        assert "Número Factura" in missing
        assert "Vlr. Subsidiado" in missing

    def test_requiere_coincidencia_exacta(self) -> None:
        """Requiere coincidencia EXACTA, no infiere."""
        headers = ["Número Factura", "Nº Identificación"]
        required = {
            "numero_factura": "Número Factura",
            "identificacion": "Nº Identificación",
        }

        indices, missing = get_column_indices(headers, required)

        assert missing == []
        assert indices["numero_factura"] == 0
        assert indices["identificacion"] == 1

    def test_soporta_headers_de_urgencias(self) -> None:
        """Debe funcionar con headers de urgencias (diferentes columnas)."""
        headers = [
            "Número Factura",
            "Código Tipo Procedimiento",
            "Cód. Equivalente CUPS",
            "Procedimiento",
            "Tipo Factura Descripción",
            "IDE Contrato",
            "Fecha Cierre",
        ]
        required = {
            "numero_factura": "Número Factura",
            "codigo_tipo_procedimiento": "Código Tipo Procedimiento",
            "codigo_equiv": "Cód. Equivalente CUPS",
            "procedimiento": "Procedimiento",
            "tipo_factura_descripcion": "Tipo Factura Descripción",
            "ide_contrato": "IDE Contrato",
            "fecha_cierre": "Fecha Cierre",
        }

        indices, missing = get_column_indices(headers, required)

        assert missing == []
        assert indices["numero_factura"] == 0
        assert indices["codigo_tipo_procedimiento"] == 1
        assert indices["codigo_equiv"] == 2
        assert indices["procedimiento"] == 3
        assert indices["tipo_factura_descripcion"] == 4
        assert indices["ide_contrato"] == 5
        assert indices["fecha_cierre"] == 6

    def test_lista_solo_faltantes_reales(self) -> None:
        """Solo debe listar como faltantes los que no se encontraron."""
        headers = ["Número Factura"]
        required = {
            "numero_factura": "Número Factura",
            "identificacion": "Nº Identificación",
            "cantidad": "Cantidad",
        }

        indices, missing = get_column_indices(headers, required)

        assert indices["numero_factura"] == 0
        assert indices["identificacion"] is None
        assert indices["cantidad"] is None
        assert missing == ["Nº Identificación", "Cantidad"]

    def test_headers_vacios_no_causan_error(self) -> None:
        """Lista vacía de headers debe retornar todos como None."""
        indices, missing = get_column_indices([], {"foo": "FOO"})

        assert indices["foo"] is None
        assert missing == ["FOO"]

    def test_maneja_valores_none_en_headers(self) -> None:
        """Headers con None no deben causar error."""
        headers = ["Número Factura", None, "Cantidad"]
        required = {
            "numero_factura": "Número Factura",
            "cantidad": "Cantidad",
        }

        indices, missing = get_column_indices(headers, required)

        assert indices["numero_factura"] == 0
        assert indices["cantidad"] == 2
        assert missing == []
