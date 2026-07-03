"""Route para Ordenado y Facturado.

Cruza el Excel de reporte estándar con el Excel de Ayudas Diagnósticas
para detectar procedimientos no facturados.
Opcional: Excel de Notas Enfermería para detectar traslados.
"""

import json
import logging
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.services.ordenado_facturado_service import procesar_cruce
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

ordenado_facturado_bp = Blueprint("ordenado_facturado", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@ordenado_facturado_bp.get("/")
@permiso_requerido("equipos_basicos")
def ordenado_facturado_react():
    """React shell for Ordenado y Facturado."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "equipos_basicos:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/ordenado-facturado/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")

    return render_template(
        "react_shell.html",
        page_title="Ordenado y Facturado",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )




@ordenado_facturado_bp.post("/procesar")
@permiso_requerido("equipos_basicos")
def procesar_ordenado_facturado():
    """Procesa los 2 archivos Excel y cruza datos."""
    archivo_reporte = request.files.get("archivo_reporte")
    archivo_ayudas = request.files.get("archivo_ayudas")
    archivo_notas = request.files.get("archivo_notas")

    if not archivo_reporte or not archivo_ayudas:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Debes subir los 2 archivos Excel"],
        }), 400

    # Archivos obligatorios
    archivos_obligatorios = [archivo_reporte, archivo_ayudas]
    archivos_opcionales = []
    if archivo_notas and archivo_notas.filename:
        archivos_opcionales.append(archivo_notas)

    temp_paths: list[Path] = []
    try:
        for f in archivos_obligatorios + archivos_opcionales:
            tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
            f.save(tmp.name)
            temp_paths.append(Path(tmp.name))
            tmp.close()

        path_reporte = temp_paths[0]
        path_ayudas = temp_paths[1]
        path_notas = temp_paths[2] if len(temp_paths) > 2 else None

        logger.info(
            "Procesando - Reporte: %s | Ayudas: %s | Notas: %s",
            archivo_reporte.filename,
            archivo_ayudas.filename,
            archivo_notas.filename if archivo_notas and archivo_notas.filename else "(no)",
        )

        cerradas = request.form.get("cerradas") == "true"
        resultado = procesar_cruce(
            path_reporte, path_ayudas,
            path_notas=path_notas,
            cerradas=cerradas,
        )

        if resultado["status"] == "error":
            return jsonify(resultado), 400

        return jsonify(resultado)

    except Exception as e:
        logger.exception("Error procesando Ordenado y Facturado")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error inesperado: {e}"],
        }), 500

    finally:
        for p in temp_paths:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
