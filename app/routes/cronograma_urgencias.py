"""Routes para cronograma de Urgencias (antiguo Abiertas Urgencias)."""

from __future__ import annotations

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

cronograma_urgencias_bp = Blueprint("cronograma_urgencias", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@cronograma_urgencias_bp.get("/")
@permiso_requerido("*")
def cronograma_urgencias_react():
    """React shell for Cronograma Urgencias."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/cronograma-urgencias/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Cronograma Urgencias",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@cronograma_urgencias_bp.route("/api", methods=["GET", "POST"])
@permiso_requerido("*")
def api_cronograma_urgencias():
    if request.method == "GET":
        mes = request.args.get("mes", type=int)
        anio = request.args.get("anio", type=int)
        return jsonify(get_horario(mes, anio))

    data = request.get_json(silent=True) or {}
    mes = request.form.get("mes", data.get("mes"), type=int)
    anio = request.form.get("anio", data.get("anio"), type=int)
    horario = request.form.get("horario", data.get("horario"))
    return jsonify(save_horario(mes, anio, horario))


@cronograma_urgencias_bp.route("/api/delete", methods=["POST"])
@permiso_requerido("*")
def api_delete_cronograma():
    data = request.get_json(silent=True) or {}
    mes = data.get("mes")
    anio = data.get("anio")
    return jsonify(delete_horario(mes, anio))
