"""Routes para la página de horarios de abiertas urgencias."""

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.services.abiertas_urgencias_service import (
    delete_horario,
    get_horario,
    save_horario,
)
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

abiertas_urgencias_bp = Blueprint("abiertas_urgencias", __name__)


# ═══════════════════════════════════════════════
# Página principal (Jinja2 — legacy)
# ═══════════════════════════════════════════════


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@abiertas_urgencias_bp.get("/")
@permiso_requerido("facturas_abiertas")
def abiertas_urgencias_react():
    """React shell for Abiertas Urgencias."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "facturas_abiertas:write" in permisos

    # Read Vite manifest to find hashed asset filename
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/abiertas-urgencias/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
            "is_auth": True,
        },
    )





# ═══════════════════════════════════════════════
# API — obtener horario guardado
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.get("/api/schedule")
@permiso_requerido("facturas_abiertas")
def api_get_schedule():
    """Obtener el horario guardado."""
    return jsonify(get_horario())


# ═══════════════════════════════════════════════
# API — guardar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.post("/api/schedule")
@permiso_requerido("facturas_abiertas:write")
def api_save_schedule():
    """Guardar el horario parseado."""
    data = request.get_json() or {}
    dias = data.get("dias", [])
    return jsonify(save_horario(dias))


# ═══════════════════════════════════════════════
# API — eliminar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.delete("/api/schedule")
@permiso_requerido("facturas_abiertas:write")
def api_delete_schedule():
    """Eliminar el horario guardado."""
    return jsonify(delete_horario())
