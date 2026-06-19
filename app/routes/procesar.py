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
    session,
)

from app.constants import AREA_UNIFICADA
from app.services.exporter import detect_problems_only
from app.services.processor_gate import rate_limit
from app.utils.auth import permiso_requerido
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

procesar_bp = Blueprint("procesar", __name__)


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
    total_errores = len(normalized_rows)

    from itertools import groupby

    errores = []
    MAX_POR_TIPO = 50

    all_items = []
    for row in normalized_rows:
        all_items.append({
            "tipo_error": row.get("tipo_error", ""),
            "tipo_factura": row.get("tipo_factura", "Sin tipo"),
            "factura": row.get("factura", ""),
            "fec_factura": row.get("fec_factura", ""),
            "responsable_cierra": row.get("responsable_cierra", ""),
            "descripcion": row.get("descripcion", ""),
            "procedimiento": row.get("procedimiento", ""),
            "detalle": row.get("detalle", ""),
            "fecha_cierre_vacia": row.get("fecha_cierre_vacia", False),
        })

    sorted_by_factura = sorted(
        all_items, key=lambda r: (r["tipo_factura"], r["tipo_error"])
    )
    for tipo_factura, factura_group in groupby(
        sorted_by_factura, key=lambda r: r["tipo_factura"]
    ):
        factura_items = list(factura_group)
        tipos = []
        total_factura = 0
        for tipo_error, error_group in groupby(
            factura_items, key=lambda r: r["tipo_error"]
        ):
            items = list(error_group)
            tipos.append({
                "tipo": tipo_error,
                "tipo_key": "norm_" + tipo_error.lower().replace(" ", "_"),
                "cantidad": len(items),
                "cantidad_mostradas": min(len(items), MAX_POR_TIPO),
                "facturas": items[:MAX_POR_TIPO],
            })
            total_factura += len(items)
        errores.append({
            "tipo_factura": tipo_factura,
            "total": total_factura,
            "tipos": tipos,
        })

    return jsonify({
        "status": "success",
        "data": {
            "errores": errores,
            "total_errores": sum(
                sum(t["cantidad"] for t in f["tipos"]) for f in errores
            ),
            "tipos_procesados": problemas_data.get(
                "tipos_procesados",
                export_result["data"].get("tipos_procesados", []),
            ),
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
    })
