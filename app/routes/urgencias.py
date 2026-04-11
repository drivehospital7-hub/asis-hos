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
from app.utils.input_data import cleanup_temp_excel, save_temp_excel
from app.constants import AREA_URGENCIAS

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

    export_result = export_excel_with_cruce_facturas(
        filename=filename,
        sheet_name=sheet_name,
        header_row=header_row,
        area=AREA_URGENCIAS,
    )

    # Cleanup archivo temporal
    cleanup_temp_excel(temp_path)

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
        
        logger.info("DATOS FINALES - centros_de_costos: %d, ide_contrato: %d", len(centros), len(ide_contrato))

    if export_result["status"] == "success":
        output_path = export_result["data"]["output_path"]
        output_name = export_result["data"]["output_file"]
        
        # Extraer info de problemas - la estructura de detect_all_problems es:
        # { "area": "...", "problemas": { "centros_de_costos": [...], "ide_contrato": [...] }, "totales": {...} }
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})
        
        # Armar lista de errores para mostrar
        errores = []
        
        # Centros de costos
        centros = problemas_dict.get("centros_de_costos", [])
        if centros:
            facturas_centros = []
            for item in centros[:50]:
                facturas_centros.append({
                    "factura": item.get("factura", ""),
                    "centro_actual": item.get("centro_actual", ""),
                    "centro_deberia": item.get("centro_deberia", ""),
                })
                # Log por cada factura con error de centro de costo
                logger.info("FACTURA CentroCosto: %s - Actual: '%s' -> Debería: '%s'",
                           item.get("factura", ""),
                           item.get("centro_actual", ""),
                           item.get("centro_deberia", ""))
            
            errores.append({
                "tipo": "No se encuentra coincidencia con los siguientes centros de costos",
                "cantidad": len(centros),
                "facturas": facturas_centros,
            })
        
        # IDE Contrato
        ide_contrato = problemas_dict.get("ide_contrato", [])
        if ide_contrato:
            facturas_ide = []
            for item in ide_contrato[:50]:
                factura_error = {
                    "factura": item.get("factura", ""),
                    "ide_contrato_actual": item.get("ide_contrato_actual", ""),
                    "ide_contrato_deberia": item.get("ide_contrato_deberia", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "codigo": item.get("codigo", ""),
                    "entidad": item.get("entidad", ""),
                    "nota": item.get("nota", ""),
                }
                facturas_ide.append(factura_error)
                # Log por cada factura con error de IDE Contrato
                logger.info("FACTURA IDEContrato: %s - Código: %s, Entidad: %s - IDE Actual: '%s' -> Debería: '%s'",
                           item.get("factura", ""),
                           item.get("codigo", ""),
                           item.get("entidad", ""),
                           item.get("ide_contrato_actual", ""),
                           item.get("ide_contrato_deberia", ""))
            
            errores.append({
                "tipo": "Problemas de IDE Contrato",
                "cantidad": len(ide_contrato),
                "facturas": facturas_ide,
            })
        
        logger.info("Total errores armador para HTML: %d (%d centros, %d ide_contrato)",
                   len(errores), len(centros), len(ide_contrato))
        
        return jsonify({
            "status": "success",
            "data": {
                "output_file": output_name,
                "download_url": url_for("urgencias.download_urgencias", filename=output_name),
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
