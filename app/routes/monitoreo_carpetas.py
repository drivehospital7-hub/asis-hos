"""Blueprint para Monitoreo de Carpetas.

POST /monitoreo-carpetas/scan       → Ejecuta escaneo completo, retorna JSON
GET  /monitoreo-carpetas/download/<filename>  → Descarga reporte Excel generado
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, send_file, session

from app.constants.monitoreo_carpetas import ENV_MONITOREO_ROOTS
from app.services.monitoreo_carpetas.detect_all import detect_all
from app.services.monitoreo_carpetas.report_generator import generate_excel
from app.utils.input_data import output_data_directory

logger = logging.getLogger(__name__)

monitoreo_carpetas_bp = Blueprint("monitoreo_carpetas", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@monitoreo_carpetas_bp.get("/")
def index():
    """React shell for Monitoreo de Carpetas."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "monitoreo_carpetas:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(
        manifest_path,
        "src/pages/monitoreo-carpetas/index.html",
        "file",
    )
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Monitoreo de Carpetas",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@monitoreo_carpetas_bp.post("/scan")
def trigger_scan():
    """Ejecuta el escaneo completo de carpetas configuradas.

    Lee las rutas raíz desde MONITOREO_CARPETAS_ROOTS env var,
    ejecuta detect_all() y genera el reporte Excel.
    Retorna JSON con resultados e indicadores.

    La variable acepta dos formatos:
    - JSON array:  ["\\\\ruta", "\\\\otra"]
    - Separado por ; :  \\\\ruta;\\\\otra
    """
    roots_raw = os.environ.get(ENV_MONITOREO_ROOTS, "").strip()

    if not roots_raw:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [
                f"No hay rutas configuradas. Define la variable de entorno {ENV_MONITOREO_ROOTS}. "
                "Ejemplo para PowerShell:\n"
                f"  $env:{ENV_MONITOREO_ROOTS}='\\\\\\\\192.168.0.124\\facturacion\\MAYO'"
            ],
        }), 200

    # Try JSON first, fallback to semicolon-separated
    if roots_raw.startswith("["):
        try:
            roots: list[str] = json.loads(roots_raw)
        except json.JSONDecodeError as exc:
            logger.error("Error parseando %s como JSON: %s", ENV_MONITOREO_ROOTS, exc)
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Error de configuración: {ENV_MONITOREO_ROOTS} no es JSON válido."],
            }), 500
    else:
        roots = [p.strip() for p in roots_raw.split(";") if p.strip()]

    if not roots:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontraron rutas válidas en la configuración."],
        }), 200

    try:
        scan_result = detect_all(roots)
    except Exception as exc:
        logger.exception("Error durante detect_all")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error interno durante el escaneo: {exc}"],
        }), 500

    # Generate Excel report
    try:
        output_dir = output_data_directory(create=True)
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = output_dir / f"monitoreo_{timestamp}.xlsx"
        generate_excel(scan_result, str(excel_path))
        excel_filename = excel_path.name
    except Exception as exc:
        logger.exception("Error generando reporte Excel")
        excel_filename = None

    # Build response data
    facturas_data = []
    for inv in scan_result.facturas:
        facturas_data.append({
            "filename": inv.filename,
            "facturador": inv.facturador,
            "full_path": inv.full_path,
            "status": inv.status,
            "invoice_type": inv.invoice_type,
            "invoice_code": inv.invoice_code,
        })

    response_data = {
        "facturas": facturas_data,
        "indicadores": dict(scan_result.indicadores),
        "duplicados": scan_result.duplicados,
        "vacias": scan_result.vacias,
        "errores_scan": scan_result.errores_scan,
        "excel_download": excel_filename,
    }

    return jsonify({
        "status": "success",
        "data": response_data,
        "errors": [],
    }), 200


@monitoreo_carpetas_bp.get("/download/<filename>")
def download_report(filename: str):
    """Descarga un reporte Excel generado.

    Valida contra path traversal antes de servir el archivo.
    """
    # Path traversal guard
    clean_name = Path(filename).name
    if clean_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Nombre de archivo no válido."],
        }), 400

    output_dir = output_data_directory()
    file_path = output_dir / clean_name

    if not file_path.exists() or not file_path.is_file():
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Archivo no encontrado."],
        }), 404

    return send_file(
        str(file_path),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=clean_name,
    )
