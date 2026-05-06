import logging

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)

from app.services.excel_headers_page import build_excel_headers_form_context
from app.services.exporter import export_excel_with_cruce_facturas
from app.services.responsables import obtener_responsable
from app.utils.input_data import cleanup_temp_excel, save_temp_excel
from app.constants import AREA_URGENCIAS, PROFESIONALES_URGENCIAS

logger = logging.getLogger(__name__)

urgencias_bp = Blueprint("urgencias", __name__)


@urgencias_bp.get("/")
def urgencias_page():
    """Pagina principal del formulario de urgencias."""
    ctx = build_excel_headers_form_context(
        file="",
        sheet_name=request.args.get("sheet_name"),
        sheet_id_raw=request.args.get("sheet_id"),
        header_row_raw=request.args.get("header_row"),
    )
    ctx["profesionales"] = PROFESIONALES_URGENCIAS
    return render_template("urgencias.html", **ctx)


@urgencias_bp.post("/")
def export_urgencias():
    """Procesa el archivo de urgencias - retorna errores en JSON."""
    uploaded_file = request.files.get("file_upload")
    
    if not uploaded_file or not uploaded_file.filename:
        ctx = build_excel_headers_form_context(
            file="",
            sheet_name=request.form.get("sheet_name"),
            sheet_id_raw=request.form.get("sheet_id"),
            header_row_raw=request.form.get("header_row"),
        )
        ctx["upload_error"] = "Debes seleccionar un archivo"
        ctx["profesionales"] = PROFESIONALES_URGENCIAS
        return render_template("urgencias.html", **ctx)
    
    temp_path, error = save_temp_excel(uploaded_file)
    if error:
        ctx = build_excel_headers_form_context(
            file="",
            sheet_name=request.form.get("sheet_name"),
            sheet_id_raw=request.form.get("sheet_id"),
            header_row_raw=request.form.get("header_row"),
        )
        ctx["upload_error"] = error
        ctx["profesionales"] = PROFESIONALES_URGENCIAS
        return render_template("urgencias.html", **ctx)
    
    filename = str(temp_path)
    sheet_name = request.form.get("sheet_name") or None
    header_row = int(request.form.get("header_row", "0"))

    ctx = build_excel_headers_form_context(
        file=filename,
        sheet_name=sheet_name,
        sheet_id_raw=request.form.get("sheet_id"),
        header_row_raw=request.form.get("header_row"),
    )
    ctx["profesionales"] = PROFESIONALES_URGENCIAS

    export_result = export_excel_with_cruce_facturas(
        filename=filename,
        sheet_name=sheet_name,
        header_row=header_row,
        area=AREA_URGENCIAS,
    )

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
        })

    # Debug: logging de la estructura completa
    logger.info("Export result keys: %s", list(export_result.keys()))
    if export_result.get("status") == "success":
        problemas_data = export_result["data"].get("problemas", {})
        logger.info("problemas_data keys: %s", list(problemas_data.keys()))
        logger.info("problemas_data content: %s", problemas_data)
        
        # Extraer info de problemas - la estructura de detect_all_problems es:
        # { "area": "...", "problemas": { "centros_de_costos": [...], "ide_contrato": [...] }, "totales": {...} }
        problemas_dict = problemas_data.get("problemas", {})
        centros = problemas_dict.get("centros_de_costos", [])
        ide_contrato = problemas_dict.get("ide_contrato", [])
        cups_equivalentes = problemas_dict.get("cups_equivalentes", [])
        
        logger.info("DATOS FINALES - centros_de_costos: %d, ide_contrato: %d, cups_equivalentes: %d", len(centros), len(ide_contrato), len(cups_equivalentes))

    if export_result["status"] == "success":
        output_path = export_result["data"]["output_path"]
        output_name = export_result["data"]["output_file"]
        
        # Extraer info de problemas - formato NORMALIZADO 6 columnas
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})
        responsables_map = export_result["data"].get("responsables_map", {})
        
        # Obtener filas normalizadas (6 columnas fijas)
        normalized_rows = problemas_dict.get("normalizados", [])
        totales_por_tipo = problemas_dict.get("totales_por_tipo", {})
        total_errores = len(normalized_rows)
        
        logger.info("Errores normalizados: %d total, por tipo: %s", total_errores, totales_por_tipo)
        
        # Armar errores agrupados por tipo para la respuesta JSON
        from itertools import groupby
        errores = []
        MAX_POR_TIPO = 50
        
        # Pre-calcular todos los items
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
        
        # Agrupar por tipo de error
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
                "output_file": output_name,
                "download_url": url_for("urgencias.download_urgencias", filename=output_name),
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
        })

    return jsonify({
        "status": "error",
        "data": {},
        "errors": export_result.get("errors", []),
    })


@urgencias_bp.get("/download/<path:filename>")
def download_urgencias(filename: str):
    """Descarga el archivo Excel procesado de urgencias."""
    from flask import send_from_directory
    from pathlib import Path
    
    output_dir = Path(__file__).parent.parent / "data" / "output"
    return send_from_directory(
        output_dir,
        filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
