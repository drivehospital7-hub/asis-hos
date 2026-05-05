"""Servicio de control de errores de urgencias."""

import logging
from typing import Any

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
)

logger = logging.getLogger(__name__)


def get_opciones() -> dict[str, list[str]]:
    """Obtener opciones para los selects."""
    from app.constants import (
        ERROR_TIPO_URGENCIAS,
        ERROR_ESTADO_URGENCIAS,
        ERROR_RESPONSABLE_URGENCIAS,
    )

    return {
        "tipos_error": ERROR_TIPO_URGENCIAS,
        "estados": ERROR_ESTADO_URGENCIAS,
        "responsables": ERROR_RESPONSABLE_URGENCIAS,
    }


def get_errores(
    tipo_error: str | None = None,
    estado: str | None = None,
    responsable: str | None = None,
) -> dict[str, Any]:
    """Listar errores con filtros."""
    try:
        errores = listar_errores(tipo_error, estado, responsable)
        logger.info(
            "Listando errores - tipo: %s, estado: %s, responsable: %s, total: %d",
            tipo_error,
            estado,
            responsable,
            len(errores),
        )
        return {"status": "success", "data": {"errores": errores}, "errors": []}
    except Exception as e:
        logger.exception("Error listando errores")
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


def add_error(data: dict[str, Any]) -> dict[str, Any]:
    """Crear un nuevo error."""
    try:
        tipo_error = data.get("tipo_error", "").strip() or "Contrato"
        factura = data.get("factura", "").strip() or ""
        observacion = data.get("observacion", "").strip() or ""
        observacion_facturador = data.get("observacion_facturador", "").strip() or ""
        estado = data.get("estado", "").strip() or "S"
        responsable = data.get("responsable", "").strip() or ""

        nuevo = crear_error(tipo_error, factura, observacion, estado, responsable, observacion_facturador)
        logger.info("Error creado con ID: %s", nuevo["id"])
        return {"status": "success", "data": {"error": nuevo}, "errors": []}
    except Exception as e:
        logger.exception("Error creando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def update_error(error_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Actualizar un error existente."""
    try:
        existente = obtener_error(error_id)
        if not existente:
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        # Solo procesar campos que vienen en el request
        kwargs = {}
        if "tipo_error" in data:
            kwargs["tipo_error"] = data["tipo_error"].strip() if data["tipo_error"] else ""
        if "factura" in data:
            kwargs["factura"] = data["factura"].strip() if data["factura"] else ""
        if "observacion" in data:
            kwargs["observacion"] = data["observacion"].strip() if data["observacion"] else ""
        if "observacion_facturador" in data:
            kwargs["observacion_facturador"] = data["observacion_facturador"].strip() if data["observacion_facturador"] else ""
        if "estado" in data:
            kwargs["estado"] = data["estado"].strip() if data["estado"] else ""
        if "responsable" in data:
            kwargs["responsable"] = data["responsable"].strip() if data["responsable"] else ""

        actualizado = actualizar_error(error_id, **kwargs)

        logger.info("Error actualizado: %s", error_id)
        return {"status": "success", "data": {"error": actualizado}, "errors": []}
    except Exception as e:
        logger.exception("Error actualizando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def delete_error(error_id: str) -> dict[str, Any]:
    """Eliminar un error."""
    try:
        eliminado = eliminar_error(error_id)
        if eliminado:
            logger.info("Error eliminado: %s", error_id)
            return {"status": "success", "data": {"eliminado": True}, "errors": []}
        return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}
    except Exception as e:
        logger.exception("Error eliminando error")
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
            logger.info("Imagen subida: %s", result)
            return {"status": "success", "data": {"filename": result, "count": obtener_imagenes_count(error_id)}, "errors": []}
        return {"status": "error", "data": {}, "errors": [result]}
    except Exception as e:
        logger.exception("Error subiendo imagen")
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