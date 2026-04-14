import logging

from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

ordenado_facturado_bp = Blueprint("ordenado_facturado", __name__)


@ordenado_facturado_bp.get("/ordenado-facturado")
def ordenado_facturado_page():
    """Pagina de Ordenado y Facturado."""
    return render_template("ordenado_facturado.html", form={})


@ordenado_facturado_bp.post("/ordenado-facturado/procesar")
def procesar_ordenado_facturado():
    """Procesa los 3 archivos Excel de Ordenado y Facturado."""
    try:
        # Obtener los 3 archivos
        archivo_1 = request.files.get("archivo_1")
        archivo_2 = request.files.get("archivo_2")
        archivo_3 = request.files.get("archivo_3")

        if not archivo_1 or not archivo_2 or not archivo_3:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["Debes subir los 3 archivos Excel"]
            }), 400

        # TODO: Acá va la lógica de procesamiento
        # Por ahora solo verificamos que lleguen bien
        logger.info("Archivo 1: %s", archivo_1.filename)
        logger.info("Archivo 2: %s", archivo_2.filename)
        logger.info("Archivo 3: %s", archivo_3.filename)

        return jsonify({
            "status": "success",
            "data": {
                "message": "Archivos recibidos correctamente",
                "archivos": [
                    {"nombre": archivo_1.filename, "size": archivo_1.content_length},
                    {"nombre": archivo_2.filename, "size": archivo_2.content_length},
                    {"nombre": archivo_3.filename, "size": archivo_3.content_length},
                ]
            },
            "errors": []
        })

    except Exception as e:
        logger.exception("Error procesando Ordenado y Facturado")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)]
        }), 500