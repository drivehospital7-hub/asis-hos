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
from app.constants import AREA_URGENCIAS, PROFESIONALES_URGENCIAS

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
    ctx["profesionales"] = PROFESIONALES_URGENCIAS
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
        ctx["profesionales"] = PROFESIONALES_URGENCIAS
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
        ctx["profesionales"] = PROFESIONALES_URGENCIAS
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
    ctx["profesionales"] = PROFESIONALES_URGENCIAS

    export_result = export_excel_with_cruce_facturas(
        filename=filename,
        sheet_name=sheet_name,
        header_row=header_row,
        area=AREA_URGENCIAS,
    )

    # Verificar si hay columnas faltantes ANTES de procesar (coincidencia exacta)
    problemas_data = export_result.get("data", {}).get("problemas", {})
    missing_columns = problemas_data.get("missing_columns", [])
    
    # Cleanup archivo temporal ANTES de retornar (sea éxito o error)
    cleanup_temp_excel(temp_path)
    
    if missing_columns:
        # Columnas faltantes - no procesar, devolver error inmediatamente
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"Columnas no encontradas en el Excel: {', '.join(missing_columns)}. "
                f"Verifica que el archivo tenga los encabezados correctos."
            ],
            "missing_columns": missing_columns,  # Para mostrar al usuario qué falta
        })

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
        cups_equivalentes = problemas_dict.get("cups_equivalentes", [])
        
        logger.info("DATOS FINALES - centros_de_costos: %d, ide_contrato: %d, cups_equivalentes: %d", len(centros), len(ide_contrato), len(cups_equivalentes))

    if export_result["status"] == "success":
        output_path = export_result["data"]["output_path"]
        output_name = export_result["data"]["output_file"]
        
        # Extraer info de problemas - la estructura de detect_all_problems es:
        # { "area": "...", "problemas": { "centros_de_costos": [...], "ide_contrato": [...] }, "totales": {...} }
        problemas_data = export_result["data"].get("problemas", {})
        problemas_dict = problemas_data.get("problemas", {})
        
        # Armar lista de errores para mostrar
        errores = []
        
        # Centros de costos - MOSTRAR TODOS los errores (sin deduplicar por factura)
        centros = problemas_dict.get("centros_de_costos", [])
        if centros:
            # No deduplicamos - mostramos todos los errores de cada factura
            facturas_centros = []
            for item in centros[:50]:
                facturas_centros.append({
                    "tipo_factura": item.get("tipo_factura", ""),
                    "factura": item.get("factura", ""),
                    "codigo": item.get("codigo", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "centro_actual": item.get("centro_actual", ""),
                    "centro_deberia": item.get("centro_deberia", ""),
                })
                logger.info("FACTURA CentroCosto: %s - Tipo: %s, Código: %s, Procedimiento: %s - Actual: '%s' -> Debería: '%s'",
                           item.get("factura", ""),
                           item.get("tipo_factura", ""),
                           item.get("codigo", ""),
                           item.get("procedimiento", ""),
                           item.get("centro_actual", ""),
                           item.get("centro_deberia", ""))
            
            errores.append({
                "tipo": "No se encuentra coincidencia con los siguientes centros de costos",
                "tipo_key": "centros_de_costos",
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
                "tipo_key": "ide_contrato",
                "cantidad": len(ide_contrato),
                "facturas": facturas_ide,
            })
        
        # Cups equivalentes
        cups_equiv = problemas_dict.get("cups_equivalentes", [])
        if cups_equiv:
            facturas_cups = []
            for item in cups_equiv[:50]:
                factura_error = {
                    "factura": item.get("factura", ""),
                    "codigo": item.get("codigo", ""),
                    "codigo_equiv": item.get("codigo_equiv", ""),
                    "accion": item.get("accion", ""),
                }
                facturas_cups.append(factura_error)
                logger.info("FACTURA CupsEquiv: %s - Código: %s, Código Equiv: %s - Acción: %s",
                           item.get("factura", ""),
                           item.get("codigo", ""),
                           item.get("codigo_equiv", ""),
                           item.get("accion", ""))
            
            errores.append({
                "tipo": "Cups Equivalentes",
                "tipo_key": "cups_equivalentes",
                "cantidad": len(cups_equiv),
                "facturas": facturas_cups,
            })
        
        # Reglas transversales: Decimales
        decimales = problemas_dict.get("decimales", [])
        if decimales:
            # Ahora cada fila con decimales se incluye (no deduplicar por factura)
            errores.append({
                "tipo": "Decimales",
                "tipo_key": "decimales",
                "cantidad": len(decimales),
                "facturas": decimales[:50],  # Ya es lista de dicts con "factura" y "valores"
            })
        
        # Reglas transversales: Tipo Identificación vs Edad
        tipo_id_edad = problemas_dict.get("tipo_identificacion_edad", [])
        if tipo_id_edad:
            facturas_tipo_id = []
            for item in tipo_id_edad[:50]:
                facturas_tipo_id.append({
                    "factura": item.get("factura", ""),
                    "tipo_actual": item.get("tipo_actual", ""),
                    "tipo_deberia": item.get("tipo_deberia", ""),
                    "edad": item.get("edad", ""),
                })
            errores.append({
                "tipo": "Tipo Identificación",
                "tipo_key": "tipo_identificacion_edad",
                "cantidad": len(tipo_id_edad),
                "facturas": facturas_tipo_id,
            })
        
        # Reglas transversales: Cód Entidad Cobrar vs Entidad Afiliación
        entidad_afiliacion = problemas_dict.get("codigo_entidad_vs_afiliacion", [])
        if entidad_afiliacion:
            facturas_entidad = []
            for item in entidad_afiliacion[:50]:
                facturas_entidad.append({
                    "factura": item.get("factura", ""),
                    "codigo_entidad_cobrar": item.get("codigo_entidad_cobrar", ""),
                    "entidad_afiliacion": item.get("entidad_afiliacion", ""),
                    "codigo_extraido_afiliacion": item.get("codigo_extraido_afiliacion", ""),
                    "problema": item.get("problema", ""),
                })
            errores.append({
                "tipo": "Entidad Cobrar vs Afiliación",
                "tipo_key": "codigo_entidad_vs_afiliacion",
                "cantidad": len(entidad_afiliacion),
                "facturas": facturas_entidad,
            })
        
        # Profesionales (Urgencias)
        profesionales = problemas_dict.get("profesionales", [])
        if profesionales:
            facturas_profesionales = []
            for item in profesionales[:50]:
                factura_error = {
                    "factura": item.get("factura", ""),
                    "codigo_profesional": item.get("codigo_profesional", ""),
                    "nombre": item.get("nombre", ""),
                    "tipo": item.get("tipo", ""),
                    "profesional_area": item.get("profesional_area", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "regla": item.get("regla", ""),
                    "problema": item.get("problema", ""),
                }
                facturas_profesionales.append(factura_error)
                logger.info("FACTURA Profesionales: %s - Área: %s, Procedimiento: %s, Regla: %s, Problema: %s",
                           item.get("factura", ""),
                           item.get("profesional_area", ""),
                           item.get("procedimiento", ""),
                           item.get("regla", ""),
                           item.get("problema", ""))
            
            errores.append({
                "tipo": "Profesionales",
                "tipo_key": "profesionales",
                "cantidad": len(profesionales),
                "facturas": facturas_profesionales,
            })
        
        # MAL CAPITADO
        mal_capitado = problemas_dict.get("mal_capitado", [])
        if mal_capitado:
            facturas_mal = []
            for item in mal_capitado[:50]:
                factura_error = {
                    "factura": item.get("factura", ""),
                    "codigo": item.get("codigo", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "observacion": item.get("observacion", ""),
                }
                facturas_mal.append(factura_error)
                logger.info("FACTURA MAL CAPITADO: %s - Código: %s, Procedimiento: %s, Observación: %s",
                           item.get("factura", ""),
                           item.get("codigo", ""),
                           item.get("procedimiento", ""),
                           item.get("observacion", ""))
            
            errores.append({
                "tipo": "MAL CAPITADO",
                "tipo_key": "mal_capitado",
                "cantidad": len(mal_capitado),
                "facturas": facturas_mal,
            })
        
        # Los códigos sin DB ya están incluídos en ide_contrato con ide_contrato_deberia = "SIN CONTRATO"
        # No necesitamos crear un grupo de error separado
        
        logger.info("Total errores armador para HTML: %d (%d centros, %d ide_contrato, %d decimales, %d tipo_id_edad, %d entidad_afiliacion, %d profesionales)",
                   len(errores), len(centros), len(ide_contrato), len(decimales), len(tipo_id_edad), len(entidad_afiliacion), len(profesionales))
        
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
