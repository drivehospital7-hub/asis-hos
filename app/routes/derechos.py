import json
import logging
import os
import re
from pathlib import Path

from flask import Blueprint, current_app, render_template, request, Response, jsonify, session

from app.utils.auth import permiso_requerido
from app.services.processor_gate import rate_limit
from app.constants.base import DERECHOS_PDF_BASE_PATH

logger = logging.getLogger(__name__)

derechos_bp = Blueprint("derechos", __name__)


def _ruta_dentro_de_base(ruta: str) -> bool:
    """True si la ruta resuelta está dentro de DERECHOS_PDF_BASE_PATH.

    Usa realpath + commonpath para impedir escapes con '..' o symlinks.
    Si no hay base configurada, no se permite ninguna lectura (fail closed).
    """
    base = os.path.realpath(DERECHOS_PDF_BASE_PATH) if DERECHOS_PDF_BASE_PATH else ""
    if not base:
        return False
    try:
        ruta_real = os.path.realpath(ruta)
        return os.path.commonpath([ruta_real, base]) == base
    except (ValueError, OSError):
        return False


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


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
@permiso_requerido("derechos")
def derechos_react():
    """React shell for Derechos."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "derechos:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/derechos/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Derechos",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )



@derechos_bp.get("/texto")
@permiso_requerido("derechos")
def derechos_texto():
    """
    Devuelve el texto RAW de un PDF para debugging.
    Útil para ver cómo viene el texto y entender la estructura.
    
    URL:
    http://localhost:5000/derechos/texto
    """
    ruta_pdf = request.args.get("ruta", "").strip()

    if not ruta_pdf:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Falta el parámetro 'ruta'"]
        }), 400

    if not _ruta_dentro_de_base(ruta_pdf):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta está fuera del directorio permitido (DERECHOS_PDF_BASE_PATH)"]
        }), 403

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
@permiso_requerido("derechos")
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

    if not _ruta_dentro_de_base(ruta_valida):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta está fuera del directorio permitido (DERECHOS_PDF_BASE_PATH)"]
        }), 403

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


# =============================================================================
# Auditoría PDF endpoints
# =============================================================================


@derechos_bp.get("/auditoria")
@permiso_requerido("derechos")
def auditoria_react():
    """React shell for Auditoría PDF."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/auditoria/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Auditoría PDF",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@derechos_bp.post("/auditoria/debug")
@permiso_requerido("derechos")
def auditoria_debug_pdf():
    """Debug endpoint: muestra el texto extraído y cada paso del parseo de un PDF."""
    from app.services.auditoria.extractor import extraer_texto_pdf
    from app.services.auditoria.pde_parser import extraer_bloque_derechos, extraer_datos_derechos
    from app.services.auditoria.fev_parser import parsear_fev

    data = request.get_json()
    ruta = data.get("ruta", "").strip() if data else ""

    if not ruta:
        return jsonify({"status": "error", "data": {}, "errors": ["Ruta de archivo no existe"]}), 400

    if not _ruta_dentro_de_base(ruta):
        return jsonify({"status": "error", "data": {}, "errors": ["La ruta está fuera del directorio permitido (DERECHOS_PDF_BASE_PATH)"]}), 403

    if not os.path.isfile(ruta):
        return jsonify({"status": "error", "data": {}, "errors": ["Ruta de archivo no existe"]}), 400

    nombre = os.path.basename(ruta).upper()

    debug = {"archivo": nombre, "pasos": []}

    # Tipo
    if nombre.startswith("PDE"):
        debug["tipo"] = "PDE"
        debug["pasos"].append({"paso": "1. extraer_texto_pdf", "estado": "..."})
        texto = extraer_texto_pdf(ruta, "PDE")
        debug["pasos"][-1]["estado"] = "OK" if texto else "VACÍO"
        debug["texto_crudo"] = texto[:2000] if texto else ""

        debug["pasos"].append({"paso": "2. extraer_bloque_derechos", "estado": "..."})
        bloque = extraer_bloque_derechos(texto) if texto else ""
        debug["pasos"][-1]["estado"] = "OK" if bloque else "NO ENCONTRADO"
        debug["bloque_encontrado"] = bloque[:1000] if bloque else ""

        debug["pasos"].append({"paso": "3. extraer_datos_derechos", "estado": "..."})
        datos = extraer_datos_derechos(bloque or texto) if (bloque or texto) else {}
        debug["pasos"][-1]["estado"] = "OK"
        debug["datos_extraidos"] = datos

    elif nombre.startswith("FEV"):
        debug["tipo"] = "FEV"
        try:
            resultado = parsear_fev(ruta)
            debug["datos_extraidos"] = resultado
        except Exception as e:
            debug["error"] = str(e)

    else:
        debug["tipo"] = "OTRO"
        debug["pasos"].append({"paso": "1. extraer_texto_pdf", "estado": "..."})
        texto = extraer_texto_pdf(ruta, "SOPORTE")
        debug["pasos"][-1]["estado"] = "OK" if texto else "VACÍO"
        debug["texto_crudo"] = texto[:2000] if texto else ""

    return jsonify({"status": "success", "data": debug, "errors": []})


