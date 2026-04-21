import logging

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    send_file,
    url_for,
)

from app.constants import PROFESIONALES_ODONTOLOGIA
from app.services.excel_headers_page import build_excel_headers_form_context
from app.services.exporter import export_excel_with_cruce_facturas
from app.utils.input_data import cleanup_temp_excel, save_temp_excel

logger = logging.getLogger(__name__)

excel_headers_bp = Blueprint("excel_headers", __name__)


@excel_headers_bp.get("/")
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

    export_result = export_excel_with_cruce_facturas(
        filename=filename,
        sheet_name=sheet_name,
        header_row=header_row,
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
        })

    if export_result["status"] == "success":
        output_path = export_result["data"]["output_path"]
        output_name = export_result["data"]["output_file"]
        
        # Extraer info de problemas del nuevo campo "problemas"
        problemas_data = export_result["data"].get("problemas", {})
        problemas = problemas_data.get("problemas", {})
        
        # Armar lista de errores para mostrar
        errores = []
        for tipo, items in problemas.items():
            if items:
                # Extraer campos según el tipo de error
                facturas = []
                for item in items[:50]:
                    if isinstance(item, dict):
                        base = {
                            "factura": item.get("factura", ""),
                        }
                        
                        # Agregar campos según el tipo de error
                        if tipo == "decimales":
                            base["valores"] = item.get("valores", "")
                        elif tipo == "doble_tipo_procedimiento":
                            base["tipos"] = item.get("tipos", "")
                        elif tipo == "ruta_duplicada":
                            base["identificacion"] = item.get("identificacion", "")
                            base["facturas"] = item.get("facturas", "")
                            base["cantidad"] = item.get("cantidad", "")
                        elif tipo == "convenio_procedimiento":
                            base["convenio"] = item.get("convenio", "")
                            base["procedimiento"] = item.get("procedimiento", "")
                            base["problema"] = item.get("problema", "")
                        elif tipo == "cantidades_anomalas":
                            base["tipo_procedimiento"] = item.get("tipo_procedimiento", "")
                            base["procedimiento"] = item.get("procedimiento", "")
                            base["cantidad"] = item.get("cantidad", "")
                            base["convenio"] = item.get("convenio", "")
                            base["problema"] = item.get("problema", "")
                        elif tipo == "tipo_identificacion_edad":
                            base["tipo_actual"] = item.get("tipo_actual", "")
                            base["tipo_deberia"] = item.get("tipo_deberia", "")
                            base["edad"] = item.get("edad", "")
                        elif tipo == "centro_costo":
                            base["profesional"] = item.get("profesional", "")
                            base["fec_factura"] = item.get("fec_factura", "")
                            base["centro_actual"] = item.get("centro_actual", "")
                            base["centro_deberia"] = item.get("centro_deberia", "")
                        elif tipo == "codigo_entidad_vs_afiliacion":
                            base["codigo_entidad_cobrar"] = item.get("codigo_entidad_cobrar", "")
                            base["entidad_afiliacion"] = item.get("entidad_afiliacion", "")
                            base["codigo_extraido_afiliacion"] = item.get("codigo_extraido_afiliacion", "")
                            base["problema"] = item.get("problema", "")
                        elif tipo == "ide_contrato":
                            base["codigo"] = item.get("codigo", "")
                            base["cod_entidad"] = item.get("cod_entidad", "")
                            base["ide_actual"] = item.get("ide_actual", "")
                            base["ide_deberia"] = item.get("ide_deberia", "")
                            base["nota"] = item.get("nota", "")
                        
                        facturas.append(base)
                    else:
                        facturas.append({
                            "factura": item,
                        })
                
                # Nombre más legible para mostrar
                tipo_display = tipo
                if tipo == "tipo_identificacion_edad":
                    tipo_display = "Tipo Identificación"
                elif tipo == "doble_tipo_procedimiento":
                    tipo_display = "Doble tipo procedimiento"
                elif tipo == "ruta_duplicada":
                    tipo_display = "Ruta Duplicada"
                elif tipo == "convenio_procedimiento":
                    tipo_display = "Convenio de procedimiento"
                elif tipo == "cantidades_anomalas":
                    tipo_display = "Cantidades"
                elif tipo == "centro_costo":
                    tipo_display = "Centro Costo"
                elif tipo == "codigo_entidad_vs_afiliacion":
                    tipo_display = "Entidad Cobrar vs Afiliación"
                elif tipo == "ide_contrato":
                    tipo_display = "Entidades y contratos"
                
                errores.append({
                    "tipo": tipo_display,
                    "tipo_key": tipo,  # Key original para uso interno
                    "cantidad": len(items),
                    "facturas": facturas,
                })
        
        return jsonify({
            "status": "success",
            "data": {
                "output_file": output_name,
                "download_url": url_for("excel_headers.download_excel", filename=output_name),
                "errores": errores,
                "total_errores": sum(e["cantidad"] for e in errores),
            },
            "errors": [],
        })

    return jsonify({
        "status": "error",
        "data": {},
        "errors": export_result.get("errors", []),
    })


@excel_headers_bp.get("/download/<path:filename>")
def download_excel(filename: str):
    """Descarga el archivo Excel procesado."""
    from flask import send_from_directory
    from pathlib import Path
    
    output_dir = Path(__file__).parent.parent / "data" / "output"
    return send_from_directory(
        output_dir,
        filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )