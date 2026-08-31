"""Tests for busqueda_pdf.extractor — extraer_texto()."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.busqueda_pdf.extractor import extraer_texto


def test_extraer_texto_pdf_valido():
    """PDF with selectable text returns (texto, None)."""
    mock_doc = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.get_text.return_value = "Texto de prueba página 1\n"
    mock_page2 = MagicMock()
    mock_page2.get_text.return_value = "Texto de prueba página 2\n"
    mock_doc.__iter__.return_value = [mock_page1, mock_page2]
    mock_doc.__len__.return_value = 2

    with patch("app.services.busqueda_pdf.extractor.fitz.open", return_value=mock_doc):
        texto, error = extraer_texto("ruta/test.pdf")

    assert "Texto de prueba página 1" in texto
    assert "Texto de prueba página 2" in texto
    assert error is None


def test_extraer_texto_pdf_vacio():
    """PDF with no text returns ("", None)."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""
    mock_doc.__iter__.return_value = [mock_page]
    mock_doc.__len__.return_value = 1

    with patch("app.services.busqueda_pdf.extractor.fitz.open", return_value=mock_doc):
        texto, error = extraer_texto("ruta/vacio.pdf")

    assert texto == ""
    assert error is None


def test_extraer_texto_error():
    """When fitz.open raises an exception → returns ("", error_msg)."""
    with patch("app.services.busqueda_pdf.extractor.fitz.open", side_effect=Exception("Corrupt PDF")):
        texto, error = extraer_texto("ruta/corrupto.pdf")

    assert texto == ""
    assert error is not None
    assert "Corrupt PDF" in error
