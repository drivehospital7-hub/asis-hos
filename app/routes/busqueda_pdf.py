"""Blueprint para Búsqueda de Términos en PDF."""

import json
import logging
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.constants import busqueda_pdf as busqueda_pdf_consts
from app.services.busqueda_pdf.sinonimos_storage import cargar_sinonimos, guardar_sinonimos
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

busqueda_pdf_bp = Blueprint("busqueda_pdf", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


def _validar_ruta(ruta: str) -> str | None:
    """Valida que la ruta exista, esté dentro de PDF_BASE_PATH y no tenga path traversal.

    Returns:
        Ruta normalizada si es válida, None si es inválida.
    """
    if not ruta or not ruta.strip():
        return None

    # Bloquear path traversal
    if ".." in ruta:
        return None

    # Normalizar separadores
    ruta_normalizada = ruta.replace("/", os.sep).replace("\\", os.sep)

    # Verificar que esté dentro de PDF_BASE_PATH
    base_normalizada = busqueda_pdf_consts.PDF_BASE_PATH.replace("/", os.sep).replace("\\", os.sep)
    if not ruta_normalizada.startswith(base_normalizada):
        return None

    # Verificar que exista y sea directorio
    if not os.path.isdir(ruta_normalizada):
        return None

    return ruta_normalizada


@busqueda_pdf_bp.get("/busqueda-pdf/")
@permiso_requerido("busqueda_pdf")
def react_shell():
    """React shell for Búsqueda PDF."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/busqueda-pdf/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Búsqueda PDF",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
            "pdf_base_path": busqueda_pdf_consts.PDF_BASE_PATH,
        },
    )


@busqueda_pdf_bp.get("/busqueda-pdf/listar-directorios")
@permiso_requerido("busqueda_pdf")
def listar_directorios():
    """Lista subdirectorios y archivos PDF de una ruta."""
    ruta = request.args.get("ruta", "").strip()

    ruta_valida = _validar_ruta(ruta)
    if ruta_valida is None:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Ruta inválida o fuera de base"],
        }), 400

    try:
        entries = os.listdir(ruta_valida)
    except OSError:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"No se pudo leer el directorio: {ruta}"],
        }), 400

    directorios = []
    pdfs = []

    for entry in sorted(entries):
        entry_path = os.path.join(ruta_valida, entry)
        if os.path.isdir(entry_path):
            directorios.append({
                "nombre": entry,
                "ruta_completa": entry_path,
            })
        elif entry.lower().endswith(".pdf"):
            pdfs.append(entry)

    return jsonify({
        "status": "success",
        "data": {
            "directorios": directorios,
            "pdfs": pdfs,
        },
        "errors": [],
    })


@busqueda_pdf_bp.get("/busqueda-pdf/sinonimos")
@permiso_requerido("busqueda_pdf")
def get_sinonimos():
    """Devuelve los sinónimos persistidos."""
    sinonimos = cargar_sinonimos()
    return jsonify({
        "status": "success",
        "data": {"sinonimos": sinonimos},
        "errors": [],
    })


@busqueda_pdf_bp.post("/busqueda-pdf/sinonimos")
@permiso_requerido("busqueda_pdf")
def save_sinonimos():
    """Guarda los sinónimos enviados desde el frontend."""
    data = request.get_json(silent=True)
    if not data or "sinonimos" not in data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Se requiere el campo 'sinonimos'"],
        }), 400

    sinonimos = data["sinonimos"]
    if not isinstance(sinonimos, dict):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["'sinonimos' debe ser un dict"],
        }), 400

    try:
        guardar_sinonimos(sinonimos)
        return jsonify({
            "status": "success",
            "data": {"sinonimos": sinonimos},
            "errors": [],
        })
    except OSError:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Error al guardar los sinónimos"],
        }), 500


@busqueda_pdf_bp.post("/busqueda-pdf/buscar")
@permiso_requerido("busqueda_pdf")
def buscar():
    """Busca términos en PDFs de una carpeta."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Cuerpo de request inválido"],
        }), 400

    ruta = data.get("ruta", "").strip()
    condicion = data.get("condicion", "").strip()
    transporte = data.get("transporte", "").strip()
    sinonimos = data.get("sinonimos")

    if not ruta:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["La ruta no puede estar vacía"],
        }), 400

    ruta_valida = _validar_ruta(ruta)
    if ruta_valida is None:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Ruta no encontrada: {ruta}"],
        }), 400

    try:
        from app.services.busqueda_pdf.buscador import buscar_en_carpeta

        result = buscar_en_carpeta(ruta_valida, condicion, transporte, sinonimos)

        return jsonify({
            "status": "success",
            "data": result,
            "errors": [],
        })
    except Exception:
        logger.exception("Error en búsqueda de PDFs")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Error interno al procesar la búsqueda"],
        }), 500
