import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, session, url_for

logger = logging.getLogger(__name__)

home_bp = Blueprint("home", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@home_bp.get("/")
def root_redirect():
    """Redirige la raíz al dashboard."""
    return redirect(url_for("home.home_react"))


@home_bp.get("/dashboard")
def home_react():
    """React shell for dashboard."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "dashboard:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/index/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    kpis = [
        {"label": "Facturas del mes", "value": "0", "trend": "Sin datos", "icon": "trending-up"},
        {"label": "Pendientes de revisi\u00f3n", "value": "0", "trend": "Sin datos", "icon": "clock"},
        {"label": "Resueltas este mes", "value": "0", "trend": "Sin datos", "icon": "check-circle"},
    ]
    areas = [
        {"title": "Urgencias", "description": "Procesamiento y validaci\u00f3n de facturas del servicio de urgencias.", "href": "/urgencias", "pending": 31, "tone": "danger", "pending_label": "errores"},
        {"title": "Control de Novedades", "description": "Registro y seguimiento de novedades en facturaci\u00f3n.", "href": "/control-errores", "pending": 9, "tone": "warning", "pending_label": "pendientes"},
        {"title": "Facturas Abiertas", "description": "Gesti\u00f3n de horarios y responsables del servicio de urgencias.", "href": "/abiertas-urgencias", "pending": 0, "tone": "info", "pending_label": "sin horario"},
    ]

    return render_template(
        "react_shell.html",
        page_title="Panel Principal",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
            "kpis": kpis,
            "areas": areas,
        },
    )


