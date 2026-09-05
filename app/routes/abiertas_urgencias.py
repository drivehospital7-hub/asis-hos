"""Routes para la página de horarios de abiertas urgencias."""

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.services.abiertas_urgencias_service import (
    delete_horario,
    get_horario,
    list_horarios,
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
# API — listar meses disponibles
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.get("/api/schedules")
@permiso_requerido("facturas_abiertas")
def api_list_schedules():
    """Listar meses con horario guardado."""
    result = list_horarios()
    return jsonify(result)


# ═══════════════════════════════════════════════
# API — obtener horario guardado
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.get("/api/schedule")
@permiso_requerido("facturas_abiertas")
def api_get_schedule():
    """Obtener el horario guardado (soporta ?mes=&anio=)."""
    mes_raw = request.args.get("mes")
    anio_raw = request.args.get("anio")
    if mes_raw is not None or anio_raw is not None:
        if not mes_raw or not anio_raw:
            return jsonify({"status": "error", "data": {}, "errors": ["mes y anio requeridos"]}), 400
        if not mes_raw.isdigit() or not anio_raw.isdigit():
            return jsonify({"status": "error", "data": {}, "errors": ["mes invalido"]}), 400
        mes = int(mes_raw)
        anio = int(anio_raw)
        result = get_horario(mes, anio)
        return jsonify(result)
    return jsonify(get_horario())


# ═══════════════════════════════════════════════
# API — guardar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.post("/api/schedule")
@permiso_requerido("facturas_abiertas:write")
def api_save_schedule():
    """Guardar el horario parseado (soporta mes/anio)."""
    data = request.get_json() or {}
    dias = data.get("dias")
    mes_raw = data.get("mes")
    anio_raw = data.get("anio")

    if dias is None:
        return jsonify({"status": "error", "data": {}, "errors": ["No hay datos para guardar"]}), 400

    # Legacy body only dias -> delegate to service default current month
    if mes_raw is None and anio_raw is None:
        return jsonify(save_horario(dias))

    # Require both mes and anio when one is present
    if mes_raw is None or anio_raw is None:
        return jsonify({"status": "error", "data": {}, "errors": ["mes y anio requeridos"]}), 400

    try:
        mes = int(mes_raw)
        anio = int(anio_raw)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "data": {}, "errors": ["mes invalido"]}), 400

    return jsonify(save_horario(mes, anio, dias))


# ═══════════════════════════════════════════════
# API — eliminar horario
# ═══════════════════════════════════════════════


@abiertas_urgencias_bp.delete("/api/schedule")
@permiso_requerido("facturas_abiertas:write")
def api_delete_schedule():
    """Eliminar el horario guardado (?mes=&anio= requeridos)."""
    mes_raw = request.args.get("mes")
    anio_raw = request.args.get("anio")
    if not mes_raw or not anio_raw:
        return jsonify({"status": "error", "data": {}, "errors": ["mes y anio requeridos"]}), 400
    if not mes_raw.isdigit() or not anio_raw.isdigit():
        return jsonify({"status": "error", "data": {}, "errors": ["mes invalido"]}), 400
    mes = int(mes_raw)
    anio = int(anio_raw)
    return jsonify(delete_horario(mes, anio))
