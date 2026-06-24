"""Blueprint for the Rule Engine admin page (/admin/reglas).

Protected by @admin_requerido — only users with permiso '*' can access.
Serves the React SPA via react_shell.html template.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, render_template, session

from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

reglas_admin_bp = Blueprint("reglas_admin", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    try:
        manifest = json.loads(manifest_path.read_text())
        return manifest.get(entry_key, {}).get(field, "")
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not read manifest at %s", manifest_path)
        return ""


@reglas_admin_bp.get("/admin/reglas")
@admin_requerido
def reglas_admin_react():
    """React shell for the Rule Engine Admin page."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/admin-reglas/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Admin Reglas · Hospital Orito",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )
