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
    return render_template("excel_headers.html", **ctx)


@excel_headers_bp.post("/")
def export_cruce_facturas():
    """Procesa el archivo - retorna errores en JSON."""
    uploaded_file = request.files.get("file_upload")
    
    if not uploaded_file or not uploaded_file.filename:
        ctx = build_excel_headers_form_context(
            file="",
            sheet_name=request.form.get("sheet_name"),
            sheet_id_raw=request.form.get("sheet_id"),
            header_row_raw=request.form.get("header_row"),
        )
        ctx["upload_error"] = "Debes seleccionar un archivo"
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
        return render_template("excel_headers.html", **ctx)
    
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
    )

    # Cleanup archivo temporal
    cleanup_temp_excel(temp_path)

    if export_result["status"] == "success":
        output_path = export_result["data"]["output_path"]
        output_name = export_result["data"]["output_file"]
        
        # Extraer info de problemas para mostrar en web
        applied_rules = export_result["data"].get("applied_rules", [])
        revision_info = None
        for rule in applied_rules:
            if rule.get("rule") == "create_revision_sheet":
                revision_info = rule
                break
        
        problemas = revision_info.get("problemas", {}) if revision_info else {}
        
        # Armar lista de errores para mostrar
        errores = []
        for tipo, items in problemas.items():
            if items:
                facturas = []
                for item in items[:20]:
                    # Formato "FACTURA|CENTRO_ACTUAL|CENTRO_DEBERIA"
                    if "|" in str(item):
                        parts = item.split("|")
                        facturas.append({
                            "factura": parts[0],
                            "centro_actual": parts[1],
                            "centro_deberia": parts[2],
                        })
                    else:
                        # Formato viejo
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