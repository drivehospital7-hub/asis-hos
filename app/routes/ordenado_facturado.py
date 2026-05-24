"""Route para Ordenado y Facturado.

Cruza el Excel de reporte estándar con el Excel de Ayudas Diagnósticas
para detectar procedimientos no facturados.
Opcional: Excel de Notas Enfermería para detectar traslados.
"""

import logging
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request

from app.services.ordenado_facturado_service import procesar_cruce
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

ordenado_facturado_bp = Blueprint("ordenado_facturado", __name__)


@ordenado_facturado_bp.get("/")
@permiso_requerido("equipos_basicos")
def ordenado_facturado_page():
    """Página de Ordenado y Facturado."""
    return render_template("ordenado_facturado.html")


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

        resultado = procesar_cruce(path_reporte, path_ayudas, path_notas=path_notas)

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
