"""Ruta universal de procesamiento — acepta cualquier Excel y aplica reglas
según el valor de 'Tipo Factura Descripción' en cada fila.

No requiere parámetro de área: el sistema detecta automáticamente qué tipos
de factura están presentes y despacha al orquestador correspondiente.
"""

from __future__ import annotations

import json
import logging

from flask import (
    Blueprint,
    render_template,
    request,
)

from app.services.exporter import detect_problems_only
from app.utils.input_data import cleanup_temp_excel, save_temp_excel
from app.constants import AREA_UNIFICADA
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

procesar_bp = Blueprint("procesar", __name__)


@procesar_bp.get("/")
def procesar_form():
    """Formulario para subir Excel y ver resultados."""
    return render_template("procesar.html")


@procesar_bp.post("/")
@permiso_requerido("urgencias")
def procesar_unificado():
    """Procesa un Excel aplicando reglas según Tipo Factura Descripción.
    Renderiza resultados en tabla + JSON crudo para debugging.
    """
    uploaded_file = request.files.get("file_upload")
    if not uploaded_file or not uploaded_file.filename:
        return render_template("procesar.html", error="Debes seleccionar un archivo")

    temp_path, error = save_temp_excel(uploaded_file)
    if error:
        return render_template("procesar.html", error=error)

    filename = str(temp_path)
    sheet_name = request.form.get("sheet_name") or None

    export_result, status_code = detect_problems_only(
        filename=filename,
        sheet_name=sheet_name,
        area=AREA_UNIFICADA,
    )

    problemas_data = export_result.get("data", {}).get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])

    cleanup_temp_excel(temp_path)

    if missing_columns:
        return render_template(
            "procesar.html",
            error=(
                f"Columnas no encontradas: {', '.join(missing_columns)}. "
                "Verificá que el archivo tenga los encabezados correctos."
            ),
        )

    if export_result["status"] != "success":
        return render_template(
            "procesar.html",
            error=export_result.get("errors", ["Error desconocido"])[0],
        )

    problemas_data = export_result["data"].get("problemas", {})
    problemas_dict = problemas_data.get("problemas", {})

    normalized_rows = problemas_dict.get("normalizados", [])
    tipos_procesados = problemas_data.get(
        "tipos_procesados",
        export_result["data"].get("tipos_procesados", []),
    )
    total_errores = len(normalized_rows)

    from itertools import groupby

    errores = []
    MAX_POR_TIPO = 50

    all_items = []
    for row in normalized_rows:
        all_items.append({
            "tipo_error": row.get("tipo_error", ""),
            "tipo_factura": row.get("tipo_factura", "Sin tipo"),
            "factura": row.get("factura", ""),
            "fec_factura": row.get("fec_factura", ""),
            "responsable_cierra": row.get("responsable_cierra", ""),
            "descripcion": row.get("descripcion", ""),
            "procedimiento": row.get("procedimiento", ""),
            "detalle": row.get("detalle", ""),
            "fecha_cierre_vacia": row.get("fecha_cierre_vacia", False),
        })

    # Agrupar primero por tipo_factura, después por tipo_error
    sorted_by_factura = sorted(all_items, key=lambda r: (r["tipo_factura"], r["tipo_error"]))
    for tipo_factura, factura_group in groupby(sorted_by_factura, key=lambda r: r["tipo_factura"]):
        factura_items = list(factura_group)
        tipos = []
        total_factura = 0
        for tipo_error, error_group in groupby(factura_items, key=lambda r: r["tipo_error"]):
            items = list(error_group)
            tipos.append({
                "tipo": tipo_error,
                "tipo_key": "norm_" + tipo_error.lower().replace(" ", "_"),
                "cantidad": len(items),
                "cantidad_mostradas": min(len(items), MAX_POR_TIPO),
                "facturas": items[:MAX_POR_TIPO],
            })
            total_factura += len(items)
        errores.append({
            "tipo_factura": tipo_factura,
            "total": total_factura,
            "tipos": tipos,
        })

    total_categorias = sum(len(f["tipos"]) for f in errores)
    resultados = {
        "errores": errores,
        "total_errores": sum(
            sum(t["cantidad"] for t in f["tipos"]) for f in errores
        ),
        "total_categorias": total_categorias,
        "tipos_procesados": tipos_procesados,
    }

    resultados_json = json.dumps(export_result, indent=2, ensure_ascii=False, default=str)

    return render_template(
        "procesar.html",
        resultados=resultados,
        resultados_json=resultados_json,
    )
