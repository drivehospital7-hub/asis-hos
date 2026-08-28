"""Rutas del módulo Exámenes (Lab Prefactura).

Blueprint SIN ``url_prefix`` (precedente ``import_facturas``, D3): las
declaraciones SON las URLs efectivas — ``/examenes``, ``/api/examenes``,
``/api/listado``.

Envelope obligatorio ``{status, data, errors}`` (AGENTS.md / EX-3): los GET
anidan ``data.examenes`` / ``data.listado``; los POST exitosos devuelven
``{status: "success", data: {}, errors: []}``; fallos → ``{status: "error"}``
con ``errors[]`` legible (401/403 los produce el decorador ``permiso_requerido``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session

from app.constants.examenes import (
    DEFAULT_EXAMENES,
    EX_EXAMENES_FILE,
    EX_LISTADO_FILE,
)
from app.utils import examenes_store
from app.utils.auth import permiso_requerido

logger = logging.getLogger(__name__)

examenes_bp = Blueprint("examenes", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extrae un campo del manifest.json de Vite para la entrada dada."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get(entry_key, {}).get(field, "")


def _session_facturador() -> str:
    """Facturador del shell compuesto desde la sesión (EX-21), CERO consultas DB.

    Mismo formato que ``users_store.get_facturadores`` (``nombre_completo``):
    ``primer_nombre`` + ``apellido_1`` en mayúsculas, cada campo con strip
    (idéntico a get_facturadores). Sin campos de nombre → ``username`` en
    mayúsculas; sin ambos → ``""`` (el frontend mapea "" → "—").
    """
    nombre = " ".join(
        n
        for n in [
            session.get("primer_nombre", "").strip(),
            session.get("apellido_1", "").strip(),
        ]
        if n
    ).upper()
    return nombre or session.get("username", "").upper()


def _success(data: dict | None = None):
    """Envelope de éxito (EX-3)."""
    return jsonify({"status": "success", "data": data or {}, "errors": []})


def _error(errors: list[str], status_code: int):
    """Envelope de error con código HTTP (EX-3)."""
    return jsonify({"status": "error", "data": {}, "errors": errors}), status_code


def _save_body(body):
    """Arreglo plano (legacy) u objeto {data, base_hash} (R4-001).

    ``base_hash`` es el SHA-256 canónico del arreglo en el que el cliente
    basó su copia. Devuelve ``(arreglo, base_hash)`` o ``(None, None)``.
    """
    if isinstance(body, list):
        return body, None
    if isinstance(body, dict):
        data = body.get("data")
        base_hash = body.get("base_hash")
        if isinstance(data, list) and (base_hash is None or isinstance(base_hash, str)):
            return data, base_hash
    return None, None


@examenes_bp.route("/examenes")
@permiso_requerido("examenes")
def examenes_react():
    """Shell React del módulo (EX-1). `:write` expande a `examenes` (auth.py)."""
    permisos = session.get("permisos", [])
    can_write = "*" in permisos or "examenes:write" in permisos
    manifest_path = (
        Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    )
    entry_js = _get_manifest_asset(
        manifest_path, "src/pages/examenes/index.html", "file"
    )
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_shell.html",
        page_title="Exámenes — Laboratorio",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
            "can_write": can_write,
            "current_facturador": _session_facturador(),
            "default_examenes": DEFAULT_EXAMENES,
        },
    )


@examenes_bp.route("/api/examenes", methods=["GET"])
@permiso_requerido("examenes")
def get_examenes():
    """GET catálogo → 200 con ``data.examenes`` (EX-3)."""
    return _success({"examenes": examenes_store.get_examenes()})


@examenes_bp.route("/api/examenes", methods=["POST"])
@permiso_requerido("examenes:write")
def save_examenes():
    """POST catálogo (arreglo completo). No-arreglo → 400 (EX-3 deviation).

    Con ``base_hash`` presente y distinto del estado actual → 409 sin escribir
    (concurrencia optimista, R4-001). Sin ``base_hash`` → reemplazo legacy.
    """
    body = request.get_json(silent=True)
    data, base_hash = _save_body(body)
    if data is None:
        return _error(["El cuerpo debe ser un arreglo de exámenes"], 400)
    try:
        result = examenes_store.save_if_unchanged(EX_EXAMENES_FILE, data, base_hash)
    except Exception:
        logger.exception("Error guardando catálogo de exámenes")
        return _error(["Error guardando el catálogo de exámenes"], 500)
    if result == "conflict":
        return _error(
            ["Conflicto: el catálogo cambió desde su última carga. Recargue para ver la versión actual."],
            409,
        )
    return _success()


@examenes_bp.route("/api/listado", methods=["GET"])
@permiso_requerido("examenes")
def get_listado():
    """GET listado → 200 con ``data.listado`` (EX-3)."""
    return _success({"listado": examenes_store.get_listado()})


@examenes_bp.route("/api/listado", methods=["POST"])
@permiso_requerido("examenes:write")
def save_listado():
    """POST listado (arreglo completo). No-arreglo → 400 (EX-3 deviation).

    Con ``base_hash`` presente y distinto del estado actual → 409 sin escribir
    (concurrencia optimista, R4-001). Sin ``base_hash`` → reemplazo legacy.
    """
    body = request.get_json(silent=True)
    data, base_hash = _save_body(body)
    if data is None:
        return _error(["El cuerpo debe ser un arreglo de prefacturas"], 400)
    try:
        result = examenes_store.save_if_unchanged(EX_LISTADO_FILE, data, base_hash)
    except Exception:
        logger.exception("Error guardando el listado de exámenes")
        return _error(["Error guardando el listado de exámenes"], 500)
    if result == "conflict":
        return _error(
            ["Conflicto: el listado cambió desde su última carga. Recargue para ver la versión actual."],
            409,
        )
    return _success()