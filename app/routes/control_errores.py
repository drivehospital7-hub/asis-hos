"""Routes para control de errores de urgencias."""

import logging

from flask import Blueprint, jsonify, request, send_from_directory

from app.services.control_errores_service import (
    get_opciones,
    get_errores,
    add_error,
    update_error,
    delete_error,
    get_imagenes,
    upload_imagen,
    delete_imagen,
)

from app.constants import IMAGENES_DIR

logger = logging.getLogger(__name__)

control_errores_bp = Blueprint("control_errores", __name__)


@control_errores_bp.get("/")
def control_errores_page():
    """Página principal del control de errores."""
    from flask import render_template
    from flask_login import login_required
    from flask_login.utils import login_required

    return render_template("control_errores.html")


@control_errores_bp.get("/api/control-errores/opciones")
def listar_opciones():
    """Obtener opciones para los selects."""
    opciones = get_opciones()
    return jsonify({"status": "success", "data": opciones, "errors": []})


@control_errores_bp.get("/api/control-errores")
def listar_errores():
    """Listar errores con filtros."""
    tipo_error = request.args.get("tipo_error")
    estado = request.args.get("estado")
    responsable = request.args.get("responsable")

    return jsonify(get_errores(tipo_error, estado, responsable))


@control_errores_bp.post("/api/control-errores")
def crear_error():
    """Crear un nuevo error."""
    data = request.get_json() or {}
    return jsonify(add_error(data))


@control_errores_bp.put("/api/control-errores/<error_id>")
def actualizar_error(error_id: str):
    """Actualizar un error existente."""
    data = request.get_json() or {}
    return jsonify(update_error(error_id, data))


@control_errores_bp.delete("/api/control-errores/<error_id>")
def eliminar_error(error_id: str):
    """Eliminar un error."""
    return jsonify(delete_error(error_id))


# =============================================================================
# Gestión de Imágenes
# =============================================================================

@control_errores_bp.get("/api/control-errores/<error_id>/imagenes")
def listar_imagenes(error_id: str):
    """Listar imágenes."""
    return jsonify(get_imagenes(error_id))


@control_errores_bp.post("/api/control-errores/<error_id>/imagenes")
def subir_imagen(error_id: str):
    """Subir imagen."""
    if "imagen" not in request.files:
        return jsonify({"status": "error", "data": {}, "errors": ["No se encontró archivo"]})
    file = request.files["imagen"]
    if file.filename == "":
        return jsonify({"status": "error", "data": {}, "errors": ["Archivo vacío"]})
    return jsonify(upload_imagen(error_id, file))


@control_errores_bp.route("/api/control-errores/<error_id>/imagenes/", methods=["DELETE"])
def eliminar_imagen(error_id: str):
    """Eliminar imagen."""
    import urllib.parse
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"status": "error", "data": {}, "errors": ["filename requerido"]})
    filename = urllib.parse.unquote(filename)
    return jsonify(delete_imagen(error_id, filename))


@control_errores_bp.route("/api/control-errores/<error_id>/imagenes/<path:filename>")
def servir_imagen(error_id: str, filename: str):
    """Servir imagen."""
    from pathlib import Path
    from flask import current_app, send_from_directory, abort

    app_root = Path(current_app.root_path)
    imagenes_dir = app_root / "data" / "imagenes" / error_id
    filepath = imagenes_dir / filename
    
    if not filepath.exists():
        logger.warning(f"Imagen no encontrada: {filepath}")
        abort(404)
    
    logger.info(f"Sirviendo imagen: {filepath}")
    return send_from_directory(imagenes_dir, filename)