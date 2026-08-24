"""Routes para control de errores de urgencias."""

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, send_from_directory, session

from app.services.control_errores_service import (
    get_opciones,
    get_errores,
    add_error,
    update_error,
    delete_error,
    get_imagenes,
    upload_imagen,
    delete_imagen,
    get_ultima_actualizacion,
    check_cambios,
)
from app.services.control_errores_export import build_errores_export_workbook, filename_export

from app.constants import IMAGENES_DIR, IMAGENES_SCOPES
from app.utils.auth import permiso_requerido
from app.utils.errores_storage import obtener_error

logger = logging.getLogger(__name__)

control_errores_bp = Blueprint("control_errores", __name__)


def _validar_scope() -> tuple[str | None, tuple | None]:
    """Lee ``?scope=`` y lo valida contra el allowlist (R2/D2).

    El scope alimenta un componente de ruta en storage, así que todo valor
    fuera de ``IMAGENES_SCOPES`` se rechaza acá (400) ANTES de tocar el
    filesystem. Default "" = observación (comportamiento legacy).

    Returns:
        (scope, None) si es válido; (None, respuesta_json_400) si no.
    """
    scope = request.args.get("scope", "")
    if scope not in IMAGENES_SCOPES:
        return None, (
            jsonify({"status": "error", "data": {}, "errors": ["scope inválido"]}),
            400,
        )
    return scope, None


def _validar_error_id(error_id: str) -> tuple[bool, tuple | None]:
    """Rechaza IDs que no son un único componente de registro."""
    if not error_id or error_id in {".", ".."} or Path(error_id).name != error_id:
        return False, (jsonify({"status": "error", "data": {}, "errors": ["Error no encontrado"]}), 404)
    return True, None


def _validar_permiso_imagen(scope: str) -> tuple[bool, tuple | None]:
    """Valida el permiso de subir/eliminar adjuntos según el scope (FA-4, D15).

    - scope ``facturador``: permitido a quien tenga ``control_urgencias``
      (con o sin ``:write``) o admin (``*``).
    - scope ``""`` (observación): se requiere ``control_urgencias:write``
      (o admin).

    El rol ``responsable_facturacion`` NO otorga acceso al flujo de imágenes.

    Returns:
        (True, None) si está permitido; (False, respuesta_json_403) si no.
    """
    permisos = session.get("permisos", [])
    if "*" in permisos:
        return True, None
    if scope == "facturador":
        allowed = "control_urgencias" in permisos
    else:
        allowed = "control_urgencias:write" in permisos
    if not allowed:
        return False, (
            jsonify({"status": "error", "data": {}, "errors": ["Permiso denegado"]}),
            403,
        )
    return True, None


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


@control_errores_bp.get("/control-novedades")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def control_errores_page():
    """Página principal del control de errores (Jinja2)."""
    return render_template("control_errores.html")


@control_errores_bp.get("/api/control-errores/opciones")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def listar_opciones():
    """Obtener opciones para los selects."""
    return jsonify(get_opciones())


@control_errores_bp.get("/api/control-errores")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def listar_errores():
    """Listar errores con filtros (visibilidad por rol de sesión)."""
    tipo_error = request.args.get("tipo_error")
    estado = request.args.get("estado")
    responsable = request.args.get("responsable")
    area = request.args.get("area")
    validador = request.args.get("validador")

    return jsonify(get_errores(
        tipo_error, estado, responsable, area=area, session=dict(session),
        validador=validador,
    ))


@control_errores_bp.get("/api/control-errores/export")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def exportar_errores():
    """Exportar errores filtrados a Excel (.xlsx) con adjuntos como links."""
    tipo_error = request.args.get("tipo_error")
    estado = request.args.get("estado")
    responsable = request.args.get("responsable")
    area = request.args.get("area")
    validador = request.args.get("validador")
    mes = request.args.get("mes")

    result = get_errores(
        tipo_error, estado, responsable, area=area, session=dict(session),
        validador=validador,
    )

    if result["status"] != "success":
        return jsonify(result), 400

    errores = result["data"].get("errores", [])
    if mes:
        errores = [
            e for e in errores if str(e.get("creado_en", ""))[:7] == mes
        ]

    if not errores:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No hay datos para exportar"],
        }), 400

    configured = (current_app.config.get("EXPORT_BASE_URL") or "").strip()
    base_url = configured if configured else request.host_url
    if not base_url.endswith("/"):
        base_url += "/"

    buffer = build_errores_export_workbook(errores, base_url)

    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename_export(mes),
    )


@control_errores_bp.get("/api/control-errores/changes")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def check_changes():
    """Verificar si hubo cambios desde el último poll."""
    since = request.args.get("since")
    changed, last_update = check_cambios(since)
    return jsonify({
        "status": "success",
        "data": {
            "changed": changed,
            "last_update": last_update
        },
        "errors": []
    })


