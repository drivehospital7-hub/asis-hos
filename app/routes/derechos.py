import logging
import os
import re

from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

derechos_bp = Blueprint("derechos", __name__)

# Intentar importar extractor de PDFs
try:
    from app.services.derechos_extractor import (
        procesar_carpeta_derechos,
        extraer_texto_pdf,
        extraer_datos_emssanar,
        validar_pdf_por_carpeta
    )
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    logger.warning("Extractor de PDFs no disponible")

# Regex: PDE como sufijo antes del .pdf (con o sin underscore)
# ✅ PDE.pdf, archivo_PDE.pdf, CAP447148_PDE.pdf
# ❌ 112PDE.pdf, documento_PDE_2024.pdf
PATRON_PDE = re.compile(r'(_?PDE)\.pdf$', re.IGNORECASE)


def buscar_archivos_pde(ruta_base, extraer_datos: bool = True):
    """
    Busca recursivamente archivos PDF con patrón PDE.
    
    Args:
        ruta_base: Ruta raíz donde buscar
        extraer_datos: Si True, extrae datos de cada PDF (requiere pypdf)
    
    Returns:
        Estructura jerárquica con PDFs y sus datos:
        {
            "CAP447148": {
                "archivos": ["PDE.pdf"],
                "datos": {...} o None si extraer_datos=False
            }
        }
    """
    estructura = {}

    for root, dirs, files in os.walk(ruta_base):
        # Filtrar solo archivos PDF con patrón PDE
        archivos_pde = [f for f in files if PATRON_PDE.match(f)]

        if archivos_pde:
            # Obtener ruta relativa desde la carpeta base
            rel_path = os.path.relpath(root, ruta_base)
            partes = rel_path.split(os.sep)
            
            # Nombre de la carpeta (último nivel)
            nombre_carpeta = partes[-1] if partes else "Raíz"

            # Si es raíz, usar el nombre de la carpeta como clave
            if len(partes) == 1 and partes[0] == ".":
                nombre_carpeta = os.path.basename(root)
            
            # Extraer datos de cada PDF si está disponible
            datos_carpeta = None
            if extraer_datos and EXTRACTOR_AVAILABLE:
                datos_carpeta = procesar_carpeta_derechos(root)
            
            estructura[nombre_carpeta] = {
                "archivos": sorted(archivos_pde),
                "ruta": root,
                "datos": datos_carpeta
            }

    return estructura


@derechos_bp.get("/derechos")
def derechos_page():
    """Pagina principal del modulo Derechos."""
    return render_template("derechos.html")


@derechos_bp.get("/texto")
def derechos_texto():
    """
    Devuelve el texto RAW de un PDF para debugging.
    Útil para ver cómo viene el texto y entender la estructura.
    
    URL:
    http://localhost:5000/derechos/texto
    """
    # Ruta hardcodeada para debug
    RUTA_DEBUG = "/home/papsivi/asis-hos/.0CAPITA EMSSANAR/CAP447195/PDE.pdf"
    ruta_pdf = request.args.get("ruta", "").strip() or RUTA_DEBUG
    
    if not ruta_pdf:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Falta el parámetro 'ruta'"]
        }), 400
    
    # Convertir ruta WSL si es necesario
    ruta_normalizada = ruta_pdf.replace("\\", "/")
    
    if ruta_normalizada.startswith("//wsl.localhost/"):
        ruta_sin_prefix = ruta_normalizada[len("//wsl.localhost/"):]
        primer_slash = ruta_sin_prefix.find("/")
        if primer_slash > 0:
            ruta_linux = "/" + ruta_sin_prefix[primer_slash + 1:]
        else:
            ruta_linux = "/" + ruta_sin_prefix
        
        if os.path.isdir(ruta_linux):
            ruta_pdf = ruta_linux
    
    if not os.path.isfile(ruta_pdf):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"El archivo no existe: {ruta_pdf}"]
        }), 400
    
    texto = extraer_texto_pdf(ruta_pdf)
    
    # Aplicar algoritmo de extracción
    datos_extraidos = extraer_datos_emssanar(texto, "debug")
    validacion = validar_pdf_por_carpeta(datos_extraidos, "debug")
    
    return jsonify({
        "status": "success",
        "data": {
            "ruta": ruta_pdf,
            "texto_crudo": texto,
            "texto_lineas": texto.split("\n") if texto else [],
            "datos": datos_extraidos,
            "validacion": validacion
        },
        "errors": []
    })


