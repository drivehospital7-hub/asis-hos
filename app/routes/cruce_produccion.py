"""Blueprint para Cruce Producción vs Carpetas.

GET  /cruce-produccion/         → Shell React (permiso cruce_produccion)
POST /cruce-produccion/cruce    → Cruza Excel producción vs scan fresco (requiere :write)
GET  /cruce-produccion/export   → Descarga el .xlsx cacheado (?id=)

Solo delega: reader/matcher/exporter viven en
app/services/cruce_produccion/ y el scan fresco en
app.services.monitoreo_carpetas.detect_all.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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

from app.services.cruce_produccion.exporter import (
    build_cruce_export_workbook,
    cache_cruce_result,
    get_cached_cruce_result,
)
from app.services.cruce_produccion.matcher import (
    extract_code,
    find_desactualizados,
    find_faltantes,
)
from app.services.cruce_produccion.reader import read_produccion
from app.services.monitoreo_carpetas.detect_all import detect_all
from app.services.processor_gate import rate_limit
from app.utils import procesar_export_store as export_store
from app.utils.auth import permiso_requerido
from app.utils.errores_storage import obtener_novedades
from app.utils.input_data import cleanup_temp_excel, save_temp_excel
from app.utils.monitoreo_store import get_roots

logger = logging.getLogger(__name__)

cruce_produccion_bp = Blueprint("cruce_produccion", __name__)

__all__ = ["cruce_produccion_bp"]

CRUCE_EXPORT_FILENAME = "cruce_produccion_faltantes.xlsx"


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@cruce_produccion_bp.get("/")
@permiso_requerido("cruce_produccion")
def index():
    """React shell for Cruce Producción."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "cruce_produccion:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(
        manifest_path,
        "src/pages/cruce-produccion/index.html",
        "file",
    )
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Cruce Producción",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@cruce_produccion_bp.post("/cruce")
@rate_limit(1, 120, admin_exempt=True)
@permiso_requerido("cruce_produccion:write")
def cruce_api():
    """Cruza el Excel de producción contra un scan fresco de carpetas.

    Retorna faltantes (códigos sin carpeta, con responsable), filas a
    revisar (sin código extraíble) y resumen, más export_id opcional
    para GET /export. El scan es fresco (detect_all directo).
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

    try:
        return _cruce_from_temp(str(temp_path))
    finally:
        cleanup_temp_excel(temp_path)


def _cruce_from_temp(filename: str):
    """Lee producción, escanea carpetas y retorna el cruce envelopado."""
    roots, _fuente, _ultima = get_roots()
    if not roots:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontraron rutas válidas en la configuración."],
        }), 200

    rows, missing = read_produccion(filename)
    if missing:
        logger.error("Columnas faltantes en producción: %s", missing)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing)}. "
                "Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing,
        }), 200

    scan_result = detect_all(roots)
    novedades = obtener_novedades()
    result = find_faltantes(rows, scan_result.facturas, novedades)
    # Soportes no actualizados: solo facturas del Excel en proceso.
    codigos_excel = {
        code
        for row in rows
        if (code := extract_code(row.get("numero_factura"))) is not None
    }
    des = find_desactualizados(
        scan_result.facturas, novedades, solo_codigos=codigos_excel
    )
    result["resumen"]["total_desactualizados"] = des["resumen"][
        "total_desactualizados"
    ]

    try:
        export_id: str | None = cache_cruce_result(
            result["faltantes"], result["revisar"], des["desactualizados"]
        )
    except Exception:
        logger.exception("[BACK][ERROR] Cruce export cache write failed")
        export_id = None

    data = {
        "faltantes": result["faltantes"],
        "revisar": result["revisar"],
        "desactualizados": des["desactualizados"],
        "resumen": result["resumen"],
        "scanned_roots": roots,
        "last_scan_at": datetime.now(timezone.utc).isoformat(),
    }
    if export_id is not None:
        data["export_id"] = export_id
    return jsonify({"status": "success", "data": data, "errors": []}), 200


@cruce_produccion_bp.get("/export")
@permiso_requerido("cruce_produccion")
def cruce_export_api():
    """Download the cached cruce .xlsx for a previous POST /cruce.

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

    cached = get_cached_cruce_result(export_id)
    if cached is None:
        logger.warning("[BACK] Cruce export id unknown or expired")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Exportación no encontrada o expirada"],
        }), 400

    faltantes = cached["faltantes"]
    revisar = cached["revisar"]
    desactualizados = cached.get("desactualizados", [])
    if (
        len(faltantes) + len(revisar) + len(desactualizados)
        > export_store.PROCESAR_EXPORT_MAX_ROWS
        or len(json.dumps(cached, default=str))
        > export_store.PROCESAR_EXPORT_MAX_ENTRY_BYTES
    ):
        logger.warning("[BACK] Cruce export over cap")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Exportación excede el tamaño máximo permitido"],
        }), 413

    buffer = build_cruce_export_workbook(faltantes, revisar, desactualizados)
    logger.info(
        "[BACK] Cruce export download: %d faltantes, %d a revisar, %d desactualizados",
        len(faltantes),
        len(revisar),
        len(desactualizados),
    )
    return send_file(
        buffer,
        as_attachment=True,
        download_name=CRUCE_EXPORT_FILENAME,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
