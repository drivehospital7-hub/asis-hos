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

from app.constants import AREA_ODONTOLOGIA, PROFESIONALES_ODONTOLOGIA
from app.services.excel_headers_page import build_excel_headers_form_context
from app.services.exporter import detect_problems_only
from app.services.processor_gate import rate_limit
from app.utils.auth import permiso_requerido
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

excel_headers_bp = Blueprint("excel_headers", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@excel_headers_bp.get("/")
@permiso_requerido("odontologia")
def excel_headers_react():
    """React shell for Odontologia."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "odontologia:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/odontologia/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Odontología",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
            "profesionales": [
                {"codigo": k, **v}
                for k, v in PROFESIONALES_ODONTOLOGIA.items()
            ],
        },
    )





@excel_headers_bp.post("/")
@rate_limit(1, 120, admin_exempt=True)
def export_cruce_facturas():
    """Procesa el archivo - retorna errores en JSON."""
    uploaded_file = request.files.get("file_upload")
    
    # Obtener selección profesional y días
    profesional = request.form.get("profesional", "")
    dias_str = request.form.get("dias_seleccionados", "")
    dias = [int(d) for d in dias_str.split(",") if d.strip().isdigit()] if dias_str else []
    
    # Obtener todos los profesionales y sus días desde localStorage
    todos_dias_json = request.form.get("todos_profesionales_dias", "{}")
    try:
        import json
        todos_profesionales_dias = json.loads(todos_dias_json)
    except:
        todos_profesionales_dias = {}
    
    validar_centro_costo = request.form.get("validar_centro_costo") == "on"
    
    logger.info("Procesando archivo - Profesional: %s, Días: %s, Validar Centro Costo: %s, TodosProfesionalesDias: %s", 
                profesional, dias, validar_centro_costo, todos_profesionales_dias)
    
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
    # Valores por defecto (las opciones avanzadas fueron eliminadas)
    sheet_name = None
    header_row = 0

    ctx = build_excel_headers_form_context(
        file=filename,
        sheet_name=sheet_name,
        sheet_id_raw=None,
        header_row_raw=None,
    )
    ctx["profesionales"] = PROFESIONALES_ODONTOLOGIA

    export_result, status_code = detect_problems_only(
        filename=filename,
        sheet_name=sheet_name,
        area=AREA_ODONTOLOGIA,
        profesional=profesional,
        dias=dias,
        todos_profesionales_dias=todos_profesionales_dias,
        validar_centro_costo=validar_centro_costo,
    )

    # Cleanup archivo temporal
    cleanup_temp_excel(temp_path)

    # Verificar si hay columnas faltantes ANTES de procesar (coincidencia exacta)
    problemas_data = export_result.get("data", {}).get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])
    
    # Cleanup archivo temporal ANTES de retornar (sea éxito o error)
    cleanup_temp_excel(temp_path)
    
    if missing_columns:
        # Columnas faltantes - no procesar, devolver error inmediatamente
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing_columns)}. "
                f"Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing_columns,  # Para mostrar al usuario qué falta
        }), 200

    if export_result["status"] == "success":
        # Extraer info de problemas - formato NORMALIZADO 6 columnas
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})
        
        # Obtener filas normalizadas (6 columnas fijas)
        normalized_rows = problemas_dict.get("normalizados", [])
        total_errores = len(normalized_rows)
        
        logger.info("Errores normalizados Odontología: %d total", total_errores)
        
        # Armar errores agrupados por tipo para la respuesta JSON
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

