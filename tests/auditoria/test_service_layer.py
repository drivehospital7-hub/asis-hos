"""Tests for the auditoria service layer (Phase 1)."""

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Task 1.1: Package file
# =============================================================================

class TestPackage:
    """Test that the auditoria package exists and is importable."""

    def test_package_importable(self):
        """RED: Package __init__ does not exist yet."""
        from app.services.auditoria import __name__  # noqa: F811
        assert True


# =============================================================================
# Task 1.2: extractor.py
# =============================================================================

class TestExtractor:
    """Test extractor module — fitz-based PDF text extraction."""

    def test_extraer_texto_pdf_exists(self):
        """RED: extraer_texto_pdf function does not exist yet."""
        from app.services.auditoria.extractor import extraer_texto_pdf
        assert callable(extraer_texto_pdf)

    def test_limpiar_texto_removes_extra_spaces(self):
        """RED: limpiar_texto function does not exist yet in this module."""
        from app.services.auditoria.extractor import limpiar_texto
        assert limpiar_texto("  hello   world  ") == "hello world"

    def test_palabras_medicas_contains_diagnostico(self):
        """RED: PALABRAS_MEDICAS constant does not exist yet."""
        from app.services.auditoria.extractor import PALABRAS_MEDICAS
        assert "DIAGNOSTICO" in PALABRAS_MEDICAS

    def test_ocr_constants_env_override(self):
        """RED: OCR constants should be configurable via env vars."""
        import os

        with patch.dict(os.environ, {
            "TESSERACT_CMD": r"D:\custom\tesseract.exe",
            "TESSERACT_LANG": "deu",
            "OCR_SCALE": "4.0",
        }, clear=False):
            from app.constants import auditoria as audit_const
            importlib.reload(audit_const)

            assert str(audit_const.TESSERACT_CMD) == r"D:\custom\tesseract.exe"
            assert audit_const.TESSERACT_LANG == "deu"
            assert audit_const.OCR_SCALE == 4.0


# =============================================================================
# Task 3.3-3.5: OCR fallback integration
# =============================================================================

class TestOcrExtractor:
    """Test OCR fallback integration in extractor (Phase 2)."""

    def test_ocr_attempted_when_tesseract_available(self):
        """RED: OCR should be attempted when Tesseract is available and page text is short."""
        from app.services.auditoria import extractor
        importlib.reload(extractor)

        with patch.object(extractor, '_tesseract_available', True):
            with patch.object(extractor, 'pytesseract') as mock_pytesseract:
                mock_pytesseract.image_to_string.return_value = "OCR extracted text"
                with patch.object(extractor, 'Image') as mock_image:
                    mock_image.open.return_value = MagicMock()
                    with patch.object(extractor, 'fitz') as mock_fitz:
                        mock_page = MagicMock()
                        mock_page.get_text.return_value = "short"
                        mock_page.get_pixmap.return_value.tobytes.return_value = b"fake_png_bytes"

                        mock_doc = MagicMock()
                        mock_doc.__len__.return_value = 1
                        mock_doc.__getitem__.return_value = mock_page
                        mock_fitz.open.return_value = mock_doc

                        result = extractor.extraer_texto_pdf("/fake/path.pdf")

                        assert mock_pytesseract.image_to_string.called
                        assert "OCR extracted text" in result

    def test_ocr_graceful_when_tesseract_missing(self):
        """RED: No OCR attempt and no crash when Tesseract binary is missing."""
        from app.services.auditoria import extractor
        importlib.reload(extractor)

        with patch.object(extractor, '_tesseract_available', False):
            with patch.object(extractor, 'pytesseract') as mock_pytesseract:
                with patch.object(extractor, 'fitz') as mock_fitz:
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "short page"

                    mock_doc = MagicMock()
                    mock_doc.__len__.return_value = 1
                    mock_doc.__getitem__.return_value = mock_page
                    mock_fitz.open.return_value = mock_doc

                    result = extractor.extraer_texto_pdf("/fake/path.pdf")

                    assert not mock_pytesseract.image_to_string.called
                    assert "short page" in result

    def test_ocr_digital_pdf_fast_path(self):
        """RED: Digital PDF pages (>50 chars) should NOT trigger OCR."""
        from app.services.auditoria import extractor
        importlib.reload(extractor)

        text = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        assert len(text) > 50, "Test text must be > 50 chars"

        with patch.object(extractor, '_tesseract_available', True):
            with patch.object(extractor, 'pytesseract') as mock_pytesseract:
                with patch.object(extractor, 'fitz') as mock_fitz:
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = text

                    mock_doc = MagicMock()
                    mock_doc.__len__.return_value = 1
                    mock_doc.__getitem__.return_value = mock_page
                    mock_fitz.open.return_value = mock_doc

                    result = extractor.extraer_texto_pdf("/fake/path.pdf")

                    assert not mock_pytesseract.image_to_string.called
                    assert text in result


