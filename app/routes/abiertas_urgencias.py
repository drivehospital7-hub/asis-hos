"""Routes para la página de horarios de abiertas urgencias."""

import logging

from flask import Blueprint, jsonify, render_template, request, session
from flask_login import current_user

from app.services.abiertas_urgencias_service import (
    delete_horario,
    get_horario,
    save_horario,
)

logger = logging.getLogger(__name__)

abiertas_urgencias_bp = Blueprint("abiertas_urgencias", __name__)


# ═══════════════════════════════════════════════
# Página principal
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.get("/")
def abiertas_urgencias_page():
    """Página de horarios de abiertas urgencias."""
    is_auth = current_user.is_authenticated or session.get("ce_authenticated")
    return render_template("abiertas_urgencias.html", is_auth=is_auth)


# ═══════════════════════════════════════════════
# API — obtener horario guardado
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.get("/api/schedule")
def api_get_schedule():
    """Obtener el horario guardado."""
    return jsonify(get_horario())


# ═══════════════════════════════════════════════
# API — guardar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.post("/api/schedule")
def api_save_schedule():
    """Guardar el horario parseado."""
    data = request.get_json() or {}
    dias = data.get("dias", [])
    return jsonify(save_horario(dias))


# ═══════════════════════════════════════════════
# API — eliminar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.delete("/api/schedule")
def api_delete_schedule():
    """Eliminar el horario guardado."""
    return jsonify(delete_horario())
