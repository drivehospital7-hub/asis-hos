"""PDF text extraction using PyMuPDF (fitz)."""

import logging

import fitz

logger = logging.getLogger(__name__)


def extraer_texto(ruta_pdf: str) -> tuple[str, str | None]:
    """Extrae texto plano de un PDF usando PyMuPDF.

    Args:
        ruta_pdf: Ruta al archivo PDF.

    Returns:
        Tupla (texto, error):
        - texto: texto extraído, o "" si no se pudo leer.
        - error: None si OK, mensaje de error si hubo excepción.
    """
    try:
        doc = fitz.open(ruta_pdf)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        doc.close()
        return texto.strip(), None
    except Exception as e:
        logger.warning("No se pudo extraer texto de: %s", ruta_pdf, exc_info=True)
        return "", f"Error al leer PDF: {e!s}"