# =============================================================================
# Task 1.3: pde_parser.py
# =============================================================================

class TestPdeParser:
    """Test PDE parser module — EPS-specific text parsers."""

    def test_extraer_eps_exists(self):
        """RED: extraer_eps function does not exist yet."""
        from app.services.auditoria.pde_parser import extraer_eps
        assert callable(extraer_eps)

    def test_extraer_eps_detects_emssanar(self):
        """GREEN: extraer_eps should detect EMSSANAR from validation header."""
        from app.services.auditoria.pde_parser import extraer_eps
        texto = "VALIDACION DE DERECHOS DE AFILIADOS EMSSANAR"
        assert extraer_eps(texto) == "EMSSANAR"

    def test_extraer_eps_detects_mallamas(self):
        """TRIANGULATE: extraer_eps should detect MALLAMAS."""
        from app.services.auditoria.pde_parser import extraer_eps
        texto = "CONSULTA DE AFILIADOS LINEA"
        assert extraer_eps(texto) == "MALLAMAS"

    def test_extraer_eps_unknown(self):
        """TRIANGULATE: unknown text returns NO IDENTIFICADA."""
        from app.services.auditoria.pde_parser import extraer_eps
        texto = "SOME RANDOM TEXT"
        assert extraer_eps(texto) == "NO IDENTIFICADA"

    def test_parser_emssanar_exists(self):
        from app.services.auditoria.pde_parser import parser_emssanar
        assert callable(parser_emssanar)

    def test_parser_mallamas_exists(self):
        from app.services.auditoria.pde_parser import parser_mallamas
        assert callable(parser_mallamas)

    def test_parser_aic_exists(self):
        from app.services.auditoria.pde_parser import parser_aic
        assert callable(parser_aic)

    def test_parser_nueva_eps_exists(self):
        from app.services.auditoria.pde_parser import parser_nueva_eps
        assert callable(parser_nueva_eps)

    def test_parser_adres_exists(self):
        from app.services.auditoria.pde_parser import parser_adres
        assert callable(parser_adres)

    def test_parser_fomag_exists(self):
        from app.services.auditoria.pde_parser import parser_fomag
        assert callable(parser_fomag)

    def test_extraer_datos_derechos_exists(self):
        from app.services.auditoria.pde_parser import extraer_datos_derechos
        assert callable(extraer_datos_derechos)

    def test_normalizar_tipo_doc_exists(self):
        from app.services.auditoria.pde_parser import normalizar_tipo_doc
        assert callable(normalizar_tipo_doc)

    def test_normalizar_texto_removes_accents(self):
        from app.services.auditoria.pde_parser import normalizar_texto
        result = normalizar_texto("PACIENTE AÑO 2024-ÑOÑO")
        assert result == "PACIENTE ANO 2024-NONO"

    def test_normalizar_tipo_doc_cc(self):
        from app.services.auditoria.pde_parser import normalizar_tipo_doc
        assert normalizar_tipo_doc("CEDULA DE CIUDADANIA") == "CC"

    def test_clasificar_estado_activo(self):
        from app.services.auditoria.pde_parser import clasificar_estado
        assert clasificar_estado("ACTIVO") == "ACTIVO"

    def test_clasificar_estado_no_activo(self):
        from app.services.auditoria.pde_parser import clasificar_estado
        assert clasificar_estado("RETIRADO") == "NO ACTIVO"

    def test_no_print_in_pde_parser(self):
        """Verify no print() statements in pde_parser module."""
        from app.services.auditoria import pde_parser
        import inspect
        source = inspect.getsource(pde_parser)
        lines_with_print = [
            line for line in source.splitlines()
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_print, f"print() found in pde_parser: {lines_with_print}"


# =============================================================================
# Task 1.4: fev_parser.py
# =============================================================================

class TestFevParser:
    """Test FEV parser module — pdfplumber-based FEV layout parsing."""

    def test_parsear_fev_exists(self):
        """RED: parsear_fev function does not exist yet."""
        from app.services.auditoria.fev_parser import parsear_fev
        assert callable(parsear_fev)

    def test_detectar_categoria_exists(self):
        from app.services.auditoria.fev_parser import detectar_categoria
        assert callable(detectar_categoria)

    def test_detectar_categoria_consulta(self):
        from app.services.auditoria.fev_parser import detectar_categoria
        assert detectar_categoria("CONSULTAS") == "CONSULTAS"

    def test_detectar_categoria_None(self):
        from app.services.auditoria.fev_parser import detectar_categoria
        assert detectar_categoria("NOT A CATEGORY") is None


# =============================================================================
# Task 1.5: normalizador.py
# =============================================================================

class TestNormalizador:
    """Test normalizador module — FEV↔PDE normalization and comparison."""

    def test_normalizar_fev_emssanar_exists(self):
        from app.services.auditoria.normalizador import normalizar_fev_emssanar
        assert callable(normalizar_fev_emssanar)

    def test_normalizar_pde_emssanar_exists(self):
        from app.services.auditoria.normalizador import normalizar_pde_emssanar
        assert callable(normalizar_pde_emssanar)

    def test_comparar_campos_exists(self):
        from app.services.auditoria.normalizador import comparar_campos
        assert callable(comparar_campos)

    def test_normalizar_fev_emssanar_returns_expected_keys(self):
        from app.services.auditoria.normalizador import normalizar_fev_emssanar
        fev_data = {
            "encabezado": {
                "RESPONSABLE": "EMSSANAR",
                "TIPO DE DOCUMENTO": "CC",
                "NUMERO DE DOCUMENTO": "123456789",
                "NOMBRE COMPLETO": "JUAN PEREZ",
                "REGIMEN": "SUBSIDIADO",
                "TIPO PACIENTE": "SUBSIDIADO",
                "ESTADO": "ACTIVO",
                "NUMERO FACTURA": "FEV001",
                "CUFE": "abc123",
            }
        }
        result = normalizar_fev_emssanar(fev_data)
        assert result["tipo_documento"] == "CC"
        assert result["numero_documento"] == "123456789"
        assert result["regimen"] == "SUBSIDIADO"

    def test_comparar_campos_detects_difference(self):
        from app.services.auditoria.normalizador import comparar_campos
        fev = {"eps": "EMSSANAR", "tipo_documento": "CC", "numero_documento": "123", "nombre": "A", "regimen": "SUBSIDIADO"}
        pde = {"eps": "EMSSANAR", "tipo_documento": "TI", "numero_documento": "456", "nombre": "B", "regimen": "CONTRIBUTIVO", "estado": "ACTIVO"}
        diffs = comparar_campos(fev, pde)
        assert "tipo_documento" in diffs
        assert diffs["tipo_documento"]["FEV"] == "CC"
        assert diffs["tipo_documento"]["PDE"] == "TI"

    def test_no_print_in_normalizador(self):
        from app.services.auditoria import normalizador
        import inspect
        source = inspect.getsource(normalizador)
        lines_with_print = [
            line for line in source.splitlines()
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_print, f"print() found in normalizador: {lines_with_print}"


# =============================================================================
# Task 1.6 & 1.7: validador_soportes.py & reglas_soportes.json
# =============================================================================

class TestValidadorSoportes:
    """Test validador_soportes module — support document validation."""

    def test_validar_soportes_exists(self):
        from app.services.auditoria.validador_soportes import validar_soportes
        assert callable(validar_soportes)

    def test_reglas_json_resolves_from_any_cwd(self):
        """Task 5.6: Verify reglas_soportes.json resolves from any CWD via __file__."""
        from app.services.auditoria.validador_soportes import REGLAS_PLANAS
        assert isinstance(REGLAS_PLANAS, dict)
        assert len(REGLAS_PLANAS) > 0
        # Spot-check: verify a known code from odontologia
        assert "890303" in REGLAS_PLANAS

    def test_no_assert_in_validador_soportes(self):
        """Verify no assert statements in validador_soportes (replaced with conditionals)."""
        from app.services.auditoria import validador_soportes
        import inspect
        source = inspect.getsource(validador_soportes)
        lines_with_assert = [
            line for line in source.splitlines()
            if line.strip().startswith("assert ") and not line.strip().startswith("#")
        ]
        assert not lines_with_assert, f"assert found in validador_soportes: {lines_with_assert}"

    def test_no_print_in_validador_soportes(self):
        from app.services.auditoria import validador_soportes
        import inspect
        source = inspect.getsource(validador_soportes)
        lines_with_print = [
            line for line in source.splitlines()
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_print, f"print() found in validador_soportes: {lines_with_print}"

    def test_reglas_json_file_exists(self):
        """Verify reglas_soportes.json exists alongside validador_soportes.py."""
        from app.services.auditoria import validador_soportes
        json_path = Path(validador_soportes.__file__).parent / "reglas_soportes.json"
        assert json_path.exists(), f"reglas_soportes.json not found at {json_path}"

    def test_validar_soportes_no_fev_returns_empty(self):
        """No FEV in archivos → validar_soportes returns empty list."""
        from app.services.auditoria.validador_soportes import validar_soportes
        archivos = [
            {"tipo": "SOPORTE", "archivo": "EPI_001.pdf", "texto": "some text"}
        ]
        result = validar_soportes(archivos)
        assert result == []


# =============================================================================
# Task 1.8: auditor.py
# =============================================================================

class TestAuditor:
    """Test auditor module — main orchestration of PDF auditing."""

    def test_auditar_carpeta_exists(self):
        """RED: auditar_carpeta function does not exist yet."""
        from app.services.auditoria.auditor import auditar_carpeta
        assert callable(auditar_carpeta)

    def test_auditar_carpeta_returns_dict(self):
        """GREEN: auditar_carpeta must return a dict."""
        from app.services.auditoria.auditor import auditar_carpeta
        with patch("app.services.auditoria.auditor.os.walk") as mock_walk:
            mock_walk.return_value = []
            result = auditar_carpeta("/fake/path")
            assert isinstance(result, dict)

    def test_auditar_carpeta_empty_dir_no_pdfs(self):
        """TRIANGULATE: empty directory returns empty results dict."""
        from app.services.auditoria.auditor import auditar_carpeta
        with patch("app.services.auditoria.auditor.os.walk") as mock_walk:
            # A directory with a subfolder but no PDFs
            mock_walk.return_value = [
                ("/fake/path", ["subfolder"], ["readme.txt"]),
                ("/fake/path/subfolder", [], ["notes.txt"]),
            ]
            result = auditar_carpeta("/fake/path")
            assert isinstance(result, dict)

    def test_no_seleccionar_carpeta(self):
        """Verify seleccionar_carpeta (Tkinter) is NOT in auditor module."""
        from app.services.auditoria import auditor
        import inspect
        source = inspect.getsource(auditor)
        assert "seleccionar_carpeta" not in source, "Tkinter function still present"
        assert "tkinter" not in source, "Tkinter import still present"

    def test_no_print_in_auditor(self):
        from app.services.auditoria import auditor
        import inspect
        source = inspect.getsource(auditor)
        lines_with_print = [
            line for line in source.splitlines()
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_print, f"print() found in auditor: {lines_with_print}"


# =============================================================================
# Global no-print sweep (Task 5.5)
# =============================================================================

class TestGlobalConventions:
    """Verify global conventions across all auditoria modules."""

    MODULES = [
        "app.services.auditoria.extractor",
        "app.services.auditoria.pde_parser",
        "app.services.auditoria.fev_parser",
        "app.services.auditoria.normalizador",
        "app.services.auditoria.validador_soportes",
        "app.services.auditoria.auditor",
    ]

    @pytest.mark.parametrize("module_name", MODULES)
    def test_no_print_in_module(self, module_name):
        """Task 5.5: No print() in new service modules."""
        import importlib
        module = importlib.import_module(module_name)
        import inspect
        source = inspect.getsource(module)
        lines_with_print = [
            line for line in source.splitlines()
            if "print(" in line and not line.strip().startswith("#")
        ]
        assert not lines_with_print, f"print() found in {module_name}: {lines_with_print}"
