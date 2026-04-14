"""Routes para CRUD de procedimientos.

Endpoints REST para consultar y gestionar la base de datos de procedimientos.
"""

from flask import Blueprint, request, jsonify
from app.services.procedimientos_db import (
    get_procedimiento,
    get_all_by_codigo,
    get_eps_disponibles,
    get_all_by_eps,
)
from app.services.procedimientos_crud import (
    insert_procedimiento,
    update_procedimiento,
    delete_procedimiento,
    ProcedimientoInput,
)

procedimientos_bp = Blueprint("procedimientos", __name__)


@procedimientos_bp.route("/procedimientos", methods=["GET"])
def list_procedimientos():
    """Listar procedimientos con filtros opcionales.
    
    Query params:
        - eps: filtrar por EPS
        - codigo: filtrar por código CUPS
        - all: si es "true" y hay eps, devuelve todos los procedimientos de esa EPS
    """
    eps = request.args.get("eps")
    codigo = request.args.get("codigo")
    all_flag = request.args.get("all", "false").lower() == "true"
    
    # Si hay filtro por código, buscar todas las EPS para ese código
    if codigo:
        resultados = get_all_by_codigo(codigo)
        data = [
            {
                "id": p.id,
                "eps": p.eps,
                "codigo_cups": p.codigo_cups,
                "descripcion": p.descripcion,
                "tarifa": p.tarifa,
            }
            for p in resultados
        ]
        return jsonify({"status": "success", "data": data, "errors": []})
    
    # Si hay eps y all=true, devolver todos los procedimientos de esa EPS
    if eps and all_flag:
        resultados = get_all_by_eps(eps)
        data = [
            {
                "id": p.id,
                "eps": p.eps,
                "codigo_cups": p.codigo_cups,
                "descripcion": p.descripcion,
                "tarifa": p.tarifa,
            }
            for p in resultados
        ]
        return jsonify({"status": "success", "data": data, "errors": []})
    
    # Si hay filtro por eps (sin all), buscar un procedimiento
    if eps:
        proc = get_procedimiento(eps, codigo or "")
        if proc:
            data = [{
                "id": proc.id,
                "eps": proc.eps,
                "codigo_cups": proc.codigo_cups,
                "descripcion": proc.descripcion,
                "tarifa": proc.tarifa,
            }]
        else:
            data = []
    else:
        # Sin filtros, devolver EPS disponibles
        return jsonify({
            "status": "success",
            "data": {"eps_disponibles": get_eps_disponibles()},
            "errors": []
        })
    
    return jsonify({"status": "success", "data": data, "errors": []})


@procedimientos_bp.route("/procedimientos/eps", methods=["GET"])
def list_eps():
    """Listar EPS disponibles."""
    return jsonify({
        "status": "success",
        "data": {"eps_disponibles": get_eps_disponibles()},
        "errors": []
    })


@procedimientos_bp.route("/procedimientos/<eps>/<codigo>", methods=["GET"])
def get_procedimiento(eps: str, codigo: str):
    """Buscar un procedimiento por EPS y código."""
    proc = get_procedimiento(eps, codigo)
    
    if not proc:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Procedimiento no encontrado: {eps} / {codigo}"]
        }), 404
    
    return jsonify({
        "status": "success",
        "data": {
            "id": proc.id,
            "eps": proc.eps,
            "codigo_cups": proc.codigo_cups,
            "descripcion": proc.descripcion,
            "tarifa": proc.tarifa,
        },
        "errors": []
    })


@procedimientos_bp.route("/procedimientos", methods=["POST"])
def create_procedimiento():
    """Insertar un nuevo procedimiento."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Request body requerido"]
        }), 400
    
    # Validar campos requeridos
    errors = []
    if "eps" not in data or not data.get("eps"):
        errors.append("eps es requerido")
    if "codigo_cups" not in data or not data.get("codigo_cups"):
        errors.append("codigo_cups es requerido")
    
    if errors:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": errors
        }), 400
    
    proc_input = ProcedimientoInput(
        eps=data.get("eps"),
        codigo_cups=data.get("codigo_cups"),
        descripcion=data.get("descripcion"),
        tarifa=data.get("tarifa"),
    )
    
    success, message, inserted_id = insert_procedimiento(proc_input)
    
    if not success:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [message]
        }), 400
    
    return jsonify({
        "status": "success",
        "data": {"id": inserted_id, "message": message},
        "errors": []
    }), 201


@procedimientos_bp.route("/procedimientos/<int:procedimiento_id>", methods=["PUT"])
def update_procedimiento_route(procedimiento_id: int):
    """Actualizar un procedimiento existente."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Request body requerido"]
        }), 400
    
    proc_input = ProcedimientoInput(
        eps=data.get("eps", ""),
        codigo_cups=data.get("codigo_cups", ""),
        descripcion=data.get("descripcion"),
        tarifa=data.get("tarifa"),
    )
    
    success, message = update_procedimiento(procedimiento_id, proc_input)
    
    if not success:
        status_code = 400 if "no encontrado" in message.lower() else 404
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [message]
        }), status_code
    
    return jsonify({
        "status": "success",
        "data": {"message": message},
        "errors": []
    })


@procedimientos_bp.route("/procedimientos/<int:procedimiento_id>", methods=["DELETE"])
def delete_procedimiento_route(procedimiento_id: int):
    """Eliminar un procedimiento."""
    success, message = delete_procedimiento(procedimiento_id)
    
    if not success:
        status_code = 400 if "no encontrado" in message.lower() else 404
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [message]
        }), status_code
    
    return jsonify({
        "status": "success",
        "data": {"message": message},
        "errors": []
    })