"""Tests para la capa de File Size (PR 1).

Verifica:
- MAX_EXCEL_UPLOAD_SIZE_MB existe como constante
- MAX_CONTENT_LENGTH en config/prod.py es coherente
- save_temp_excel() rechaza archivos que exceden el límite
- Flask devuelve 413 para requests > MAX_CONTENT_LENGTH
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Phase 1: Foundation — constantes
# =============================================================================


class TestMaxExcelUploadSizeMbConstant:
    """MAX_EXCEL_UPLOAD_SIZE_MB debe ser importable y tener el valor correcto."""

    def test_max_excel_upload_size_mb_is_importable(self) -> None:
        """RED: MAX_EXCEL_UPLOAD_SIZE_MB debe importarse desde app.constants."""
        # Esta importación fallará hasta que se agregue la constante
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB  # noqa: F811

        assert MAX_EXCEL_UPLOAD_SIZE_MB == 100

    def test_max_excel_upload_size_mb_is_positive_int(self) -> None:
        """RED: El valor debe ser un entero positivo."""
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB  # noqa: F811

        assert isinstance(MAX_EXCEL_UPLOAD_SIZE_MB, int)
        assert MAX_EXCEL_UPLOAD_SIZE_MB > 0


class TestMaxContentLengthProdConfig:
    """MAX_CONTENT_LENGTH en config/prod.py debe ser coherente."""

    def test_max_content_length_is_set_in_prod_config(self) -> None:
        """RED: MAX_CONTENT_LENGTH debe estar configurado en 100MB."""
        # Importamos desde config.prod para verificar que existe
        import importlib
        import config.prod as prod_config

        importlib.reload(prod_config)

        assert prod_config.ProdConfig.MAX_CONTENT_LENGTH == 100 * 1024 * 1024

    def test_max_content_length_matches_size_constant(self) -> None:
        """REFACTOR: MAX_CONTENT_LENGTH debe ser coherente con MAX_EXCEL_UPLOAD_SIZE_MB."""
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB

        import importlib
        import config.prod as prod_config

        importlib.reload(prod_config)

        expected_max_content_length = MAX_EXCEL_UPLOAD_SIZE_MB * 1024 * 1024
        assert prod_config.ProdConfig.MAX_CONTENT_LENGTH == expected_max_content_length


# =============================================================================
# Phase 2: File Size Layer — save_temp_excel validation
# =============================================================================


class TestSaveTempExcelSizeValidation:
    """save_temp_excel debe validar tamaño de archivo contra MAX_EXCEL_UPLOAD_SIZE_MB."""

    def test_save_temp_excel_rejects_oversized_file(self) -> None:
        """RED: Archivo > MAX_EXCEL_UPLOAD_SIZE_MB debe ser rechazado con error del spec."""
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB
        from app.utils.input_data import save_temp_excel

        # Crear un mock de file_storage que reporte un tamaño superior al límite
        oversized_bytes = (MAX_EXCEL_UPLOAD_SIZE_MB + 1) * 1024 * 1024

        mock_file = MagicMock()
        mock_file.filename = "facturas_grandes.xlsx"
        mock_file.tell.return_value = oversized_bytes
        mock_file.save = MagicMock()

        path, error = save_temp_excel(mock_file)

        assert path is None, "No debe devolver path para archivo muy grande"
        assert error is not None, "Debe devolver mensaje de error"
        # El mensaje de error debe coincidir exactamente con el formato del spec R1
        expected_message = f"Archivo excede el tamaño máximo de {MAX_EXCEL_UPLOAD_SIZE_MB}MB"
        assert error == expected_message, f"Error debe coincidir con formato del spec: {expected_message!r}"

    def test_save_temp_excel_accepts_file_within_limit(self) -> None:
        """TRIANGULATE: Archivo dentro del límite debe guardarse normalmente."""
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB
        from app.utils.input_data import save_temp_excel

        # Archivo de 1MB — muy por debajo del límite
        safe_bytes = 1 * 1024 * 1024

        mock_file = MagicMock()
        mock_file.filename = "facturas_seguras.xlsx"
        mock_file.tell.return_value = safe_bytes

        # Simular save exitoso
        actual_path = None

        def fake_save(dest):
            nonlocal actual_path
            actual_path = dest

        mock_file.save = fake_save

        with patch("app.utils.input_data.temp_upload_directory") as mock_temp_dir:
            with patch("app.utils.input_data.uuid.uuid4") as mock_uuid:
                mock_temp_dir.return_value = Path("/tmp/uploads")
                mock_uuid.return_value.hex = "abc123"
                path, error = save_temp_excel(mock_file)

        # Debe guardar exitosamente
        assert error is None, f"No debe haber error: {error}"
        assert path is not None, "Debe devolver un Path"
        assert "abc123" in str(path), "Path debe contener el UUID generado"

    def test_save_temp_excel_rejects_at_boundary(self) -> None:
        """TRIANGULATE: Archivo exactamente en el límite debe ser aceptado."""
        from app.constants import MAX_EXCEL_UPLOAD_SIZE_MB
        from app.utils.input_data import save_temp_excel

        # Archivo exactamente del tamaño límite
        boundary_bytes = MAX_EXCEL_UPLOAD_SIZE_MB * 1024 * 1024

        mock_file = MagicMock()
        mock_file.filename = "boundary.xlsx"
        mock_file.tell.return_value = boundary_bytes
        mock_file.save = MagicMock()

        with patch("app.utils.input_data.temp_upload_directory") as mock_temp_dir:
            with patch("app.utils.input_data.uuid.uuid4") as mock_uuid:
                mock_temp_dir.return_value = Path("/tmp/uploads")
                mock_uuid.return_value.hex = "def456"
                path, error = save_temp_excel(mock_file)

        # Archivo en el límite debe guardarse (el check es >, no >=)
        assert error is None, f"No debe haber error para archivo en el límite: {error}"
        assert path is not None, "Debe devolver un Path"


# =============================================================================
# Phase 2: File Size Layer — Flask MAX_CONTENT_LENGTH prod gate
# =============================================================================


class TestFlaskMaxContentLengthGate:
    """Flask MAX_CONTENT_LENGTH debe retornar 413 para requests que exceden el límite."""

    def _authenticate(self, app_client) -> None:
        """Establece sesión autenticada para sortear before_request."""
        with app_client.session_transaction() as sess:
            sess["ce_authenticated"] = True
            sess["username"] = "test"

    def test_flask_returns_413_when_content_length_exceeds_limit(
        self, app_client
    ) -> None:
        """RED: Flask debe retornar 413 cuando Content-Length > MAX_CONTENT_LENGTH."""
        from io import BytesIO

        self._authenticate(app_client)

        # Configurar un límite bajo específico para el test
        # Suficiente para overhead de multipart + datos pequeños
        test_limit = 10 * 1024  # 10KB
        app_client.application.config["MAX_CONTENT_LENGTH"] = test_limit

        # Datos que exceden el límite
        oversized_data = b"x" * (test_limit + 1)

        response = app_client.post(
            "/odontologia/",
            data={"file": (BytesIO(oversized_data), "test.xlsx")},
        )

        assert response.status_code == 413, (
            f"Flask debe retornar 413 para Content-Length > MAX_CONTENT_LENGTH, "
            f"obtuvo {response.status_code} — contenido mayor a {test_limit} bytes"
        )

    def test_flask_accepts_request_within_content_length_limit(
        self, app_client
    ) -> None:
        """TRIANGULATE: Request dentro del límite debe ser aceptado (no 413)."""
        from io import BytesIO

        self._authenticate(app_client)

        # Usar un límite generoso que cubra el overhead multipart
        test_limit = 100 * 1024  # 100KB
        app_client.application.config["MAX_CONTENT_LENGTH"] = test_limit

        # Datos pequeños (1KB) dentro del límite
        safe_data = b"x" * 1024

        response = app_client.post(
            "/odontologia/",
            data={"file": (BytesIO(safe_data), "test.xlsx")},
        )

        # El endpoint de odontologia espera datos reales — puede retornar
        # 200, 400 o 500, pero NO 413
        assert response.status_code != 413, (
            "Request dentro del límite no debe ser rechazado con 413"
        )

    def test_prod_config_has_100mb_limit(self) -> None:
        """GREEN: ProdConfig debe tener MAX_CONTENT_LENGTH = 100MB."""
        import importlib

        import config.prod as prod_config

        importlib.reload(prod_config)

        assert prod_config.ProdConfig.MAX_CONTENT_LENGTH == 100 * 1024 * 1024
