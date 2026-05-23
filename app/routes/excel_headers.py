import logging

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)

from app.constants import PROFESIONALES_ODONTOLOGIA
from app.services.excel_headers_page import build_excel_headers_form_context
from app.services.exporter import detect_problems_only
from app.services.processor_gate import rate_limit
from app.utils.auth import permiso_requerido
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

excel_headers_bp = Blueprint("excel_headers", __name__)


@excel_headers_bp.get("/")
@permiso_requerido("odontologia")
def excel_headers_page():
    """Pagina principal del formulario de consumos y servicios."""
    ctx = build_excel_headers_form_context(
        file="",
        sheet_name=request.args.get("sheet_name"),
        sheet_id_raw=request.args.get("sheet_id"),
        header_row_raw=request.args.get("header_row"),
    )
    ctx["profesionales"] = PROFESIONALES_ODONTOLOGIA
    return render_template("excel_headers.html", **ctx)


@excel_headers_bp.post("/")
@rate_limit(10, 60)
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
    equipos_basicos = request.form.get("equipos_basicos") == "on"
    
    logger.info("Procesando archivo - Profesional: %s, Días: %s, Validar Centro Costo: %s, Equipos Básicos: %s, TodosProfesionalesDias: %s", 
                profesional, dias, validar_centro_costo, equipos_basicos, todos_profesionales_dias)
    
    if not uploaded_file or not uploaded_file.filename:
        ctx = build_excel_headers_form_context(
            file="",
            sheet_name=request.form.get("sheet_name"),
            sheet_id_raw=request.form.get("sheet_id"),
            header_row_raw=request.form.get("header_row"),
        )
        ctx["upload_error"] = "Debes seleccionar un archivo"
        ctx["profesionales"] = PROFESIONALES_ODONTOLOGIA
        return render_template("excel_headers.html", **ctx)
    
    temp_path, error = save_temp_excel(uploaded_file)
    if error:
        ctx = build_excel_headers_form_context(
            file="",
            sheet_name=request.form.get("sheet_name"),
            sheet_id_raw=request.form.get("sheet_id"),
            header_row_raw=request.form.get("header_row"),
        )
        ctx["upload_error"] = error
        ctx["profesionales"] = PROFESIONALES_ODONTOLOGIA
        return render_template("excel_headers.html", **ctx)
    
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
        profesional=profesional,
        dias=dias,
        todos_profesionales_dias=todos_profesionales_dias,
        validar_centro_costo=validar_centro_costo,
        equipos_basicos=equipos_basicos,
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

