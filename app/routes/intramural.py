"""Blueprint para Intramural.

GET  /intramural/  → React shell (upload form)
POST /intramural/  → Upload + detect problems
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)

from app.constants import AREA_INTRAMURAL
from app.services.exporter import detect_problems_only
from app.services.processor_gate import rate_limit
from app.utils.auth import permiso_requerido
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

intramural_bp = Blueprint("intramural", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@intramural_bp.get("/")
@permiso_requerido("intramural")
def intramural_react():
    """React shell for Intramural."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "intramural:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/intramural/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Intramural",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
            "errores": [],
            "total_errores": 0,
        },
    )


@intramural_bp.post("/")
@rate_limit(1, 120, admin_exempt=True)
def export_intramural():
    """Procesa el archivo intramural - retorna errores en JSON."""
    uploaded_file = request.files.get("file_upload")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Debes seleccionar un archivo"],
        }), 400

    temp_path, error = save_temp_excel(uploaded_file)
    if error:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [error],
        }), 400

    filename = str(temp_path)
    sheet_name = request.form.get("sheet_name") or None

    export_result, status_code = detect_problems_only(
        filename=filename,
        sheet_name=sheet_name,
        area=AREA_INTRAMURAL,
    )

    # Cleanup archivo temporal
    cleanup_temp_excel(temp_path)

    problemas_data = export_result.get("data", {}).get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])

    if missing_columns:
        logger.error("Columnas faltantes en el Excel intramural: %s", missing_columns)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing_columns)}. "
                f"Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing_columns,
        }), 200

    if export_result["status"] == "success":
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})

        normalized_rows = problemas_dict.get("normalizados", [])
        total_errores = len(normalized_rows)

        logger.info("Errores normalizados Intramural: %d total", total_errores)

        from itertools import groupby
        errores = []
        MAX_POR_TIPO = 50

        all_items = []
        for row in normalized_rows:
            all_items.append({
                "tipo_error": row.get("tipo_error", ""),
                "factura": row.get("factura", ""),
                "fec_factura": row.get("fec_factura", ""),
                "responsable_cierra": row.get("responsable_cierra", ""),
                "descripcion": row.get("descripcion", ""),
                "procedimiento": row.get("procedimiento", ""),
                "detalle": row.get("detalle", ""),
            })

        normalized_rows_sorted = sorted(all_items, key=lambda r: r["tipo_error"])
        for tipo, group in groupby(normalized_rows_sorted, key=lambda r: r["tipo_error"]):
            items = list(group)
            errores.append({
                "tipo": tipo,
                "tipo_key": "norm_" + tipo.lower().replace(" ", "_"),
                "cantidad": len(items),
                "cantidad_mostradas": min(len(items), MAX_POR_TIPO),
                "facturas": items[:MAX_POR_TIPO],
            })

        return jsonify({
            "status": "success",
            "data": {
                "errores": errores,
                "total_errores": sum(e["cantidad"] for e in errores),
                "columnas": [
                    "Fec. Factura",
                    "Tipo de error",
                    "Número Factura",
                    "Responsable Cierra",
                    "Descripción",
                    "Procedimiento",
                    "Detalle",
                ],
            },
            "errors": [],
        }), status_code

    return jsonify({
        "status": "error",
        "data": {},
        "errors": export_result.get("errors", []),
    }), status_code
