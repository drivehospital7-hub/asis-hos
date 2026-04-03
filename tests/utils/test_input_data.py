"""Tests para app/utils/input_data.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.utils.input_data import (
    input_data_directory,
    list_excel_filenames,
    output_data_directory,
    resolve_safe_excel_in_input,
)


class TestInputDataDirectory:
    """Tests para la función input_data_directory."""

    def test_input_data_directory_retorna_path(self) -> None:
        """input_data_directory debe retornar un Path válido."""
        result = input_data_directory()
        
        assert isinstance(result, Path)
        assert result.is_absolute()
        assert "data" in result.parts
        assert "input" in result.parts


class TestOutputDataDirectory:
    """Tests para la función output_data_directory."""

    def test_output_data_directory_retorna_path(self) -> None:
        """output_data_directory debe retornar un Path válido."""
        result = output_data_directory()
        
        assert isinstance(result, Path)
        assert result.is_absolute()
        assert "data" in result.parts
        assert "output" in result.parts


class TestListExcelFilenames:
    """Tests para la función list_excel_filenames."""

    def test_list_excel_filenames_sin_archivos_retorna_lista_vacia(
        self, monkeypatch: pytest.MonkeyPatch, temp_output_dir: Path
    ) -> None:
        """Si no hay archivos Excel, debe retornar lista vacía."""
        # Monkeypatch input_data_directory para apuntar a un dir vacío
        monkeypatch.setattr(
            "app.utils.input_data.input_data_directory",
            lambda: temp_output_dir,
        )
        
        result = list_excel_filenames()
        
        assert isinstance(result, list)
        assert result == []


class TestResolveSafeExcelInInput:
    """Tests para la función resolve_safe_excel_in_input."""

    def test_resolve_safe_excel_in_input_nombre_vacio_retorna_error(self) -> None:
        """Nombre de archivo vacío debe retornar error."""
        path, error = resolve_safe_excel_in_input("")
        
        assert path is None
        assert error is not None
        assert "selecciona" in error.lower()

    def test_resolve_safe_excel_in_input_path_traversal_retorna_error(self) -> None:
        """Intentar path traversal (../) debe retornar error."""
        path, error = resolve_safe_excel_in_input("../etc/passwd")
        
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()

    def test_resolve_safe_excel_in_input_doble_punto_retorna_error(self) -> None:
        """Archivo con '..' como nombre debe retornar error."""
        path, error = resolve_safe_excel_in_input("..")
        
        assert path is None
        assert error is not None
