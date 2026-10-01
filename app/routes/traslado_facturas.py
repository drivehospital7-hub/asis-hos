"""Blueprint para Traslado de Facturas.

GET  /traslado-facturas/          → Shell React (permiso monitoreo_carpetas)
POST /traslado-facturas/buscar    → Busca códigos en el cache del watcher (read)
GET  /traslado-facturas/explorar  → Lista subdirectorios bajo raíces (read)
POST /traslado-facturas/trasladar → Mueve/copia carpetas (requiere :write)

Solo delega: search/browse viven en app/services/traslado_facturas/ y
move/copy en app.services.monitoreo_carpetas.move_service. El cache de
facturas se reusa del watcher singleton de monitoreo (sin scan duplicado).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.constants.monitoreo_carpetas import MOVE_ERR_TRAVERSAL
from app.routes.monitoreo_carpetas import get_watcher
from app.services.monitoreo_carpetas.move_service import (
    execute_move,
    validate_move_request,
)
from app.services.traslado_facturas import browse_service, search_service
from app.utils.auth import permiso_requerido
from app.utils.monitoreo_store import get_roots

logger = logging.getLogger(__name__)

traslado_facturas_bp = Blueprint("traslado_facturas", __name__)

__all__ = ["traslado_facturas_bp"]

NO_SCAN_ERROR = "Sin escaneo. Ejecutá Verificar en Monitoreo de Carpetas."
VALID_OPERATIONS = ("move", "copy")


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@traslado_facturas_bp.get("/")
@permiso_requerido("traslado_facturas", "monitoreo_carpetas")
def index():
    """React shell for Traslado de Facturas."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "monitoreo_carpetas:write" in permisos \
        or "traslado_facturas:write" in permisos
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(
        manifest_path,
        "src/pages/traslado-facturas/index.html",
        "file",
    )
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Traslado de Facturas",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "can_write": can_write,
            "username": session.get("username", ""),
            "permisos": permisos,
        },
    )


@traslado_facturas_bp.post("/buscar")
@permiso_requerido("traslado_facturas", "monitoreo_carpetas")
def buscar_api():
    """Busca códigos en cache del watcher + scan fresco de no cubiertas.

    Body: {"codigos": "<cadena>", "raices"?: ["<root>", ...]}.
    Sin `raices` usa la config. Las raíces cubiertas (bajo watcher-roots)
    salen del cache; las no cubiertas se escanean en sync con `detect_all`
    y se mergean para `buscar`. Raíz inexistente/inaccesible → error de
    scan en la respuesta, no 400 (400 solo si `raices`/`codigos` vacíos
    o no-lista).
    """
    body = request.get_json(silent=True)
    if not body or not isinstance(body.get("codigos"), str):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Body must contain 'codigos' string."],
        }), 400
    if not body["codigos"].strip():
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["'codigos' must be a non-empty string."],
        }), 400

    raices = body.get("raices")
    roots, _fuente, _ultima = get_roots()
    if raices is None:
        chosen = list(roots)
    else:
        if not isinstance(raices, list) or not all(
            isinstance(r, str) for r in raices
        ):
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["'raices' must be a list of strings when provided."],
            }), 400
        chosen = [r for r in raices if r.strip()]
        if not chosen:
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["'raices' must be a non-empty list of strings."],
            }), 400

    watcher = get_watcher()
    result = watcher.get_result()
    _cubiertas, no_cubiertas = search_service.split_roots(
        chosen, watcher.get_roots()
    ) if chosen else ([], [])

    frescas: list = []
    errores_scan: list = []
    if no_cubiertas:
        from app.services.monitoreo_carpetas.detect_all import detect_all

        try:
            fresh = detect_all(no_cubiertas)
        except Exception as exc:
            logger.exception("Error en scan fresco de raíces libres")
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Error interno escaneando raíces: {exc}"],
            }), 500
        frescas = list(fresh.facturas)
        errores_scan = list(fresh.errores_scan)

    if result is None and not no_cubiertas:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [NO_SCAN_ERROR],
        }), 200

    cacheadas = list(result.facturas) if result is not None else []
    codigos = search_service.parse_codigos(body["codigos"])
    data = search_service.buscar(
        codigos, cacheadas + frescas, roots=chosen or None
    )
    data["raices"] = roots
    data["raices_buscadas"] = chosen
    data["errores_scan"] = errores_scan
    return jsonify({
        "status": "success",
        "data": data,
        "errors": [],
    }), 200


@traslado_facturas_bp.get("/explorar")
@permiso_requerido("traslado_facturas", "monitoreo_carpetas")
def explorar_api():
    """Lista subdirectorios del servidor bajo las raíces configuradas.

    Query: ?path=<absoluto> (ausente = lista las raíces).
    """
    path = request.args.get("path") or None
    roots, _fuente, _ultima = get_roots()
    if not roots:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No configured roots to browse."],
        }), 422

    data, error = browse_service.list_dirs(path, roots)
    if error is not None:
        code = 400 if error == MOVE_ERR_TRAVERSAL else 422
        logger.warning("[BACK] Explorar rejected: %s", error)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [error],
        }), code
    return jsonify({
        "status": "success",
        "data": data,
        "errors": [],
    }), 200


@traslado_facturas_bp.post("/trasladar")
@permiso_requerido("traslado_facturas:write", "monitoreo_carpetas:write")
def trasladar_api():
    """Mueve o copia carpetas de facturas a un destino.

    Body: {"sources": [...], "dest_dir": "<dir>", "operation"?: "move"|"copy"}.
    Delegates to move_service; this route only parses and envelopes.
    """
    body = request.get_json(silent=True)
    if (
        not body
        or not isinstance(body.get("sources"), list)
        or not isinstance(body.get("dest_dir"), str)
    ):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Body must contain 'sources' list and 'dest_dir' string."],
        }), 422

    operation = body.get("operation", "move")
    if operation not in VALID_OPERATIONS:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"operation must be one of {list(VALID_OPERATIONS)}."],
        }), 422

    sources = body["sources"]
    dest_dir = body["dest_dir"]
    roots, _fuente, _ultima = get_roots()
    if not roots:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No configured roots to validate destination against."],
        }), 422

    error = validate_move_request(sources, dest_dir, roots)
    if error is not None:
        code = 400 if error == MOVE_ERR_TRAVERSAL else 422
        logger.warning("[BACK] Trasladar request rejected: %s", error)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [error],
        }), code

    moved, failed = execute_move(sources, dest_dir, get_watcher(), operation=operation)
    key = "copied" if operation == "copy" else "moved"
    data = {key: moved, "failed": failed}
    if not moved and failed:
        return jsonify({
            "status": "error",
            "data": data,
            "errors": [f"{item['src']}: {item['error']}" for item in failed],
        }), 200
    return jsonify({
        "status": "success",
        "data": data,
        "errors": [],
    }), 200
