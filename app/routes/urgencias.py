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
                    # Para urgencias: formato dict con factura, centro_actual, centro_deberia
                    # o ide_contrato_actual, ide_contrato_deberia
                    if isinstance(item, dict):
                        factura_error = {"factura": item.get("factura", "")}
                        
                        # Agregar campos de centro de costo si existen
                        if "centro_actual" in item and "centro_deberia" in item:
                            factura_error["centro_actual"] = item.get("centro_actual", "")
                            factura_error["centro_deberia"] = item.get("centro_deberia", "")
                        # Agregar campos de IDE Contrato si existen
                        if "ide_contrato_actual" in item and "ide_contrato_deberia" in item:
                            factura_error["ide_contrato_actual"] = item.get("ide_contrato_actual", "")
                            factura_error["ide_contrato_deberia"] = item.get("ide_contrato_deberia", "")
                        
                        facturas.append(factura_error)
                    else:
                        # Formato string
                        facturas.append({
                            "factura": item,
                            "centro_actual": "",
                            "centro_deberia": "",
                        })
                
                errores.append({
                    "tipo": tipo,
                    "cantidad": len(items),
                    "facturas": facturas,
                })
        
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
