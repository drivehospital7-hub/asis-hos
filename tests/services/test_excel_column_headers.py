"""Tests para app/services/excel_column_headers.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.excel_column_headers import get_excel_column_headers


class TestGetExcelColumnHeaders:
    """Tests para la función get_excel_column_headers."""

    def test_archivo_no_existe_retorna_error(self, temp_output_dir: Path) -> None:
        """Archivo inexistente debe retornar status error."""
        archivo_falso = temp_output_dir / "no_existe.xlsx"
        
        result = get_excel_column_headers(archivo_falso)
        
        assert result["status"] == "error"
        assert result["data"] == {}
        assert len(result["errors"]) > 0
        assert "no encontrado" in result["errors"][0].lower()

    def test_formato_no_soportado_retorna_error(self, temp_output_dir: Path) -> None:
        """Archivo con extensión no soportada (.txt) debe retornar error."""
        archivo_txt = temp_output_dir / "archivo.txt"
        archivo_txt.write_text("contenido de prueba")
        
        result = get_excel_column_headers(archivo_txt)
        
        assert result["status"] == "error"
        assert result["data"] == {}
        assert len(result["errors"]) > 0
        assert "no soportado" in result["errors"][0].lower()

    def test_archivo_excel_valido_retorna_columnas(
        self, sample_excel_file: Path
    ) -> None:
        """Archivo Excel válido debe retornar las columnas correctamente."""
        result = get_excel_column_headers(sample_excel_file)
        
        assert result["status"] == "success"
        assert result["errors"] == []
        assert "columns" in result["data"]
        
        columns = result["data"]["columns"]
        assert isinstance(columns, list)
        assert len(columns) == 4
        assert "NUMERO_FACTURA" in columns
        assert "VALOR" in columns
        assert "FECHA" in columns
        assert "CONVENIO" in columns

    def test_sheet_name_y_sheet_id_juntos_retorna_error(
        self, sample_excel_file: Path
    ) -> None:
        """Pasar sheet_name y sheet_id juntos debe retornar error."""
        result = get_excel_column_headers(
            sample_excel_file, sheet_name="Datos", sheet_id=0
        )
        
        assert result["status"] == "error"
        assert result["data"] == {}
        assert len(result["errors"]) > 0
        assert "solo uno" in result["errors"][0].lower()

    def test_hoja_sin_columnas_retorna_error(self, empty_excel_file: Path) -> None:
        """Hoja Excel vacía (sin columnas) debe retornar error."""
        result = get_excel_column_headers(empty_excel_file)
        
        assert result["status"] == "error"
        assert result["data"] == {}
        assert len(result["errors"]) > 0
        assert "no tiene columnas" in result["errors"][0].lower()
