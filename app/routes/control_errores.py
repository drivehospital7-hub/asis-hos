"""Routes para control de errores de urgencias."""

import logging

from flask import Blueprint, jsonify, request

from app.services.control_errores_service import (
    get_opciones,
    get_errores,
    add_error,
    update_error,
    delete_error,
)

logger = logging.getLogger(__name__)

control_errores_bp = Blueprint("control_errores", __name__)


@control_errores_bp.get("/control-errores")
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