@derechos_bp.post("/procesar")
def procesar_derechos():
    """
    Procesa la ruta de carpeta y busca archivos .PDE de manera recursiva.
    Soporta:
      - Rutas absolutas Windows (D:\\carpeta)
      - Rutas UNC WSL (\\\\wsl.localhost\\Ubuntu\\...)
      - Rutas relativas Linux (/home/user/...)
      - Rutas relativas simples (carpeta)
    """
    data = request.get_json()
    ruta = data.get("ruta", "").strip()

    logger.info("Procesando ruta: %s", ruta)

    if not ruta:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no puede estar vacía"]
        }), 400

    # Normalizar separadores: convertir \ a / para compatibilidad Windows/Linux
    ruta_normalizada = ruta.replace("\\", "/")

    # Convertir rutas WSL (//wsl.localhost/Ubuntu/...) a ruta Linux nativa
    # //wsl.localhost/Ubuntu/home/user/... -> /home/user/...
    if ruta_normalizada.startswith("//wsl.localhost/"):
        ruta_sin_prefix = ruta_normalizada[len("//wsl.localhost/"):]
        primer_slash = ruta_sin_prefix.find("/")
        if primer_slash > 0:
            ruta_linux = "/" + ruta_sin_prefix[primer_slash + 1:]
        else:
            ruta_linux = "/" + ruta_sin_prefix

        if os.path.isdir(ruta_linux):
            ruta_normalizada = ruta_linux
            logger.info("Ruta WSL convertida a Linux: %s", ruta_normalizada)

    # Resolver ruta válida con fallback a relativa desde cwd
    ruta_valida = _resolver_ruta_valida(ruta_normalizada, ruta)

    if ruta_valida is None:
        if ":" in ruta:
            msg = "La ruta Windows no existe o el servidor no tiene acceso a ella."
        else:
            msg = f"La ruta no existe o no es una carpeta."
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [msg]
        }), 400

    # Buscar archivos .PDE recursivamente y extraer datos
    estructura = buscar_archivos_pde(ruta_valida, extraer_datos=EXTRACTOR_AVAILABLE)

    if not estructura:
        return jsonify({
            "status": "success",
            "data": {
                "ruta": ruta_valida,
                "mensaje": "No se encontraron archivos PDF con prefijo PDE",
                "estructura": {}
            },
            "errors": []
        })

    # Contar total de PDFs (ahora es estructura[clave]["archivos"])
    total_archivos = sum(len(info["archivos"]) for info in estructura.values())
    total_validos = sum(
        1 for info in estructura.values() 
        if info.get("datos") and info["datos"].get("pdfs")
        for pdf in info["datos"]["pdfs"]
        if pdf.get("validacion", {}).get("es_valido", False)
    )

    logger.info("Encontrados %d archivos .PDE en %d carpetas", total_archivos, len(estructura))

    return jsonify({
        "status": "success",
        "data": {
            "ruta": ruta_valida,
            "mensaje": f"Se encontraron {total_archivos} archivos .PDE ({total_validos} válidos)",
            "estructura": estructura,
            "total_carpetas": len(estructura),
            "total_archivos": total_archivos,
            "total_validos": total_validos,
            "extractor_disponible": EXTRACTOR_AVAILABLE
        },
        "errors": []
    })


def _resolver_ruta_valida(ruta_normalizada: str, ruta_original: str) -> str | None:
    """
    Verifica existencia de ruta con múltiples estrategias.
    Retorna la ruta válida o None si no se encuentra.
    """
    # 1. Tal cual (ya normalizada)
    if os.path.isdir(ruta_normalizada):
        return ruta_normalizada

    # 2. Original
    if os.path.isdir(ruta_original):
        return ruta_original

    # 3. Ruta relativa desde cwd
    ruta_relativa = os.path.abspath(ruta_normalizada)
    if os.path.isdir(ruta_relativa):
        return ruta_relativa

    # 4. Ruta Windows (D:\...)
    if ":" in ruta_original:
        ruta_windows = os.path.abspath(ruta_original)
        if os.path.isdir(ruta_windows):
            return ruta_windows

    return None