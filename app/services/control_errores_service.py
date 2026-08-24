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
    obtener_uploader,
    get_ultima_actualizacion,
    check_cambios,
    normalizar_identidad,
)
from app.constants.base import (
    ORGANIZATIONAL_AREAS,
    VALID_AREA_SLUGS,
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
    """Resolve an eligible responsible value to canonical and full DB identities.

    Eligibility is shared with the options endpoint through get_facturadores:
    facturador role or ``responsable_facturacion`` permission.
    """
    if not responsable:
        return None

    selected = normalizar_identidad(responsable)
    selected_tokens = set(selected.split())
    if len(selected_tokens) < 2:
        return None

    eligible_identities = [
        _user_identities(user) for user in users_store.get_facturadores()
    ]
    exact_matches = [
        identities for identities in eligible_identities if identities[0] == selected
    ]
    if exact_matches:
        return exact_matches[0] if len(exact_matches) == 1 else None

    ranked = []
    for identities in eligible_identities:
        full_tokens = set(identities[1].split())
        exact_score = len(selected_tokens & full_tokens)
        partial_score = sum(
            1
            for token in selected_tokens - full_tokens
            if any(token in candidate or candidate in token for candidate in full_tokens)
        )
        score = (exact_score, partial_score)
        if score > (0, 0):
            ranked.append((score, identities))

    if not ranked:
        return None
    highest = max(score for score, _ in ranked)
    matches = [identities for score, identities in ranked if score == highest]
    return matches[0] if len(matches) == 1 else None


def _resolve_responsable_identity(responsable: str | None) -> str | None:
    """Resolve a selected responsible to the canonical DB identity."""
    identities = _resolve_responsable_identities(responsable)
    return identities[0] if identities else None


def _build_areas_options() -> list[dict[str, str]]:
    """Devuelve las áreas selectables: SOLO las cuatro canónicas."""
    return [{"slug": a["slug"], "label": a["label"]} for a in ORGANIZATIONAL_AREAS]


def _resolve_area_responsables(area: str | None) -> set[str] | None:
    """Resuelve un slug de área a las identidades canónicas de sus facturadores.

    Returns:
        None → sin filtro (área ausente o slug inválido = no-op).
        set vacío → área válida sin usuarios → resultado vacío.
    """
    if not area or area not in VALID_AREA_SLUGS:
        return None
    return {
        normalizar_identidad(f.get("nombre_completo"))
        for f in users_store.get_facturadores()
        if area in (f.get("areas") or [])
    }


def get_opciones(session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Obtener opciones para los selects.

    Los responsables provienen EXCLUSIVAMENTE de usuarios DB elegibles
    (rol 'facturador' o permiso 'responsable_facturacion'). No hay fallback
    a constantes ni JSON.

    Payload aditivo (sdd Empieza): ``responsables`` sigue plano; se agregan
    ``areas`` (slug+label) y ``responsables_detalle`` (nombre → áreas).
    """
    try:
        from app.constants import (
            ERROR_TIPO_URGENCIAS,
            ERROR_ESTADO_URGENCIAS,
        )

        facturadores = users_store.get_facturadores()
        validadores = users_store.get_validadores()
        responsables = [f["nombre_completo"] for f in facturadores]

        return {
            "status": "success",
            "data": {
                "tipos_error": ERROR_TIPO_URGENCIAS,
                "estados": ERROR_ESTADO_URGENCIAS,
                "responsables": responsables,
                "validadores": validadores,
                "areas": _build_areas_options(),
                "responsables_detalle": [
                    {
                        "nombre_completo": f["nombre_completo"],
                        "identidad_completa": " ".join(
                            value.strip()
                            for value in (
                                f.get("primer_nombre", ""),
                                f.get("segundo_nombre", ""),
                                f.get("apellido_1", ""),
                                f.get("apellido_2", ""),
                            )
                            if value and value.strip()
                        ).upper(),
                        "areas": f.get("areas", []),
                    }
                    for f in facturadores
                ],
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
    area: str | None = None,
    session: dict[str, Any] | None = None,
    validador: str | None = None,
) -> dict[str, Any]:
    """Listar errores con filtros + visibilidad por rol.

    - facturador → novedades nuevas con responsable canónico exacto y legacy
      con responsable de al menos dos tokens contenidos en su identidad DB.
    - validador/admin/otros → todas las novedades (owner_identity=None).
    - area (aditivo) → post-filtra por área de los responsables elegibles;
      slug inválido = no-op; área válida sin usuarios = resultado vacío.
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
            validador=validador,
        )

        area_identities = _resolve_area_responsables(area)
        if area_identities is not None:
            errores = [
                e for e in errores
                if normalizar_identidad(e.get("responsable", "")) in area_identities
            ]

        logger.info(
            "[BACK] Listando errores - tipo: %s, estado: %s, responsable: %s, validador: %s, area: %s, owner: %s, total: %d",
            tipo_error,
            estado,
            responsable,
            validador,
            area,
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
        responsable = (_resolve_responsable_identity(responsable) or responsable).upper()

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
            responsable = data["responsable"].strip() if data["responsable"] else ""
            kwargs["responsable"] = (
                _resolve_responsable_identity(responsable) or responsable
            ).upper()

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

def get_imagenes(
    error_id: str,
    scope: str = "",
    username: str | None = None,
    is_admin: bool = False,
) -> dict[str, Any]:
    """Listar imágenes de un error, dentro del scope indicado (D1/R4).

    ``scope=""`` (observación) conserva el comportamiento legacy. Cada ítem
    expone ``{filename, can_delete}`` (FA-9): can_delete es true para admin
    (*) o el dueño registrado (obtener_uploader == username); false para
    ajenos y adjuntos legacy sin dueño.
    """
    try:
        imagenes = listar_imagenes(error_id, scope)
        count = obtener_imagenes_count(error_id, scope)
        items = [
            {
                "filename": filename,
                "can_delete": _puede_eliminar(
                    error_id, filename, scope, username, is_admin
                ),
            }
            for filename in imagenes
        ]
        return {
            "status": "success",
            "data": {"imagenes": items, "count": count},
            "errors": [],
        }
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}, 400
    except Exception as e:
        logger.exception("Error listando imágenes")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def _puede_eliminar(
    error_id: str,
    filename: str,
    scope: str = "",
    username: str | None = None,
    is_admin: bool = False,
) -> bool:
    """¿Puede este usuario eliminar ``filename``? Admin (*) o dueño (FA-8/FA-9)."""
    if is_admin:
        return True
    if not username:
        return False
    return obtener_uploader(error_id, filename, scope) == username


def upload_imagen(
    error_id: str, file, scope: str = "", username: str | None = None
) -> dict[str, Any] | tuple[dict[str, Any], int]:
    """Subir imagen dentro del scope indicado (FA-1/FA-4).

    ``username`` se reenvía a ``guardar_imagen`` para registrar la propiedad
    en el sidecar (FA-7); None mantiene compatibilidad legacy.
    """
    try:
        if not obtener_error(error_id):
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        success, result = guardar_imagen(error_id, file, scope, username=username)
        if success:
            logger.info("[BACK] Imagen subida: %s", result)
            return {"status": "success", "data": {"filename": result, "count": obtener_imagenes_count(error_id, scope)}, "errors": []}
        return {"status": "error", "data": {}, "errors": [result]}
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}, 400
    except Exception as e:
        logger.exception("[BACK][ERROR] Error subiendo imagen")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def delete_imagen(
    error_id: str,
    filename: str,
    scope: str = "",
    username: str | None = None,
    is_admin: bool = False,
) -> dict[str, Any] | tuple[dict[str, Any], int]:
    """Eliminar imagen dentro del scope.

    R1/FA-6/R3: primero se exige ``filename ∈ listar_imagenes(id, scope)``;
    un path trick o nombre no listado → envelope 404 (antes que ownership),
    sin tocar el filesystem.

    FA-8: la decisión de ownership vive en el service (no en storage). Si el
    usuario no es admin (*) ni el dueño registrado → 403 sin tocar storage.
    """
    try:
        if filename not in listar_imagenes(error_id, scope):
            return {"status": "error", "data": {}, "errors": ["Imagen no encontrada"]}, 404
        if not _puede_eliminar(error_id, filename, scope, username, is_admin):
            return {
                "status": "error",
                "data": {},
                "errors": ["Solo el autor puede eliminar el archivo"],
            }, 403
        success, error = eliminar_imagen(error_id, filename, scope)
        if success:
            return {"status": "success", "data": {"count": obtener_imagenes_count(error_id, scope)}, "errors": []}
        return {"status": "error", "data": {}, "errors": [error]}, 404
    except ValueError as e:
        return {"status": "error", "data": {}, "errors": [str(e)]}, 400
    except Exception as e:
        logger.exception("Error eliminando imagen")
        return {"status": "error", "data": {}, "errors": [str(e)]}
