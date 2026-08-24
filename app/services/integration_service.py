"""Servicio de integración LAN para control-novedades.

Recibe un payload autenticado por bearer token, fuerza la categoría
"Soportes de Carpeta", resuelve el responsable con la lógica de coincidencia
existente y mantiene el validador (del token) separado del responsable.
Cada envío crea SIEMPRE un registro nuevo: los envíos duplicados son permitidos.
Si ya existe un registro con la misma categoría y factura, la respuesta incluye
una advertencia (``ya_existia`` / ``cantidad_existentes``) sin bloquear nada.

Contrato primario (lista): el endpoint acepta ``{"novedades": [...]}`` y
procesa todos los items en una sola request. Cada item se procesa de forma
independiente:

- Un responsable que no resuelve a un usuario DB único rechaza SOLO ese item.
- Un fallo de persistencia en un item lo rechaza a él, sin abortar el lote.

Semántica de respuesta del lote:

- Lote estructuralmente inválido (``novedades`` no es lista, es una lista
  vacía, o un item no es objeto / le falta un campo requerido) → HTTP 400 con
  ``status: "error"``.
- Lote válido, con todos o con algunos items rechazados → HTTP 200 con
  ``status: "success"`` y el detalle por item en ``data.resultados``. Los items
  exitosos NO se revierten ante rechazos de otros items del mismo lote.

Formato heredado (un solo item) se conserva intacto: HTTP 201 con ``data.error``
como registro persistido.
"""

import logging
from typing import Any

from app.constants import IMAGENES_MAX_PER_OBSERVACION
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
    responsable = data["responsable"].upper()
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
    """Valida el esquema del payload (formato heredado de un solo item)."""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Campo requerido faltante o inválido: '{field}'")
    return errors


def _forced_category() -> str:
    """Categoría forzada por el servidor (el cliente nunca la controla)."""
    categoria = FORCED_CATEGORY
    if categoria not in ERROR_TIPO_URGENCIAS:
        categoria = "Otros"
    return categoria


def _contar_existentes(factura: str) -> int:
    """Cuenta registros ya persistidos con la misma categoría y factura.

    Solo advertencia (duplicate detection): el registro nuevo SIEMPRE se crea,
    sin importar el resultado. Compara la factura normalizada tal como se
    persiste (uppercase) para no perder coincidencias.
    """
    return errores_storage.contar_duplicados(
        _forced_category(), (factura or "").upper()
    )


def _validate_items(items: list[Any]) -> list[str]:
    """Valida la estructura de cada item del lote.

    Un item inválido (no objeto o con un campo requerido faltante/incorrecto)
    invalida TODO el lote → 400. Devuelve la lista de errores (vacía si OK).
    """
    errors: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"Item {index}: debe ser un objeto")
            continue
        for field in REQUIRED_FIELDS:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"Item {index}: campo requerido faltante o inválido: '{field}'"
                )
    return errors


def _process_item(item: dict[str, Any], session: dict[str, Any] | None) -> dict[str, Any]:
    """Procesa un item del lote de forma independiente.

    El rechazo por responsable no resuelto (o un fallo de persistencia) solo
    afecta a este item; los demás items del lote continúan procesándose.
    """
    factura = item["factura"]
    try:
        responsable = _resolve_responsable(item["responsable"])
        if not responsable:
            return {
                "factura": factura,
                "status": "error",
                "motivo": (
                    "Responsable no resuelto a un usuario DB único "
                    "(ambiguo o sin coincidencia)"
                ),
            }

        record_data = {
            "tipo_error": _forced_category(),
            "factura": factura,
            "observacion": item["observacion"],
            "observacion_facturador": item.get("observacion_facturador", "") or "",
            "responsable": responsable.upper(),
        }

        existentes = _contar_existentes(factura)
        nuevo = _persist(record_data, session)
        logger.info("[BACK] Integración: novedad %s persistida", nuevo["id"])
        resultado: dict[str, Any] = {
            "factura": factura,
            "status": "success",
            "error": nuevo,
        }
        if existentes:
            logger.info(
                "[BACK] Integración: duplicado detectado (factura %s, %d existente(s))",
                factura,
                existentes,
            )
            resultado["ya_existia"] = True
            resultado["cantidad_existentes"] = existentes
        return resultado
    except Exception as e:
        logger.exception(
            "[BACK][ERROR] Error integrando novedad del lote (factura %s)", factura
        )
        return {"factura": factura, "status": "error", "motivo": str(e)}


