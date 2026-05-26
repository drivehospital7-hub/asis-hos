"""Ruta universal de procesamiento — acepta cualquier Excel y aplica reglas
según el valor de 'Tipo Factura Descripción' en cada fila.

No requiere parámetro de área: el sistema detecta automáticamente qué tipos
de factura están presentes y despacha al orquestador correspondiente.
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    session,
)

from app.services.exporter import detect_problems_only
from app.services.responsables import obtener_responsable
from app.utils.input_data import cleanup_temp_excel, save_temp_excel
from app.constants import AREA_UNIFICADA
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

procesar_bp = Blueprint("procesar", __name__)


@procesar_bp.post("/")
@permiso_requerido("urgencias")
def procesar_unificado():
    """Procesa un Excel aplicando reglas según Tipo Factura Descripción.

    Acepta cualquier archivo Excel. El sistema identifica los valores de
    'Tipo Factura Descripción' presentes y ejecuta los detectores
    correspondientes a cada tipo (Urgencias, Hospitalización, Intramural,
    Ambulatoria). Las reglas transversales (decimales, tipo documento, etc.)
    se ejecutan una sola vez.
    """
    uploaded_file = request.files.get("file_upload")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Debes seleccionar un archivo"],
        }), 400

    temp_path, error = save_temp_excel(uploaded_file)
    if error:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [error],
        }), 400

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
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing_columns)}. "
                f"Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing_columns,
        }), 200

    if export_result["status"] == "success":
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})
        responsables_map = export_result["data"].get("responsables_map", {})

        normalized_rows = problemas_dict.get("normalizados", [])
        tipos_procesados = problemas_dict.get(
            "tipos_procesados",
            export_result["data"].get("tipos_procesados", []),
        )
        total_errores = len(normalized_rows)

        logger.info(
            "Procesamiento unificado: %d errores en %d tipos",
            total_errores,
            len(tipos_procesados),
        )

        # Armar errores agrupados por tipo
        from itertools import groupby

        errores = []
        MAX_POR_TIPO = 50

        all_items = []
        for row in normalized_rows:
            all_items.append({
                "tipo_error": row.get("tipo_error", ""),
                "factura": row.get("factura", ""),
                "fec_factura": row.get("fec_factura", ""),
                "responsable_cierra": row.get("responsable_cierra", ""),
                "descripcion": row.get("descripcion", ""),
                "procedimiento": row.get("procedimiento", ""),
                "detalle": row.get("detalle", ""),
                "fecha_cierre_vacia": row.get("fecha_cierre_vacia", False),
            })

        normalized_rows_sorted = sorted(all_items, key=lambda r: r["tipo_error"])
        for tipo, group in groupby(normalized_rows_sorted, key=lambda r: r["tipo_error"]):
            items = list(group)
            errores.append({
                "tipo": tipo,
                "tipo_key": "norm_" + tipo.lower().replace(" ", "_"),
                "cantidad": len(items),
                "cantidad_mostradas": min(len(items), MAX_POR_TIPO),
                "facturas": items[:MAX_POR_TIPO],
            })

        return jsonify({
            "status": "success",
            "data": {
                "errores": errores,
                "total_errores": sum(e["cantidad"] for e in errores),
                "tipos_procesados": tipos_procesados,
                "columnas": [
                    "Fec. Factura",
                    "Tipo de error",
                    "Número Factura",
                    "Responsable Cierra",
                    "Descripción",
                    "Procedimiento",
                    "Detalle",
                ],
            },
            "errors": [],
        }), status_code

    return jsonify({
        "status": "error",
        "data": {},
        "errors": export_result.get("errors", []),
    }), status_code