@control_errores_bp.post("/api/control-errores")
@permiso_requerido("control_urgencias:write")
def crear_error():
    """Crear un nuevo error (created_by automático desde la sesión)."""
    data = request.get_json() or {}
    return jsonify(add_error(data, session=dict(session)))


@control_errores_bp.put("/api/control-errores/<error_id>")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def actualizar_error(error_id: str):
    """Actualizar un error existente."""
    data = request.get_json() or {}
    result = update_error(error_id, data)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@control_errores_bp.delete("/api/control-errores/<error_id>")
@permiso_requerido("control_urgencias:write")
def eliminar_error(error_id: str):
    """Eliminar un error."""
    valid, err = _validar_error_id(error_id)
    if not valid:
        return err
    return jsonify(delete_error(error_id))


# =============================================================================
# Gestión de Imágenes
# =============================================================================

@control_errores_bp.get("/api/control-errores/<error_id>/imagenes")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def listar_imagenes(error_id: str):
    """Listar imágenes (scope opcional: "" observación | "facturador")."""
    valid, err = _validar_error_id(error_id)
    if not valid:
        return err
    scope, err = _validar_scope()
    if err:
        return err
    if not obtener_error(error_id):
        return jsonify({"status": "error", "data": {}, "errors": ["Error no encontrado"]}), 404
    username = session.get("username")
    is_admin = "*" in session.get("permisos", [])
    return jsonify(get_imagenes(error_id, scope, username=username, is_admin=is_admin))


@control_errores_bp.post("/api/control-errores/<error_id>/imagenes")
@permiso_requerido("control_urgencias", "control_urgencias:write")
def subir_imagen(error_id: str):
    """Subir imagen (scope opcional; permisos por scope, FA-4)."""
    valid, err = _validar_error_id(error_id)
    if not valid:
        return err
    scope, err = _validar_scope()
    if err:
        return err
    valid, err = _validar_permiso_imagen(scope)
    if not valid:
        return err
    if "imagen" not in request.files:
        return jsonify({"status": "error", "data": {}, "errors": ["No se encontró archivo"]})
    file = request.files["imagen"]
    if file.filename == "":
        return jsonify({"status": "error", "data": {}, "errors": ["Archivo vacío"]})
    username = session.get("username")
    result = upload_imagen(error_id, file, scope, username=username)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@control_errores_bp.route("/api/control-errores/<error_id>/imagenes/", methods=["DELETE"])
@permiso_requerido("control_urgencias", "control_urgencias:write")
def eliminar_imagen(error_id: str):
    """Eliminar imagen (scope opcional); permisos por scope (R1)."""
    import urllib.parse
    valid, err = _validar_error_id(error_id)
    if not valid:
        return err
    scope, err = _validar_scope()
    if err:
        return err
    valid, err = _validar_permiso_imagen(scope)
    if not valid:
        return err
    if not obtener_error(error_id):
        return jsonify({"status": "error", "data": {}, "errors": ["Error no encontrado"]}), 404
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"status": "error", "data": {}, "errors": ["filename requerido"]})
    filename = urllib.parse.unquote(filename)
    username = session.get("username")
    is_admin = "*" in session.get("permisos", [])
    result = delete_imagen(error_id, filename, scope, username=username, is_admin=is_admin)
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)


@control_errores_bp.route("/api/control-errores/<error_id>/imagenes/<path:filename>")
def servir_imagen(error_id: str, filename: str):
    """Servir adjunto: público por diseño, sin sesión ni token.

    Los links del Excel exportado deben abrir indefinidamente. La URL lleva el
    error_id (UUID), por lo que no es adivinable; además se valida que el
    archivo sea un adjunto real del registro DENTRO del scope solicitado
    (contra path tricks y borrados cross-scope, R1/FA-6).
    """
    from flask import send_from_directory, abort
    from app.utils.errores_storage import listar_imagenes, _get_imagenes_dir

    valid, err = _validar_error_id(error_id)
    if not valid:
        return err
    scope, err = _validar_scope()
    if err:
        return err

    # Defensa contra path tricks: el archivo debe ser un adjunto real del
    # registro dentro del scope solicitado
    if filename not in listar_imagenes(error_id, scope):
        logger.warning(f"Adjunto no listado para {error_id} (scope={scope!r}): {filename}")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Archivo no encontrado"],
        }), 404

    imagenes_dir = _get_imagenes_dir(error_id, scope)
    filepath = imagenes_dir / filename

    if not filepath.exists():
        logger.warning(f"Imagen no encontrada: {filepath}")
        abort(404)

    logger.info(f"Sirviendo imagen: {filepath}")
    return send_from_directory(imagenes_dir, filename)
