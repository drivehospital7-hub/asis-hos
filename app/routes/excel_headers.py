from flask import Blueprint, render_template, request

from app.services.excel_headers_page import build_excel_headers_view_context

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
