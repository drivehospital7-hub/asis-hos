"""Servicio de control de errores de urgencias."""

import logging
from typing import Any

import flask
from flask import session
# from flask_login import current_user  # Eliminado: auth es via session

from app.utils.errores_storage import (
    listar_errores,
    crear_error,
    obtener_error,
    actualizar_error,
    eliminar_error,
    listar_imagenes,
    obtener_imagenes_count,
    guardar_imagen,
    eliminar_imagen,
    get_ultima_actualizacion,
    check_cambios,
    normalizar_identidad,
)
from app.utils import users_store

logger = logging.getLogger(__name__)


def _user_identities(user: dict[str, Any]) -> tuple[str, str]:
    """Return canonical and full normalized identities for a DB user."""
    canonical = normalizar_identidad(
        f"{user.get('primer_nombre', '')} {user.get('apellido_1', '')}"
    )
    full = normalizar_identidad(
        " ".join(
            user.get(field, "")
            for field in (
                "primer_nombre",
                "segundo_nombre",
                "apellido_1",
                "apellido_2",
            )
        )
    )
    return canonical, full


def _resolve_owner_identities(sess: dict[str, Any]) -> tuple[str, str] | None:
    """Resolve canonical and full facturador identities from the DB.

    Solo facturadores obtienen identidad; el resto (validador/admin/otros)
    recibe None → ven todas las novedades.
    """
    if sess.get("rol") != "facturador":
        return None
    user = users_store.get_user(sess.get("username", ""))
    if not user:
        return None
    return _user_identities(user)


def _resolve_owner_identity(sess: dict[str, Any]) -> str | None:
    """Resolve the canonical ``primer_nombre + apellido_1`` identity."""
    identities = _resolve_owner_identities(sess)
    return identities[0] if identities else None


def _resolve_responsable_identities(
    responsable: str | None,
) -> tuple[str, str] | None:
    """Resolve a selected responsible to canonical and full DB identities."""
    if not responsable:
        return None

    selected = normalizar_identidad(responsable)
    for user in users_store.get_facturadores():
        if normalizar_identidad(user.get("nombre_completo")) != selected:
            continue
        return _user_identities(user)
    return None


def _resolve_responsable_identity(responsable: str | None) -> str | None:
    """Resolve a selected responsible to the canonical DB identity."""
    identities = _resolve_responsable_identities(responsable)
    return identities[0] if identities else None


