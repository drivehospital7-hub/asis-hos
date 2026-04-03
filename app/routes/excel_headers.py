from flask import Blueprint, render_template, request

from app.services.excel_headers_page import (
    build_excel_headers_form_context,
    build_excel_headers_view_context,
)
from app.services.exporter import export_excel_with_cruce_facturas

excel_headers_bp = Blueprint("excel_headers", __name__)


@excel_headers_bp.get("/encabezados")
def excel_headers_page():
    ctx = build_excel_headers_view_context(
        file=request.args.get("file", ""),
        sheet_name=request.args.get("sheet_name"),
        sheet_id_raw=request.args.get("sheet_id"),
        header_row_raw=request.args.get("header_row"),
    )
    return render_template("excel_headers.html", **ctx)


@excel_headers_bp.post("/encabezados/exportar-cruce-facturas")
def export_cruce_facturas():
    ctx = build_excel_headers_form_context(
        file=request.form.get("file", ""),
        sheet_name=request.form.get("sheet_name"),
        sheet_id_raw=request.form.get("sheet_id"),
        header_row_raw=request.form.get("header_row"),
    )
    export_result = export_excel_with_cruce_facturas(
        filename=request.form.get("file", ""),
        sheet_name=request.form.get("sheet_name") or None,
        header_row=int(request.form.get("header_row", "0"))
    )
    return render_template("excel_headers.html", **ctx, export_result=export_result)
