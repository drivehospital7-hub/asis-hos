"""Blueprint for the Catalog Management page (/catalogo).

Protected by @admin_requerido — only users with permiso '*' can access.
"""

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, render_template, session

from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

catalogo_bp = Blueprint("catalogo", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@catalogo_bp.get("/catalogo")
@admin_requerido
def catalogo_react():
    """React shell for the Catalog Management page."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/catalogo/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Catálogos · Hospital Orito",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )
