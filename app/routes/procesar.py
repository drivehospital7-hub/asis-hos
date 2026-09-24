"""Ruta universal de procesamiento — acepta cualquier Excel y aplica reglas
según el valor de 'Tipo Factura Descripción' en cada fila.

Reemplaza los POST handlers de /urgencias/, /odontologia/ y
/odontologia-equipos-basicos/.
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
    send_file,
    session,
)

from app.constants import AREA_UNIFICADA
from app.services.exporter import detect_problems_only
from app.services.procesar_export import (
    build_procesar_export_workbook,
    filename_procesar_export,
)
from app.services.procesar_response import (
    LIVE_DETAIL_DEFAULTS,
    build_procesar_response_data,
)
from app.services.processor_gate import rate_limit
from app.utils import procesar_export_store as export_store
from app.utils.auth import permiso_requerido
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

procesar_bp = Blueprint("procesar", __name__)

__all__ = ["procesar_bp", "LIVE_DETAIL_DEFAULTS"]


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@procesar_bp.get("/")
@permiso_requerido("procesar")
def procesar_react():
    """React shell for Procesar."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "procesar:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/procesar/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Procesar",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@procesar_bp.post("/")
@rate_limit(1, 120, admin_exempt=True)
@permiso_requerido("procesar")
def procesar_unificado_api():
    """Procesa un Excel aplicando reglas según Tipo Factura Descripción.

    Retorna JSON con errores agrupados por tipo (mismo formato que
    export_urgencias). Reemplaza los POST handlers individuales de
    urgencias, odontología y equipos básicos.
    """
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
    profesional = request.form.get("profesional", "")
    validar_centro_costo = request.form.get("validar_centro_costo") == "on"

    # Parsear días seleccionados
    dias_raw = request.form.get("dias_seleccionados", "")
    dias: list[int] = []
    if dias_raw:
        try:
            dias = [int(d.strip()) for d in dias_raw.split(",") if d.strip()]
        except (ValueError, TypeError):
            dias = []

    # Parsear todos_profesionales_dias (JSON desde localStorage)
    todos_profesionales_dias: dict[str, list[int]] = {}
    todos_raw = request.form.get("todos_profesionales_dias", "")
    if todos_raw:
        try:
            todos_profesionales_dias = json.loads(todos_raw)
        except (json.JSONDecodeError, TypeError):
            todos_profesionales_dias = {}

    export_result, status_code = detect_problems_only(
        filename=filename,
        sheet_name=sheet_name,
        area=AREA_UNIFICADA,
        profesional=profesional,
        dias=dias,
        todos_profesionales_dias=todos_profesionales_dias,
        validar_centro_costo=validar_centro_costo,
    )

    problemas_data = export_result.get("data", {}).get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])

    cleanup_temp_excel(temp_path)

    if missing_columns:
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing_columns)}. "
                "Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing_columns,
        }), 200

    if export_result["status"] != "success":
        return jsonify({
            "status": "error",
            "data": {},
            "errors": export_result.get("errors", ["Error desconocido"]),
        }), status_code

    problemas_data = export_result["data"].get("problemas", {})
    problemas_dict = problemas_data.get("problemas", {})

    normalized_rows = problemas_dict.get("normalizados", [])

    # Shared builder (also used by the /admin/reglas simulator): display
    # items + dedup + grouping. Returns payload without export_id plus the
    # full deduped list for the GET export cache.
    response_data, deduped_items = build_procesar_response_data(
        normalized_rows=normalized_rows,
        problemas_data=problemas_data,
        tipos_procesados_fallback=export_result["data"].get("tipos_procesados", []),
    )

    # Best-effort disk cache of the FULL deduped list for GET export.
    # Never breaks the main JSON flow: on disk failure the response
    # simply omits export_id (frontend disables the Exportar button).
    try:
        export_id: str | None = export_store.put(deduped_items)
    except Exception:
        logger.exception("[BACK][ERROR] Procesar export cache write failed")
        export_id = None

    if export_id is not None:
        response_data["export_id"] = export_id

    return jsonify({
        "status": "success",
        "data": response_data,
        "errors": [],
    })


@procesar_bp.get("/export")
@permiso_requerido("procesar")
def procesar_export_api():
    """Download the cached full-list .xlsx for a previous POST /procesar.

    Thin handler: resolves ``?id=`` from the disk cache and streams the
    styled workbook. Failures use the error envelope (no bytes).
    """
    export_id = (request.args.get("id") or "").strip()
    if not export_id:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Falta el parámetro id de exportación"],
        }), 400

    rows = export_store.get(export_id)
    if rows is None:
        logger.warning("[BACK] Procesar export id unknown or expired")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Exportación no encontrada o expirada"],
        }), 400

    if (
        len(rows) > export_store.PROCESAR_EXPORT_MAX_ROWS
        or len(json.dumps(rows, default=str))
        > export_store.PROCESAR_EXPORT_MAX_ENTRY_BYTES
    ):
        logger.warning("[BACK] Procesar export over cap: %d rows", len(rows))
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Exportación excede el tamaño máximo permitido"],
        }), 413

    buffer = build_procesar_export_workbook(rows)
    logger.info("[BACK] Procesar export download: %d rows", len(rows))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename_procesar_export(),
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
