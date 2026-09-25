"""Blueprint para Monitoreo de Carpetas.

GET  /monitoreo-carpetas/config                → Lee configuración de rutas
PUT  /monitoreo-carpetas/config                → Guarda rutas (requiere :write)
POST /monitoreo-carpetas/config/reset          → Restablece a env var (requiere :write)
POST /monitoreo-carpetas/scan                  → Escanea (1°) o devuelve cache (subsiguientes)
POST /monitoreo-carpetas/clear-snapshot        → Elimina el snapshot escaneado y reinicia el watcher
GET  /monitoreo-carpetas/data                  → Retorna datos cacheados (para recarga de página)
GET  /monitoreo-carpetas/download/<filename>   → Descarga reporte Excel generado
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, session

from app.constants.monitoreo_carpetas import (
    ENV_MONITOREO_ROOTS,
    EXCEL_REGEN_THROTTLE_SECS,
    MOVE_ERR_TRAVERSAL,
)
from app.services.monitoreo_carpetas.move_service import (
    execute_move,
    validate_move_request,
)
from app.services.monitoreo_carpetas.watcher import FolderWatcher
from app.utils.auth import permiso_requerido
from app.utils.input_data import output_data_directory
from app.utils.monitoreo_store import get_roots, save_roots

# Module-level FolderWatcher singleton (lazy-init, first call triggers full scan)
_watcher = FolderWatcher()

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


# =============================================================================
# Config endpoints (before scan route per design)
# =============================================================================


@monitoreo_carpetas_bp.get("/config")
def get_config():
    """Lee la configuración actual de rutas raíz.

    Sin verificación de permiso — solo lectura, la visibilidad
    ya está controlada por el permiso monitoreo_carpetas en el sidebar.
    """
    roots, fuente, ultima_actualizacion = get_roots()
    return jsonify({
        "status": "success",
        "data": {
            "roots": roots,
            "fuente": fuente,
            "ultima_actualizacion": ultima_actualizacion,
        },
        "errors": [],
    }), 200


@monitoreo_carpetas_bp.put("/config")
@permiso_requerido("monitoreo_carpetas:write")
def put_config():
    """Guarda las rutas raíz en el store JSON.

    Cuerpo esperado: {"roots": ["//ruta1", "//ruta2"]}
    """
    body = request.get_json(silent=True)
    if not body or "roots" not in body:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["El cuerpo debe contener 'roots' con una lista de strings."],
        }), 422

    roots = body["roots"]
    if not isinstance(roots, list) or not roots or not all(isinstance(r, str) for r in roots):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["roots debe ser una lista no vacía de strings"],
        }), 422

    try:
        save_roots(roots)
    except ValueError as e:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [str(e)],
        }), 422

    # Return updated config
    updated_roots, fuente, ultima_actualizacion = get_roots()
    return jsonify({
        "status": "success",
        "data": {
            "roots": updated_roots,
            "fuente": fuente,
            "ultima_actualizacion": ultima_actualizacion,
        },
        "errors": [],
    }), 200


def _try_ensure_fresh_excel() -> None:
    """Best-effort throttled Excel regen — never breaks the API response."""
    try:
        _watcher.ensure_fresh_excel(throttle_secs=EXCEL_REGEN_THROTTLE_SECS)
    except Exception:
        logger.exception("ensure_fresh_excel falló (best-effort, respuesta intacta)")


def _excel_name(excel_path: str | None) -> str | None:
    """Filename of an Excel path (or None)."""
    return Path(excel_path).name if excel_path else None


@monitoreo_carpetas_bp.post("/scan")
@permiso_requerido("monitoreo_carpetas:write")
def trigger_scan():
    """Ejecuta escaneo completo (1ra vez / ?force=true) o health check.

    Requiere permiso monitoreo_carpetas:write — dispara scans (mutación).
    Lectura (carpetas/last/next/tabla/export) va por GET /data y /download.

    Primera llamada: escaneo completo (el Observer solo arranca si
    ``ENABLE_WATCHDOG_OBSERVER`` está activo; la fuente de verdad es el
    escaneo programado cada 15 min). Llamadas subsiguientes: health
    check liviano del scheduler. `?force=true`: fuerza `first_scan`
    completo ignorando el cache. Sin cache, ejecuta escaneo completo
    de respaldo.
    """
    roots, _fuente, _ultima_actualizacion = get_roots()

    if not roots:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No se encontraron rutas válidas en la configuración."],
        }), 200

    # --- Reset if routes changed since last scan ---
    cached_roots = _watcher.get_roots()
    if cached_roots and set(cached_roots) != set(roots):
        logger.info("Roots changed (%s → %s), resetting watcher", cached_roots, roots)
        _watcher.reset()

    # --- First call (or after reset) or explicit ?force=true: full scan ---
    force = request.args.get("force", "").lower() == "true"
    if _watcher.get_result() is None or force:
        if force:
            logger.info("POST /scan?force=true — full scan bajo demanda")
        try:
            scan_result, excel_filename = _watcher.first_scan(roots)
        except Exception as exc:
            logger.exception("Error durante first_scan")
            return jsonify({
                "status": "error",
                "data": {},
                "errors": [f"Error interno durante el escaneo: {exc}"],
            }), 500

        facturas_data = _build_facturas_data(scan_result)
        health = _watcher.get_health_snapshot()
        response_data = {
            "monitoring": health["monitoring"],
            "message": health["message"],
            "events_count": health.get("events_count", 0),
            "observer_alive": health.get("observer_alive", True),
            "facturas": facturas_data,
            "indicadores": dict(scan_result.indicadores),
            "duplicados": scan_result.duplicados,
            "vacias": scan_result.vacias,
            "errores_scan": scan_result.errores_scan,
            "excel_download": excel_filename,
            "excel_stale": False,
            "scanned_roots": roots,
            "degraded_roots": health.get("degraded_roots", []),
            "last_event_at": health.get("last_event_at"),
            "last_reconcile_at": health.get("last_reconcile_at"),
            "last_scan_at": health.get("last_scan_at"),
            "next_scan_at": health.get("next_scan_at"),
        }
        return jsonify({
            "status": "success",
            "data": response_data,
            "errors": [],
        }), 200

    # --- Subsequent calls: health check ---
    try:
        health = _watcher.health_check()
    except Exception as exc:
        logger.exception("Error durante health_check")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [f"Error interno en health check: {exc}"],
        }), 500

    if health.get("monitoring"):
        # Watchdog alive + roots accesibles — Excel fresco throttled + cache
        _try_ensure_fresh_excel()
        cached = _watcher.get_result()
        if cached is not None:
            facturas_data = _build_facturas_data(cached)
            response_data = {
                "monitoring": True,
                "message": health["message"],
                "events_count": health.get("events_count", 0),
                "observer_alive": health.get("observer_alive", True),
                "degraded_roots": health.get("degraded_roots", []),
                "last_event_at": health.get("last_event_at"),
                "last_reconcile_at": health.get("last_reconcile_at"),
                "last_scan_at": health.get("last_scan_at"),
                "next_scan_at": health.get("next_scan_at"),
                "facturas": facturas_data,
                "indicadores": dict(cached.indicadores),
                "duplicados": cached.duplicados,
                "vacias": cached.vacias,
                "errores_scan": cached.errores_scan,
                "excel_download": _excel_name(cached.excel_path),
                "excel_stale": _watcher.excel_stale,
                "scanned_roots": _watcher.get_roots(),
            }
            return jsonify({
                "status": "success",
                "data": response_data,
                "errors": [],
            }), 200

    if "result" not in health:
        # Degraded roots (SMB desconectado): reportar cache existente
        # como no monitoreado, SIN fallback full scan automático.
        # Excel fresco throttled (best-effort) antes de responder.
        _try_ensure_fresh_excel()
        cached = _watcher.get_result()
        if cached is not None:
            facturas_data = _build_facturas_data(cached)
            response_data = {
                "monitoring": False,
                "message": health.get("message", ""),
                "events_count": health.get("events_count", 0),
                "observer_alive": health.get("observer_alive", False),
                "degraded_roots": health.get("degraded_roots", []),
                "last_event_at": health.get("last_event_at"),
                "last_reconcile_at": health.get("last_reconcile_at"),
                "last_scan_at": health.get("last_scan_at"),
                "next_scan_at": health.get("next_scan_at"),
                "facturas": facturas_data,
                "indicadores": dict(cached.indicadores),
                "duplicados": cached.duplicados,
                "vacias": cached.vacias,
                "errores_scan": cached.errores_scan,
                "excel_download": _excel_name(cached.excel_path),
                "excel_stale": _watcher.excel_stale,
                "scanned_roots": _watcher.get_roots(),
            }
            return jsonify({
                "status": "success",
                "data": response_data,
                "errors": [],
            }), 200
        return jsonify({
            "status": "success",
            "data": {
                "monitoring": False,
                "message": health.get("message", ""),
                "events_count": health.get("events_count", 0),
                "observer_alive": health.get("observer_alive", False),
                "degraded_roots": health.get("degraded_roots", []),
                "last_event_at": health.get("last_event_at"),
                "last_reconcile_at": health.get("last_reconcile_at"),
                "last_scan_at": health.get("last_scan_at"),
                "next_scan_at": health.get("next_scan_at"),
                "facturas": [],
                "indicadores": {},
                "duplicados": [],
                "vacias": [],
                "errores_scan": [],
                "excel_download": None,
                "excel_stale": False,
                "scanned_roots": _watcher.get_roots(),
            },
            "errors": [],
        }), 200

    # Watchdog dead or no cache — fallback full scan was already executed
    result = health["result"]
    excel_filename = health.get("excel_filename")
    facturas_data = _build_facturas_data(result)
    response_data = {
        "monitoring": False,
        "message": health.get("message", ""),
        "events_count": health.get("events_count", 0),
        "observer_alive": health.get("observer_alive", False),
        "degraded_roots": health.get("degraded_roots", []),
        "last_event_at": health.get("last_event_at"),
        "last_reconcile_at": health.get("last_reconcile_at"),
        "last_scan_at": health.get("last_scan_at"),
        "next_scan_at": health.get("next_scan_at"),
        "facturas": facturas_data,
        "indicadores": dict(result.indicadores),
        "duplicados": result.duplicados,
        "vacias": result.vacias,
        "errores_scan": result.errores_scan,
        "excel_download": excel_filename,
        "excel_stale": False,
        "scanned_roots": roots,
    }
    return jsonify({
        "status": "success",
        "data": response_data,
        "errors": [],
    }), 200


@monitoreo_carpetas_bp.post("/clear-snapshot")
@permiso_requerido("monitoreo_carpetas:write")
def clear_snapshot():
    """Elimina el snapshot escaneado y reinicia el watcher.

    Detiene el watchdog, limpia el cache en memoria y borra el archivo
    de snapshot del disco. La próxima vez que se haga clic en Verificar
    se ejecutará un escaneo completo desde cero.
    """
    _watcher.reset()
    logger.info("Snapshot eliminado por el usuario")
    return jsonify({
        "status": "success",
        "data": {"message": "Snapshot eliminado. Hacé clic en Verificar para un nuevo escaneo completo."},
        "errors": [],
    }), 200


@monitoreo_carpetas_bp.get("/data")
def get_cached_data():
    """Retorna datos cacheados del watcher, si existen.
    
    Si las rutas actuales del store difieren de las rutas del watcher,
    retorna cached=False para evitar mostrar datos de un escaneo anterior.

    Permite que la página muestre resultados al recargar
    sin necesidad de hacer un POST /scan.
    """
    result = _watcher.get_result()

    # Check if cached roots match current config
    current_roots, _fuente, _ = get_roots()
    cached_roots = _watcher.get_roots()
    if cached_roots and set(cached_roots) != set(current_roots):
        logger.info("GET /data: roots changed (%s → %s), returning cached=false",
                     cached_roots, current_roots)
        return jsonify({
            "status": "success",
            "data": {"cached": False, "message": "Las rutas cambiaron. Hacé clic en Verificar para re-escanear."},
            "errors": [],
        }), 200

    if result is None:
        return jsonify({
            "status": "success",
            "data": {"cached": False},
            "errors": [],
        }), 200

    facturas_data = _build_facturas_data(result)
    # Excel fresco throttled (best-effort) — único side-effect permitido aquí.
    _try_ensure_fresh_excel()
    result = _watcher.get_result() or result
    facturas_data = _build_facturas_data(result)
    health = _watcher.get_health_snapshot()
    response_data = {
        "cached": True,
        "monitoring": health["monitoring"],
        "message": health["message"],
        "degraded_roots": health["degraded_roots"],
        "observer_alive": health["observer_alive"],
        "events_count": health["events_count"],
        "last_event_at": health["last_event_at"],
        "last_reconcile_at": health["last_reconcile_at"],
        "last_scan_at": health["last_scan_at"],
        "next_scan_at": health["next_scan_at"],
        "facturas": facturas_data,
        "indicadores": dict(result.indicadores),
        "duplicados": result.duplicados,
        "vacias": result.vacias,
        "errores_scan": result.errores_scan,
        "excel_download": _excel_name(result.excel_path),
        "excel_stale": _watcher.excel_stale,
        "scanned_roots": cached_roots,
    }
    return jsonify({
        "status": "success",
        "data": response_data,
        "errors": [],
    }), 200


@monitoreo_carpetas_bp.post("/move")
@permiso_requerido("monitoreo_carpetas:write")
def move_facturas():
    """Move invoice folders in bulk to a destination under configured roots.

    Body: {"sources": ["<full_path>", ...], "dest_dir": "<dir>"}.
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
        logger.warning("[BACK] Move request rejected: %s", error)
        return jsonify({
            "status": "error",
            "data": {},
            "errors": [error],
        }), code

    moved, failed = execute_move(sources, dest_dir, _watcher)
    if not moved and failed:
        return jsonify({
            "status": "error",
            "data": {"moved": moved, "failed": failed},
            "errors": [f"{item['src']}: {item['error']}" for item in failed],
        }), 200
    return jsonify({
        "status": "success",
        "data": {"moved": moved, "failed": failed},
        "errors": [],
    }), 200


def _build_facturas_data(scan_result):
    """Convierte facturas del ScanResult a lista de dicts para JSON response."""
    return [
        {
            "filename": inv.filename,
            "facturador": inv.facturador,
            "full_path": inv.full_path,
            "status": inv.status,
            "invoice_type": inv.invoice_type,
            "invoice_code": inv.invoice_code,
        }
        for inv in scan_result.facturas
    ]


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