@derechos_bp.post("/auditoria/procesar")
@permiso_requerido("derechos")
@rate_limit(1, 120, admin_exempt=True)
def auditoria_procesar():
    """
    Procesa una carpeta de PDFs para auditoría.
    Recibe {"ruta": "..."} y retorna el análisis completo.
    """
    data = request.get_json()
    ruta = data.get("ruta", "").strip() if data else ""

    if not ruta:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no puede estar vacía"]
        }), 400

    # Normalizar separadores
    ruta_normalizada = ruta.replace("\\", "/")

    # Resolver ruta válida
    ruta_valida = _resolver_ruta_valida(ruta_normalizada, ruta)
    if ruta_valida is None:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no existe o no es una carpeta."]
        }), 400

    if not _ruta_dentro_de_base(ruta_valida):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta está fuera del directorio permitido (DERECHOS_PDF_BASE_PATH)"]
        }), 403

    # Verificar que sea un directorio, no un archivo
    if not os.path.isdir(ruta_valida):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no es una carpeta."]
        }), 400

    logger.info("Auditando carpeta: %s", ruta_valida)

    try:
        from app.services.auditoria.auditor import auditar_carpeta
        resultados = auditar_carpeta(ruta_valida)

        if isinstance(resultados, dict) and "error" in resultados:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [resultados["error"]]
            }), 400

    except ImportError as e:
        logger.exception("Error importando auditoria module")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error de configuración: {e}"]
        }), 500
    except Exception as e:
        logger.exception("Error procesando auditoría")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error procesando: {e}"]
        }), 500

    metadata = resultados.get("_metadata", {})
    expedientes = resultados.get("expedientes", resultados)

    resumen = {
        "total_pdfs_encontrados": metadata.get("total_pdfs_encontrados", 0),
        "total_clasificados": metadata.get("total_clasificados", 0),
        "total_ignorados": metadata.get("total_ignorados", 0),
        "total_expedientes": len(expedientes) if isinstance(expedientes, dict) else 0,
    }

    response_data = {
        "status": "success",
        "data": {
            "ruta": ruta_valida,
            "resumen": resumen,
            "estructura": expedientes,
            "_metadata": {
                "archivos_ignorados": metadata.get("archivos_ignorados", []),
                "archivos_con_error": metadata.get("archivos_con_error", []),
            },
        },
        "errors": [],
    }

    # ?descargar=1 → devuelve el JSON como archivo descargable
    if request.args.get("descargar"):
        nombre_base = os.path.basename(ruta_valida.rstrip("/\\").rstrip("/").rstrip("\\"))
        json_str = json.dumps(response_data, indent=2, ensure_ascii=False)
        return Response(
            json_str,
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="auditoria_{nombre_base}.json"'
            },
        )

    return jsonify(response_data)