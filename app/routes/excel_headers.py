import logging

from flask import (
    Blueprint,
    render_template,
    request,
    send_file,
)

from app.services.excel_headers_page import (
    build_excel_headers_form_context,
    build_excel_headers_view_context,
)
from app.services.exporter import export_excel_with_cruce_facturas
from app.utils.input_data import cleanup_temp_excel, resolve_safe_excel_in_input
from app.utils.input_data import save_temp_excel

logger = logging.getLogger(__name__)

excel_headers_bp = Blueprint("excel_headers", __name__)


@excel_headers_bp.get("/")
def excel_headers_page():
    ctx = build_excel_headers_view_context(
        file=request.args.get("file", ""),
        sheet_name=request.args.get("sheet_name"),
        sheet_id_raw=request.args.get("sheet_id"),
        header_row_raw=request.args.get("header_row"),
    )
    return render_template("excel_headers.html", **ctx)


@excel_headers_bp.post("/")
def excel_headers_upload():
    """Maneja upload de archivo y muestra headers (multipart/form-data)."""
    uploaded_file = request.files.get("file_upload")
    
    temp_path = None
    file_param = ""
    
    if uploaded_file and uploaded_file.filename:
        # Usuario subió un archivo
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
        
        # Usar el path temporal como "archivo"
        file_param = str(temp_path)
    else:
        # Usuario eligió archivo del repositorio
        file_param = request.form.get("file", "")

    ctx = build_excel_headers_view_context(
        file=file_param,
        sheet_name=request.form.get("sheet_name"),
        sheet_id_raw=request.form.get("sheet_id"),
        header_row_raw=request.form.get("header_row"),
    )
    
    # Agregar el path temporal al contexto para cleanup después
    if temp_path:
        ctx["temp_file_path"] = str(temp_path)
    
    return render_template("excel_headers.html", **ctx)


@excel_headers_bp.post("/exportar-cruce-facturas")
def export_cruce_facturas():
    """Exporta el CruceFacturas - acepta archivo del repo o archivo subido."""
    # Verificar si hay archivo subido
    uploaded_file = request.files.get("file_upload")
    
    temp_path = None
    filename = ""
    
    if uploaded_file and uploaded_file.filename:
        # Usuario subió un archivo
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
    else:
        # Usuario eligió archivo del repositorio
        filename = request.form.get("file", "")
    
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
    if temp_path:
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