def _submit_single(
    payload: dict[str, Any],
    session: dict[str, Any] | None = None,
    imagenes: list | None = None,
) -> tuple[dict[str, Any], int]:
    """Formato heredado: un solo item → HTTP 201 con ``data.error``."""
    # 1. Validación de esquema
    errors = _validate(payload)
    if errors:
        return {"status": "error", "data": {}, "errors": errors}, 400

    if imagenes:
        for image in imagenes:
            valid, image_error = errores_storage.validar_imagen(image)
            if not valid:
                return {
                    "status": "error",
                    "data": {},
                    "errors": [f"Imagen inválida: {image_error}"],
                }, 400

    # 2. Categoría forzada (el servidor descarta cualquier valor del cliente)
    categoria = _forced_category()

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
        "responsable": responsable.upper(),
    }

    # 5. Advertencia de duplicado (no bloquea; el registro se crea igual)
    existentes = _contar_existentes(payload["factura"])

    # 6. Persistencia atómica (siempre crea un registro nuevo)
    nuevo = _persist(record_data, session)
    logger.info("[BACK] Integración: novedad %s persistida", nuevo["id"])
    guardadas = 0
    if imagenes:
        for image in imagenes:
            try:
                saved, image_result = errores_storage.guardar_imagen(
                    nuevo["id"],
                    image,
                    username=(session or {}).get("username"),
                )
            except Exception as error:
                saved, image_result = False, str(error)
            if not saved:
                errores_storage.eliminar_error(nuevo["id"])
                logger.error(
                    "[BACK][ERROR] Fallo guardando imágenes de novedad %s: "
                    "%d/%d guardadas, causa: %s",
                    nuevo["id"],
                    guardadas,
                    len(imagenes),
                    image_result,
                )
                return {
                    "status": "error",
                    "data": {},
                    "errors": [
                        f"No se pudieron guardar todas las imágenes: "
                        f"{guardadas} de {len(imagenes)} guardada(s), fallo: "
                        f"{image_result}"
                    ],
                }, 500
            guardadas += 1
        logger.info(
            "[BACK] Integración: %d imagen(es) guardada(s) para novedad %s",
            guardadas,
            nuevo["id"],
        )
    if existentes:
        logger.info(
            "[BACK] Integración: duplicado detectado (factura %s, %d existente(s))",
            payload["factura"],
            existentes,
        )
        nuevo["ya_existia"] = True
        nuevo["cantidad_existentes"] = existentes
    return {"status": "success", "data": {"error": nuevo}, "errors": []}, 201


def _submit_batch(
    payload: dict[str, Any], session: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int]:
    """Contrato primario: ``{"novedades": [...]}`` → HTTP 200 con resultados por item.

    La validez estructural del lote es all-or-nothing (400); los rechazos por
    responsable no resuelto (o fallo de persistencia) son por item y se reportan
    en ``data.resultados`` sin revertir los items ya procesados.
    """
    novedades = payload.get("novedades")
    if not isinstance(novedades, list):
        return {
            "status": "error",
            "data": {},
            "errors": ["Campo 'novedades' debe ser una lista"],
        }, 400
    if not novedades:
        return {
            "status": "error",
            "data": {},
            "errors": ["La lista 'novedades' no puede estar vacía"],
        }, 400

    structural_errors = _validate_items(novedades)
    if structural_errors:
        return {"status": "error", "data": {}, "errors": structural_errors}, 400

    resultados: list[dict[str, Any]] = []
    procesadas = 0
    rechazadas = 0
    for item in novedades:
        resultado = _process_item(item, session)
        if resultado["status"] == "success":
            procesadas += 1
        else:
            rechazadas += 1
        resultados.append(resultado)

    data = {
        "procesadas": procesadas,
        "rechazadas": rechazadas,
        "resultados": resultados,
    }
    return {"status": "success", "data": data, "errors": []}, 200


def submit(
    payload: dict[str, Any],
    session: dict[str, Any] | None = None,
    imagenes: list | None = None,
) -> tuple[dict[str, Any], int]:
    """Procesa un envío de integración y devuelve (envelope, status_code).

    ``imagenes`` (hasta ``IMAGENES_MAX_PER_OBSERVACION`` por registro) solo se
    admite para el registro individual; el contrato JSON de lote se conserva
    cuando no hay archivos adjuntos.
    - Si el payload trae ``novedades`` (lista) → contrato de lote (HTTP 200).
    - Si no → formato heredado de un solo item (HTTP 201).

    El validador y created_by provienen de la sesión sintética del token; el
    responsable se normaliza contra la DB. Nunca se confía en la categoría ni
    en la identidad del validador enviada por el cliente.
    """
    try:
        payload = payload or {}

        if "novedades" in payload:
            if imagenes:
                return {
                    "status": "error",
                    "data": {},
                    "errors": [
                        "Las imágenes solo pueden enviarse con un registro individual"
                    ],
                }, 400
            return _submit_batch(payload, session)

        if imagenes is not None and len(imagenes) > IMAGENES_MAX_PER_OBSERVACION:
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Máximo {IMAGENES_MAX_PER_OBSERVACION} imágenes por registro"
                ],
            }, 400

        return _submit_single(payload, session, imagenes)
    except Exception as e:
        logger.exception("[BACK][ERROR] Error en integración de novedades")
        return {"status": "error", "data": {}, "errors": [str(e)]}, 500
