"""Tests for busqueda_pdf.buscador — buscar_en_carpeta()."""

from unittest.mock import patch, MagicMock

import pytest

from app.services.busqueda_pdf.buscador import buscar_en_carpeta


def test_buscar_sin_pdfs(tmp_path):
    """Empty folder → resultados vacío, resumen, sin errores."""
    result = buscar_en_carpeta(str(tmp_path), "Conductor", "Automóvil", {})

    assert result["resultados"] == []
    assert result["resumen"]["pdfs_procesados"] == 0
    assert result["resumen"]["pdfs_con_hallazgos"] == 0
    assert result["resumen"]["pdfs_sin_texto"] == 0
    assert result["resumen"]["pdfs_error"] == 0
    assert result["errores"] == []


def test_buscar_terminos_encontrados(tmp_path):
    """PDFs with matching terms report them in resultados."""
    pdf_file = tmp_path / "informe.pdf"
    pdf_file.write_text("", encoding="utf-8")

    texto_con_terminos = (
        "El día del accidente el Peatón fue trasladado en una Buseta "
        "de la empresa de transportes. El conductor manifestó que..."
    )

    mock_extractor = MagicMock(return_value=(texto_con_terminos, None))

    with (
        patch("app.services.busqueda_pdf.buscador.extraer_texto", mock_extractor),
        patch("app.services.busqueda_pdf.buscador.os.listdir", return_value=["informe.pdf"]),
    ):
        result = buscar_en_carpeta(str(tmp_path), "Conductor", "Automóvil", {})

    assert len(result["resultados"]) == 1
    assert result["resultados"][0]["pdf"] == "informe.pdf"
    assert result["resumen"]["pdfs_procesados"] == 1
    assert result["resumen"]["pdfs_con_hallazgos"] == 1

    terminos = {t["termino"] for t in result["resultados"][0]["terminos"]}
    assert "Peatón" in terminos  # from other condiciones
    assert "Buseta" in terminos  # from other transportes

    # Selected term NOT in results
    assert "Conductor" not in terminos
    assert "Automóvil" not in terminos


def test_buscar_termino_seleccionado_ignorado(tmp_path):
    """Selected condicion and transporte must NOT appear in resultados."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_text("", encoding="utf-8")

    texto = "El Conductor circulaba en un Automóvil por la vía principal."

    mock_extractor = MagicMock(return_value=(texto, None))

    with (
        patch("app.services.busqueda_pdf.buscador.extraer_texto", mock_extractor),
        patch("app.services.busqueda_pdf.buscador.os.listdir", return_value=["doc.pdf"]),
    ):
        result = buscar_en_carpeta(str(tmp_path), "Conductor", "Automóvil", {})

    # The PDF had content but only the selected terms — no results
    assert len(result["resultados"]) == 0
    assert result["resumen"]["pdfs_procesados"] == 1
    assert result["resumen"]["pdfs_con_hallazgos"] == 0


def test_buscar_con_sinonimos(tmp_path):
    """Custom synonyms are searched and matched."""
    pdf_file = tmp_path / "reporte.pdf"
    pdf_file.write_text("", encoding="utf-8")

    texto = "El acompañante resultó ileso en el accidente."

    mock_extractor = MagicMock(return_value=(texto, None))

    with (
        patch("app.services.busqueda_pdf.buscador.extraer_texto", mock_extractor),
        patch("app.services.busqueda_pdf.buscador.os.listdir", return_value=["reporte.pdf"]),
        patch("app.services.busqueda_pdf.buscador.merge_sinonimos", return_value={"Ocupante": ["Acompañante", "Pasajero"]}),
    ):
        result = buscar_en_carpeta(str(tmp_path), "Conductor", "Automóvil", {"Ocupante": ["Acompaniante"]})

    assert len(result["resultados"]) == 1
    terminos_encontrados = result["resultados"][0]["terminos"]
    terminos_texto_lower = [t["termino"].lower() for t in terminos_encontrados]
    assert "acompañante" in terminos_texto_lower


def test_buscar_ignora_mayusculas_y_tildes(tmp_path):
    """Search must be case-insensitive AND accent-insensitive.

    'Conductor', 'CONDUCTOR', y 'Conductór' deben matchear el mismo término.
    """
    pdf_file = tmp_path / "informe.pdf"
    pdf_file.write_text("", encoding="utf-8")

    texto = (
        "El CONDUCTOR manejaba a alta velocidad. "
        "El peatón andaba distraído. "
        "También se menciona un Peatón con acento. "
        "Y por último CONDUCTOR en mayúscula."
    )

    mock_extractor = MagicMock(return_value=(texto, None))

    with (
        patch("app.services.busqueda_pdf.buscador.extraer_texto", mock_extractor),
        patch("app.services.busqueda_pdf.buscador.os.listdir", return_value=["informe.pdf"]),
    ):
        result = buscar_en_carpeta(str(tmp_path), "Conductór", "Automóvil", {})

    # Peatón should be found (other condición, case-insensitive + accent)
    assert len(result["resultados"]) == 1
    terminos = {t["termino"] for t in result["resultados"][0]["terminos"]}
    assert "Peatón" in terminos or "peatón" in terminos or "PEATÓN" in terminos


def test_buscar_pdf_error_no_detiene_batch(tmp_path):
    """A corrupt PDF should not stop processing remaining PDFs."""
    pdf1 = tmp_path / "bueno.pdf"
    pdf1.write_text("", encoding="utf-8")
    pdf2 = tmp_path / "malo.pdf"
    pdf2.write_text("", encoding="utf-8")

    mock_extractor = MagicMock()
    mock_extractor.side_effect = [
        ("Texto con Peatón", None),  # pdf1 works
        ("", "Error al leer PDF: Corrupt"),  # pdf2 corrupt → error
    ]

    with (
        patch("app.services.busqueda_pdf.buscador.extraer_texto", mock_extractor),
        patch("app.services.busqueda_pdf.buscador.os.listdir", return_value=["bueno.pdf", "malo.pdf"]),
    ):
        result = buscar_en_carpeta(str(tmp_path), "Conductor", "Automóvil", {})

    assert result["resumen"]["pdfs_procesados"] == 2
    assert result["resumen"]["pdfs_con_hallazgos"] == 1  # only pdf1 had terms
    assert result["resumen"]["pdfs_sin_texto"] == 0  # not empty, it errored
    assert result["resumen"]["pdfs_error"] == 1  # pdf2 corrupt
    assert len(result["errores"]) == 1
    assert "malo.pdf" in result["errores"][0]
