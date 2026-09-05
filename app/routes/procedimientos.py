"""Routes para consulta de procedimientos (solo lectura).

Endpoints REST para consultar la vista unificada v_procedimientos.
Los endpoints de escritura (POST/PUT/DELETE) fueron descontinuados —
retornan 410 Gone con mensaje informativo.
"""

from flask import Blueprint, request, jsonify
from app.utils.auth import admin_requerido
from app.services.procedimientos_db import (
    get_procedimiento,
    get_all_by_codigo,
    get_eps_disponibles,
    get_all_by_eps,
)

procedimientos_bp = Blueprint("procedimientos", __name__)

GONE_MESSAGE = "Este endpoint ya no está disponible. Usá /catalogo para gestionar procedimientos."


# ─── READ endpoints (mantenidos) ───────────────────────────────────────


@procedimientos_bp.route("/procedimientos", methods=["GET"])
@admin_requerido
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
@admin_requerido
def list_eps():
    """Listar EPS disponibles."""
    return jsonify({
        "status": "success",
        "data": {"eps_disponibles": get_eps_disponibles()},
        "errors": []
    })


@procedimientos_bp.route("/procedimientos/<eps>/<codigo>", methods=["GET"])
@admin_requerido
def get_procedimiento_route(eps: str, codigo: str):
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


# ─── WRITE endpoints (descontinuados → 410 Gone) ──────────────────────


@procedimientos_bp.route("/procedimientos", methods=["POST"])
def create_procedimiento_gone():
    """POST /procedimientos — descontinuado."""
    return jsonify({
        "status": "error",
        "data": {},
        "errors": [GONE_MESSAGE],
    }), 410


@procedimientos_bp.route("/procedimientos/<int:procedimiento_id>", methods=["PUT"])
def update_procedimiento_gone(procedimiento_id: int):
    """PUT /procedimientos/<id> — descontinuado."""
    return jsonify({
        "status": "error",
        "data": {},
        "errors": [GONE_MESSAGE],
    }), 410


@procedimientos_bp.route("/procedimientos/<int:procedimiento_id>", methods=["DELETE"])
def delete_procedimiento_gone(procedimiento_id: int):
    """DELETE /procedimientos/<id> — descontinuado."""
    return jsonify({
        "status": "error",
        "data": {},
        "errors": [GONE_MESSAGE],
    }), 410
