"""PDF text extraction using PyMuPDF (fitz) with optional OCR fallback.

OCR fallback by page: if fitz.get_text() returns ≤ 50 chars (scanned page)
and Tesseract binary is available, render the page with fitz at OCR_SCALE
and run pytesseract.image_to_string().

Copied from AUDITORA/extractor.py, keeping only:
- fitz import
- PALABRAS_MEDICAS
- limpiar_texto()
- extraer_texto_pdf() (with OCR fallback restored)
"""

import io
import logging
import os

import fitz
from PIL import Image

import pytesseract
from app.constants.auditoria import TESSERACT_CMD, TESSERACT_LANG, OCR_SCALE

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
_tesseract_available = os.path.exists(TESSERACT_CMD)
if not _tesseract_available:
    logger.warning("Tesseract no encontrado en %s. OCR desactivado.", TESSERACT_CMD)

# ================== FILTROS ==================

PALABRAS_MEDICAS = [
    "DIAGNOSTICO", "DX", "TRIAGE", "ENFERMERIA", "EVOLUCION",
    "MEDICO", "MEDICINA", "PACIENTE INGRESA", "SIGNOS VITALES",
    "TRATAMIENTO", "HOSPITALIZACION", "FORMULA MEDICA"
]


def limpiar_texto(t):
    return " ".join(t.split())


# ================== LECTOR PDF (con OCR) ==================

def extraer_texto_pdf(ruta, tipo_documento=None):
    """Extract text from a PDF using PyMuPDF + optional OCR fallback.

    Tries fitz.get_text() first per page. If a page has ≤ 50 characters
    (scanned page) and Tesseract is available, renders the page at OCR_SCALE
    and applies pytesseract.image_to_string(). If Tesseract is unavailable,
    returns the original fitz text without exception.

    Args:
        ruta: Path to the PDF file.
        tipo_documento: Optional hint ("PDE", "SOPORTE", etc.) to limit pages.

    Returns:
        Cleaned text string, or "" on failure.
    """
    texto_total = ""

    try:
        doc = fitz.open(ruta)

        # =====================================
        # RECORRER TODAS LAS PAGINAS
        # =====================================
        # Sin OCR leer páginas con fitz es rápido, leemos todas.
        # Si ya encontramos datos relevantes para PDE, cortamos antes.
        pde_completo = False

        for num_pagina in range(len(doc)):
            page = doc[num_pagina]
            texto = page.get_text()

            # OCR fallback por página: si el texto extraído es muy corto
            # (PDF escaneado), renderizar con fitz y aplicar OCR
            if len(texto.strip()) > 50:
                texto_total += "\n" + texto
                continue
            if _tesseract_available:
                mat = fitz.Matrix(OCR_SCALE, OCR_SCALE)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                imagen = Image.open(io.BytesIO(img_bytes))
                texto_ocr = pytesseract.image_to_string(imagen, lang=TESSERACT_LANG)
                texto_total += "\n" + texto_ocr
            else:
                texto_total += "\n" + texto

            # Para PDE: si ya acumulamos suficiente texto con datos relevantes,
            # cortamos para no leer páginas de más (historia clínica, etc.)
            if tipo_documento == "PDE" and len(texto_total) > 200:
                texto_upper = texto_total.upper()
                if (
                    "VALIDACION DE DERECHOS" in texto_upper
                    and "IDENTIFICACION" in texto_upper
                ) or (
                    "CONSULTA DE AFILIADOS" in texto_upper
                    and "DOCUMENTO" in texto_upper
                ) or (
                    "FECHA/HORA CONSULTA" in texto_upper
                    and "IDENTIFICACION" in texto_upper
                ) or (
                    "CERTIFICADO DE AFILIACION" in texto_upper
                    and "IDENTIFICACION" in texto_upper
                ):
                    logger.debug("Datos PDE completos encontrados en página %d, cortando", num_pagina + 1)
                    pde_completo = True
                    break

        doc.close()

    except Exception as e:
        logger.exception("Error procesando %s: %s", ruta, e)
        return ""

    return limpiar_texto(texto_total)
