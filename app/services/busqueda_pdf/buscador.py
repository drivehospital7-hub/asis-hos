"""Orquestador de búsqueda de términos en PDFs."""

import logging
import os
import re
import unicodedata

from app.constants.busqueda_pdf import CONDICIONES, TRANSPORTES
from app.services.busqueda_pdf.extractor import extraer_texto
from app.services.busqueda_pdf.sinonimos import merge_sinonimos

logger = logging.getLogger(__name__)

_CONTEXTO_RADIO = 40


def _normalizar(s: str) -> str:
    """Normaliza texto: minúsculas + sin tildes/diacríticos."""
    nfkd = unicodedata.normalize("NFKD", s)
    return nfkd.encode("ascii", "ignore").decode("ascii").lower()


def _crear_mapping(texto: str) -> list[int]:
    """Mapa de posición normalizada → posición original.

    Cada caracter en texto_original puede expandirse (p.ej. 'é' → 'e')
    o contraerse (p.ej. 'ñ' → 'n') tras normalizar. Este mapping permite
    convertir coordenadas del texto normalizado a coordenadas originales.
    """
    mapping: list[int] = []
    for i, ch in enumerate(texto):
        nfkd = unicodedata.normalize("NFKD", ch)
        ascii_len = len(nfkd.encode("ascii", "ignore"))
        mapping.extend([i] * ascii_len)
    return mapping


def _generar_terminos_busqueda(condicion: str, transporte: str, sinonimos: dict) -> list[dict]:
    """Genera lista de términos a buscar, excluyendo el seleccionado.

    Tanto las condiciones/transportes como las claves de sinónimos se
    normalizan (minúsculas + sin tildes) para la comparación, de modo
    que "CONDUCTOR", "Conductór" y "Conductor" sean equivalentes.

    Returns:
        Lista de dicts con {'termino': str, 'tipo': 'condicion'|'transporte'}.
    """
    terminos = []

    # Indexar sinónimos por clave normalizada
    sinonimos_norm = {_normalizar(k): v for k, v in sinonimos.items()}
    cond_norm = _normalizar(condicion)
    transp_norm = _normalizar(transporte)

    for c in CONDICIONES:
        c_norm = _normalizar(c)
        if c_norm != cond_norm:
            terminos.append({"termino": c, "tipo": "condicion"})
            for sin in sinonimos_norm.get(c_norm, []):
                terminos.append({"termino": sin, "tipo": "condicion"})

    for t in TRANSPORTES:
        t_norm = _normalizar(t)
        if t_norm != transp_norm:
            terminos.append({"termino": t, "tipo": "transporte"})
            for sin in sinonimos_norm.get(t_norm, []):
                terminos.append({"termino": sin, "tipo": "transporte"})

    return terminos


def _extraer_contexto(texto: str, match_start: int, match_end: int) -> str:
    """Extrae ~40 caracteres alrededor del match."""
    inicio = max(0, match_start - _CONTEXTO_RADIO)
    fin = min(len(texto), match_end + _CONTEXTO_RADIO)

    contexto = texto[inicio:fin]
    # Reemplazar saltos de línea por espacios
    contexto = " ".join(contexto.split())
    return contexto.strip()


def buscar_en_carpeta(
    ruta: str, condicion: str, transporte: str, sinonimos_custom: dict | None
) -> dict:
    """Busca términos de otras condiciones/transportes en PDFs de la carpeta.

    Args:
        ruta: Ruta a la carpeta con PDFs.
        condicion: Condición seleccionada por el usuario.
        transporte: Transporte seleccionado por el usuario.
        sinonimos_custom: Dict opcional de sinónimos customizados.

    Returns:
        Dict con resultados, resumen y errores.
    """
    sinonimos = merge_sinonimos(sinonimos_custom)
    terminos_a_buscar = _generar_terminos_busqueda(condicion, transporte, sinonimos)

    resultados = []
    pdfs_procesados = 0
    pdfs_con_hallazgos = 0
    pdfs_sin_texto = 0
    pdfs_error = 0
    errores = []

    try:
        archivos = os.listdir(ruta)
    except OSError as e:
        logger.exception("Error listando directorio: %s", ruta)
        return {
            "resultados": [],
            "resumen": {"pdfs_procesados": 0, "pdfs_con_hallazgos": 0, "pdfs_sin_texto": 0, "pdfs_error": 0},
            "errores": [f"Error al listar directorio: {e!s}"],
        }

    pdfs = [f for f in archivos if f.lower().endswith(".pdf")]

    if not pdfs:
        return {
            "resultados": [],
            "resumen": {"pdfs_procesados": 0, "pdfs_con_hallazgos": 0, "pdfs_sin_texto": 0, "pdfs_error": 0},
            "errores": [],
        }

    for pdf_name in pdfs:
        pdfs_procesados += 1
        ruta_completa = os.path.join(ruta, pdf_name)

        texto, error = extraer_texto(ruta_completa)

        if error:
            pdfs_error += 1
            errores.append(f"{pdf_name}: {error}")
            continue

        if not texto:
            pdfs_sin_texto += 1
            continue

        # Normalización: una vez por PDF (ignora mayúsculas + tildes)
        texto_norm = _normalizar(texto)
        mapping = _crear_mapping(texto)

        def _pos_orig(norm_pos: int) -> int:
            if norm_pos >= len(mapping):
                return len(texto)
            return mapping[norm_pos]

        terminos_encontrados = []
        for term_info in terminos_a_buscar:
            termino = term_info["termino"]
            termino_norm = _normalizar(termino)

            if termino_norm not in texto_norm:
                continue

            pattern = re.compile(re.escape(termino_norm))
            for match in pattern.finditer(texto_norm):
                start_orig = _pos_orig(match.start())
                end_orig = _pos_orig(match.end() - 1) + 1
                match_text = texto[start_orig:end_orig]
                contexto = _extraer_contexto(texto, start_orig, end_orig)
                terminos_encontrados.append({
                    "termino": match_text,
                    "tipo": term_info["tipo"],
                    "contexto": contexto,
                })

        if terminos_encontrados:
            pdfs_con_hallazgos += 1
            resultados.append({
                "pdf": pdf_name,
                "ruta_completa": ruta_completa,
                "terminos": terminos_encontrados,
            })

    return {
        "resultados": resultados,
        "resumen": {
            "pdfs_procesados": pdfs_procesados,
            "pdfs_con_hallazgos": pdfs_con_hallazgos,
            "pdfs_sin_texto": pdfs_sin_texto,
            "pdfs_error": pdfs_error,
        },
        "errores": errores,
    }