def get_opciones(session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Obtener opciones para los selects.

    Los responsables provienen EXCLUSIVAMENTE de usuarios DB con rol
    'facturador' (get_facturadores). No hay fallback a constantes ni JSON.
    """
    try:
        from app.constants import (
            ERROR_TIPO_URGENCIAS,
            ERROR_ESTADO_URGENCIAS,
        )

        facturadores = users_store.get_facturadores()
        responsables = [f["nombre_completo"] for f in facturadores]

        return {
            "status": "success",
            "data": {
                "tipos_error": ERROR_TIPO_URGENCIAS,
                "estados": ERROR_ESTADO_URGENCIAS,
                "responsables": responsables,
            },
            "errors": [],
        }
    except Exception as e:
        logger.exception("[BACK][ERROR] Error obteniendo opciones")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def get_errores(
    tipo_error: str | None = None,
    estado: str | None = None,
    responsable: str | None = None,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Listar errores con filtros + visibilidad por rol.

    - facturador → novedades nuevas con responsable canónico exacto y legacy
      con responsable de al menos dos tokens contenidos en su identidad DB.
    - validador/admin/otros → todas las novedades (owner_identity=None).
    """
    try:
        sess = session if session is not None else flask.session
        owner_identities = _resolve_owner_identities(sess)
        responsable_identities = _resolve_responsable_identities(responsable)
        owner_identity = owner_identities[0] if owner_identities else None
        owner_full_identity = owner_identities[1] if owner_identities else None
        responsable_identity = (
            responsable_identities[0] if responsable_identities else None
        )
        responsable_full_identity = (
            responsable_identities[1] if responsable_identities else None
        )

        errores = listar_errores(
            tipo_error,
            estado,
            responsable,
            owner_identity=owner_identity,
            owner_full_identity=owner_full_identity,
            responsable_identity=responsable_identity,
            responsable_full_identity=responsable_full_identity,
        )
        logger.info(
            "[BACK] Listando errores - tipo: %s, estado: %s, responsable: %s, owner: %s, total: %d",
            tipo_error,
            estado,
            responsable,
            owner_identity,
            len(errores),
        )
        return {"status": "success", "data": {"errores": errores}, "errors": []}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error listando errores")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def get_last_update() -> dict[str, Any]:
    """Obtener timestamp de última modificación."""
    try:
        last = get_ultima_actualizacion()
        return {"status": "success", "data": {"last_update": last}, "errors": []}
    except Exception as e:
        logger.exception("Error obteniendo última actualización")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def check_for_changes(since: str | None = None) -> dict[str, Any]:
    """Verificar si hubo cambios desde un timestamp."""
    try:
        changed, last_update = check_cambios(since)
        return {"status": "success", "data": {"changed": changed, "last_update": last_update}, "errors": []}
    except Exception as e:
        logger.exception("Error verificando cambios")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def add_error(data: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Crear un nuevo error.

    ``created_by`` es auditoría automática: proviene de la sesión
    autenticada, nunca del payload del cliente.
    """
    try:
        sess = session if session is not None else flask.session

        tipo_error = data.get("tipo_error", "").strip() or "Otros"
        factura = (data.get("factura", "").strip() or "").upper()
        observacion = (data.get("observacion", "").strip() or "").upper()
        observacion_facturador = data.get("observacion_facturador", "").strip() or ""
        estado = data.get("estado", "").strip() or "S"
        responsable = data.get("responsable", "").strip() or ""

        validador = f"{sess.get('primer_nombre', '')} {sess.get('apellido_1', '')}".strip()
        created_by = sess.get("username", "")

        nuevo = crear_error(
            tipo_error, factura, observacion, estado, responsable,
            observacion_facturador, validador=validador, created_by=created_by,
        )
        logger.info("[BACK] Error creado con ID: %s", nuevo["id"])
        return {"status": "success", "data": {"error": nuevo}, "errors": []}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error creando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def update_error(error_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Actualizar un error existente."""
    try:
        existente = obtener_error(error_id)
        if not existente:
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        # Permisos de escritura: "*" o "control_urgencias:write" = full access
        user_permisos = session.get("permisos", [])
        is_full_write = "*" in user_permisos or "control_urgencias:write" in user_permisos

        if not is_full_write:
            prohibited = set(data.keys()) - {"estado", "observacion_facturador"}
            if prohibited:
                return {
                    "status": "error",
                    "data": {},
                    "errors": [
                        f"No autorizado. Solo puede cambiar 'estado' y "
                        f"'observacion_facturador'. "
                        f"Campos rechazados: {', '.join(sorted(prohibited))}"
                    ],
                }, 403

        # Solo procesar campos que vienen en el request
        kwargs = {}
        if "tipo_error" in data:
            kwargs["tipo_error"] = data["tipo_error"].strip() if data["tipo_error"] else ""
        if "factura" in data:
            kwargs["factura"] = (data["factura"].strip() if data["factura"] else "").upper()
        if "observacion" in data:
            kwargs["observacion"] = (data["observacion"].strip() if data["observacion"] else "").upper()
        if "observacion_facturador" in data:
            kwargs["observacion_facturador"] = data["observacion_facturador"].strip() if data["observacion_facturador"] else ""
        if "estado" in data:
            kwargs["estado"] = data["estado"].strip() if data["estado"] else ""
        if "responsable" in data:
            kwargs["responsable"] = data["responsable"].strip() if data["responsable"] else ""

        actualizado = actualizar_error(error_id, **kwargs)

        logger.info("[BACK] Error actualizado: %s", error_id)
        return {"status": "success", "data": {"error": actualizado}, "errors": []}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error actualizando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def delete_error(error_id: str) -> dict[str, Any]:
    """Eliminar un error."""
    try:
        eliminado = eliminar_error(error_id)
        if eliminado:
            logger.info("[BACK] Error eliminado: %s", error_id)
            return {"status": "success", "data": {"eliminado": True}, "errors": []}
        return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error eliminando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


# =============================================================================
# Gestión de Imágenes
# =============================================================================

def get_imagenes(error_id: str) -> dict[str, Any]:
    """Listar imágenes."""
    try:
        imagenes = listar_imagenes(error_id)
        count = obtener_imagenes_count(error_id)
        return {"status": "success", "data": {"imagenes": imagenes, "count": count}, "errors": []}
    except Exception as e:
        logger.exception("Error listando imágenes")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def upload_imagen(error_id: str, file) -> dict[str, Any]:
    """Subir imagen."""
    try:
        if not obtener_error(error_id):
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        success, result = guardar_imagen(error_id, file)
        if success:
            logger.info("[BACK] Imagen subida: %s", result)
            return {"status": "success", "data": {"filename": result, "count": obtener_imagenes_count(error_id)}, "errors": []}
        return {"status": "error", "data": {}, "errors": [result]}
    except Exception as e:
        logger.exception("[BACK][ERROR] Error subiendo imagen")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def delete_imagen(error_id: str, filename: str) -> dict[str, Any]:
    """Eliminar imagen."""
    try:
        success, error = eliminar_imagen(error_id, filename)
        if success:
            return {"status": "success", "data": {"count": obtener_imagenes_count(error_id)}, "errors": []}
        return {"status": "error", "data": {}, "errors": [error]}
    except Exception as e:
        logger.exception("Error eliminando imagen")
        return {"status": "error", "data": {}, "errors": [str(e)]}
