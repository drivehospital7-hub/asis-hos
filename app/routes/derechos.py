import logging
import os
import re

from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

derechos_bp = Blueprint("derechos", __name__)

# Regex para archivos tipo PDEXXXX.pdf
PATRON_PDE = re.compile(r'^PDE\d+\.pdf$', re.IGNORECASE)


def buscar_archivos_pde(ruta_base):
    """
    Busca recursivamente archivos PDF con prefijo PDE (PDEXXXX.pdf).
    Retorna una estructura jerarquica: CAPITA XXX > CAPXXXX > archivos
    """
    estructura = {}

    for root, dirs, files in os.walk(ruta_base):
        # Filtrar solo archivos PDF con prefijo PDE
        archivos_pde = [f for f in files if PATRON_PDE.match(f)]

        if archivos_pde:
            # Obtener ruta relativa desde la carpeta base
            rel_path = os.path.relpath(root, ruta_base)
            partes = rel_path.split(os.sep)

            # Construir la clave jerárquica
            clave = " > ".join(partes) if partes else "Raíz"

            estructura[clave] = sorted(archivos_pde)

    return estructura


@derechos_bp.get("/derechos")
def derechos_page():
    """Pagina principal del modulo Derechos."""
    return render_template("derechos.html")


@derechos_bp.post("/procesar")
def procesar_derechos():
    """
    Procesa la ruta de carpeta y busca archivos .PDE de manera recursiva.
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

    if not os.path.isdir(ruta):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"La ruta '{ruta}' no existe o no es una carpeta"]
        }), 400

    # Buscar archivos .PDE recursivamente
    estructura = buscar_archivos_pde(ruta)

    if not estructura:
        return jsonify({
            "status": "success",
            "data": {
                "ruta": ruta,
                "mensaje": "No se encontraron archivos PDF con prefijo PDE",
                "estructura": {}
            },
            "errors": []
        })

    total_archivos = sum(len(archivos) for archivos in estructura.values())

    logger.info("Encontrados %d archivos .PDE en %d carpetas", total_archivos, len(estructura))

    return jsonify({
        "status": "success",
        "data": {
            "ruta": ruta,
            "mensaje": f"Se encontraron {total_archivos} archivos .PDE",
            "estructura": estructura,
            "total_carpetas": len(estructura),
            "total_archivos": total_archivos
        },
        "errors": []
    })