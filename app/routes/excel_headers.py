import logging

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
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
    """Exporta el reporte - solo acepta archivos subidos."""
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
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return render_template("excel_headers.html", **ctx, export_result=export_result)