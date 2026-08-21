"""Servicio de integración LAN JSON para control-novedades.

Recibe un payload JSON autenticado por bearer token, fuerza la categoría
"Soportes de Carpeta", resuelve el responsable con la lógica de coincidencia
existente y mantiene el validador (del token) separado del responsable.
Cada envío crea SIEMPRE un registro nuevo: los envíos duplicados son permitidos.
"""

import logging
from typing import Any

from app.constants.urgencias import ERROR_TIPO_URGENCIAS
from app.services.control_errores_service import (
    _resolve_responsable_identity,
)
from app.utils import errores_storage

logger = logging.getLogger(__name__)

# Categoría forzada por el servidor; el cliente NO la controla.
FORCED_CATEGORY = "Soportes de Carpeta"

# Campos requeridos y sus tipos (strings no vacíos).
REQUIRED_FIELDS = ("factura", "observacion", "responsable")


def _resolve_responsable(raw: str) -> str | None:
    """Resuelve el responsable crudo a su identidad DB canónica."""
    return _resolve_responsable_identity(raw)


def _persist(data: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    """Persiste el registro de forma atómica.

    Usa ``errores_storage.crear_error``: el write corre bajo el lock del
    almacén, evitando pérdidas de actualizaciones entre envíos concurrentes.
    Cada llamada crea SIEMPRE un registro nuevo (los duplicados se permiten).

    Returns:
        El registro persistido.
    """
    sess = session or {}
    responsable = data["responsable"]
    validador = f"{sess.get('primer_nombre', '')} {sess.get('apellido_1', '')}".strip()
    created_by = sess.get("username", "")
    return errores_storage.crear_error(
        tipo_error=data["tipo_error"],
        factura=(data["factura"] or "").upper(),
        observacion=(data["observacion"] or "").upper(),
        observacion_facturador=data.get("observacion_facturador", "") or "",
        estado=data.get("estado", "S"),
        responsable=responsable,
        validador=validador,
        created_by=created_by,
    )


def _validate(payload: dict[str, Any]) -> list[str]:
    """Valida el esquema del payload. Devuelve lista de errores (vacía si OK)."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo requerido faltante o inválido: '{field}'")
    return errors


def submit(payload: dict[str, Any], session: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
    """Procesa un envío de integración y devuelve (envelope, status_code).

    El validador y created_by provienen de la sesión sintética del token; el
    responsable se normaliza contra la DB. Nunca se confía en la categoría ni
    en la identidad del validador enviada por el cliente.
    """
    try:
        payload = payload or {}

        # 1. Validación de esquema
        errors = _validate(payload)
        if errors:
            return {"status": "error", "data": {}, "errors": errors}, 400

        # 2. Categoría forzada (el servidor descarta cualquier valor del cliente)
        categoria = FORCED_CATEGORY
        if categoria not in ERROR_TIPO_URGENCIAS:
            categoria = "Otros"

        # 3. Resolución del responsable (rechazo si es ambiguo/sin coincidencia)
        responsable = _resolve_responsable(payload["responsable"])
        if not responsable:
            return {
                "status": "error",
                "data": {},
                "errors": [
                    "Responsable no resuelto a un usuario DB único (ambiguo o sin coincidencia)"
                ],
            }, 400

        # 4. Construcción del registro (identidad de validador del token)
        record_data = {
            "tipo_error": categoria,
            "factura": payload["factura"],
            "observacion": payload["observacion"],
            "observacion_facturador": payload.get("observacion_facturador", "") or "",
            "responsable": responsable,
        }

        # 5. Persistencia atómica (siempre crea un registro nuevo)
        nuevo = _persist(record_data, session)
        logger.info("[BACK] Integración: novedad %s persistida", nuevo["id"])
        return {"status": "success", "data": {"error": nuevo}, "errors": []}, 201
    except Exception as e:
        logger.exception("[BACK][ERROR] Error en integración de novedad")
        return {"status": "error", "data": {}, "errors": [str(e)]}, 500
