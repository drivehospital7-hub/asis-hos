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
                facturas = []
                for item in items[:50]:
                    # centro_costo viene como dict, tipo_identificacion_edad también
                    if isinstance(item, dict):
                        facturas.append({
                            "factura": item.get("factura", ""),
                            "tipo_actual": item.get("tipo_actual", ""),
                            "tipo_deberia": item.get("tipo_deberia", ""),
                            "edad": item.get("edad", ""),
                            "centro_actual": item.get("centro_actual", ""),
                            "centro_deberia": item.get("centro_deberia", ""),
                            "profesional": item.get("profesional", ""),
                            "fec_factura": item.get("fec_factura", ""),
                        })
                    else:
                        facturas.append({
                            "factura": item,
                            "centro_actual": "",
                            "centro_deberia": "",
                            "profesional": "",
                            "fec_factura": "",
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