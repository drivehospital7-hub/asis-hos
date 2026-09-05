"""Routes para cronograma de bacteriólogas."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.services.cronograma_bacteriologas_service import (
    get_cronograma,
    save_cronograma,
    get_turno_del_dia,
)
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

cronograma_bp = Blueprint("cronograma_bacteriologas", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@cronograma_bp.get("/")
@permiso_requerido("cronograma_bacteriologas")
def cronograma_react():
    """React shell for Cronograma Bacteriólogas."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/cronograma-bacteriologas/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Cronograma Bacteriólogas",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": True,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@cronograma_bp.get("/api")
@permiso_requerido("cronograma_bacteriologas")
def api_get_cronograma():
    mes = request.args.get("mes", type=int)
    anio = request.args.get("anio", type=int)
    data = get_cronograma(mes, anio)
    return jsonify({"status": "success", "data": data, "errors": []})


@cronograma_bp.post("/api")
@permiso_requerido("cronograma_bacteriologas")
def api_save_cronograma():
    body = request.get_json()
    if not body:
        return jsonify({"status": "error", "data": {}, "errors": ["Body requerido"]}), 400
    mes = body.get("mes")
    anio = body.get("anio")
    if not mes or not anio:
        return jsonify({"status": "error", "data": {}, "errors": ["mes y anio requeridos"]}), 400
    data = save_cronograma(mes, anio, body)
    return jsonify({"status": "success", "data": data, "errors": []})


@cronograma_bp.get("/api/turno")
@permiso_requerido("cronograma_bacteriologas")
def api_turno():
    mes = request.args.get("mes", type=int)
    anio = request.args.get("anio", type=int)
    dia = request.args.get("dia", type=int)
    en_turno = get_turno_del_dia(mes, anio, dia)
    return jsonify({"status": "success", "data": {"en_turno": en_turno}, "errors": []})
