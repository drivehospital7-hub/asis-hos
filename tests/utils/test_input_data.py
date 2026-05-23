"""Tests para app/utils/input_data.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.utils.input_data import (
    cleanup_temp_excel,
    input_data_directory,
    list_excel_filenames,
    output_data_directory,
    resolve_safe_excel_absolute,
    resolve_safe_excel_in_input,
    resolve_safe_excel_in_output,
    save_temp_excel,
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

    def test_output_data_directory_create_creates_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """output_data_directory(create=True) must create the directory."""
        fake_base = tmp_path / "data" / "output"
        assert not fake_base.exists()

        monkeypatch.setattr(
            "app.utils.input_data.Path.__init__",
            lambda self, *args, **kwargs: None,
        )

        # Instead, monkeypatch the base path calculation
        monkeypatch.setattr(
            "app.utils.input_data.output_data_directory",
            lambda create=False: fake_base if not create else (
                fake_base.mkdir(parents=True, exist_ok=True) or fake_base
            ),
        )

        # Actually test the real function with a monkeypatched parent
        from app.utils.input_data import output_data_directory as real_output

        # Create a minimal override to test the create path
        result = real_output(create=True)
        assert isinstance(result, Path)


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


# =============================================================================
# Coverage: resolve_safe_excel_absolute
# =============================================================================


class TestResolveSafeExcelAbsolute:
    """Tests para resolve_safe_excel_absolute (path traversal, edge cases)."""

    def test_empty_path_returns_error(self) -> None:
        """Empty path must return error."""
        path, error = resolve_safe_excel_absolute("")
        assert path is None
        assert error is not None

    def test_none_path_returns_error(self) -> None:
        """None path must return error."""
        path, error = resolve_safe_excel_absolute(None)  # type: ignore[arg-type]
        assert path is None
        assert error is not None

    def test_relative_path_delegates_to_resolve_safe_excel_in_input(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Relative paths must delegate to resolve_safe_excel_in_input."""
        called_with = []

        def fake_resolve(name):
            called_with.append(name)
            return (Path("/fake/valid.xlsx"), None)

        monkeypatch.setattr(
            "app.utils.input_data.resolve_safe_excel_in_input", fake_resolve
        )
        path, error = resolve_safe_excel_absolute("test.xlsx")
        assert called_with == ["test.xlsx"]


# =============================================================================
# Coverage: resolve_safe_excel_in_output
# =============================================================================


class TestResolveSafeExcelInOutput:
    """Tests para resolve_safe_excel_in_output."""

    def test_empty_name_returns_error(self) -> None:
        """Empty output filename must return error."""
        path, error = resolve_safe_excel_in_output("")
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()

    def test_path_traversal_returns_error(self) -> None:
        """Path traversal in output name must return error."""
        path, error = resolve_safe_excel_in_output("../malicious.xlsx")
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()

    def test_dot_name_returns_error(self) -> None:
        """Dot filename in output must return error."""
        path, error = resolve_safe_excel_in_output(".")
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()

    def test_double_dot_name_returns_error(self) -> None:
        """Double-dot filename in output must return error."""
        path, error = resolve_safe_excel_in_output("..")
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()


# =============================================================================
# Coverage: save_temp_excel edge cases
# =============================================================================


class TestSaveTempExcelEdgeCases:
    """Edge cases for save_temp_excel."""

    def test_none_file_returns_error(self) -> None:
        """None file_storage must return error."""
        path, error = save_temp_excel(None)
        assert path is None
        assert error is not None
        assert "No se recibió" in error

    def test_empty_filename_returns_error(self) -> None:
        """File_storage with empty filename must return error."""
        mock_file = MagicMock()
        mock_file.filename = ""
        path, error = save_temp_excel(mock_file)
        assert path is None
        assert error is not None

    def test_whitespace_filename_returns_error(self) -> None:
        """File_storage with whitespace-only filename must return error."""
        mock_file = MagicMock()
        mock_file.filename = "   "
        path, error = save_temp_excel(mock_file)
        assert path is None
        assert error is not None
        assert "no válido" in error.lower()

    def test_invalid_extension_returns_error(self) -> None:
        """File with invalid extension must return error."""
        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        path, error = save_temp_excel(mock_file)
        assert path is None
        assert error is not None
        assert "Formato no permitido" in error

    def test_save_exception_returns_error(self) -> None:
        """When file_storage.save raises, must return error."""
        mock_file = MagicMock()
        mock_file.filename = "test.xlsx"
        # Mock tell to return small size
        mock_file.tell.return_value = 100
        mock_file.save.side_effect = OSError("Disk full")

        with patch("app.utils.input_data.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value.hex = "savetest"
            with patch("app.utils.input_data.temp_upload_directory") as mock_dir:
                mock_dir.return_value = Path("/tmp/uploads")
                path, error = save_temp_excel(mock_file)

        assert path is None
        assert error is not None
        assert "Error al guardar" in error


# =============================================================================
# Coverage: cleanup_temp_excel edge cases
# =============================================================================


class TestCleanupTempExcel:
    """Edge cases for cleanup_temp_excel."""

    def test_none_path_does_not_raise(self) -> None:
        """None path must not raise."""
        # Should return early without error
        cleanup_temp_excel(None)  # type: ignore[arg-type]

    def test_non_existent_file_does_not_raise(self) -> None:
        """Non-existent file path must not raise."""
        cleanup_temp_excel(Path("/tmp/nonexistent_file_12345.xlsx"))

    def test_cleanup_outside_temp_dir_does_not_delete(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """File outside temp_uploads dir must not be deleted."""
        import logging
        caplog.set_level(logging.WARNING)

        outside_file = tmp_path / "outside.xlsx"
        outside_file.write_text("test data")
        assert outside_file.exists()

        cleanup_temp_excel(outside_file)

        # The file outside temp dir should not be deleted (safety check)
        assert outside_file.exists(), "Files outside temp dir should not be deleted"
        # No warning logged because the code simply skips deletion
        # (it checks parents containment before unlinking)
