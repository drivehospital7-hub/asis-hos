"""Servicio de control de errores de urgencias."""

import logging
import re
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
)

from app.utils.users_store import list_users

logger = logging.getLogger(__name__)


# =============================================================================
# Permission helpers (role resolution + ownership checks)
# Used by add_error(), update_error(), delete_error(), get_errores()
# =============================================================================


def _resolve_effective_role(
    permisos: list[str] | None = None,
    rol: str | None = None,
) -> str:
    """Resolve effective role from session permisos and rol.

    Priority:
        1. ``"*"`` in permisos  → ``"admin"``
        2. any ``:write`` suffix → ``"write"``
        3. fallback to session rol → ``"read"`` if missing
    """
    if permisos and "*" in permisos:
        return "admin"
    if permisos and any(p.endswith(":write") for p in permisos):
        return "write"
    return rol if rol else "read"


def _can_edit(record: dict, effective_role: str, username: str) -> bool:
    """Determine whether a user can edit a specific record.

    - admin/auditor/write → always True
    - facturador → record's ``responsable_rol == "MEDICO"``
      OR ``created_by == username``
    - medico → only if ``created_by == username``
    - read / unknown → False
    - Legacy (``created_by`` is None) → only admin/auditor/write;
      facturador also allowed if ``responsable_rol == "MEDICO"``
    """
    if effective_role in ("admin", "auditor", "write"):
        return True
    if effective_role == "facturador":
        if record.get("responsable_rol") == "MEDICO":
            return True
        if record.get("created_by") == username:
            return True
        return False
    if effective_role == "medico":
        return record.get("created_by") == username
    return False


def _can_delete(record: dict, effective_role: str) -> bool:
    """Determine whether a user can delete a specific record.

    - admin/auditor/write → always True
    - facturador → only if ``responsable_rol == "MEDICO"``
    - medico / read / unknown → False
    """
    if effective_role in ("admin", "auditor", "write"):
        return True
    if effective_role == "facturador":
        return record.get("responsable_rol") == "MEDICO"
    return False


def _can_create_for(target_rol: str, effective_role: str) -> bool:
    """Determine whether a user can create records for a given target role.

    - admin/auditor/write → any target
    - facturador → only ``"medico"`` (case-insensitive)
    - medico / read / unknown → False
    """
    if effective_role in ("admin", "auditor", "write"):
        return True
    if effective_role == "facturador":
        return target_rol.lower() == "medico"
    return False


def _has_full_write_access(
    effective_role: str,
    record: dict,
    username: str,
) -> bool:
    """Determine whether the user has FULL write access (all fields) on a record.

    - admin/auditor/write → always True
    - facturador → True if ``_can_edit`` passes (médico record or own)
    - medico / read / others → False (partial only)
    """
    if effective_role in ("admin", "auditor", "write"):
        return True
    if effective_role == "facturador":
        return _can_edit(record, effective_role, username)
    return False


def _build_user_data(roles_filter: set[str] | None = None
                     ) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Construye listas de responsables, nombres completos y roles desde los usuarios.

    Args:
        roles_filter: si se pasa, solo incluye usuarios con rol en este set.
                      Si es None, incluye todos los usuarios con primer_nombre.

    Returns:
        (responsables, responsables_nombres_completos, responsables_roles)
    """
    usuarios = list_users()
    if not usuarios:
        from app.constants import (
            ERROR_RESPONSABLE_URGENCIAS,
            ERROR_RESPONSABLE_ROLES,
            RESPONSABLE_NOMBRES_COMPLETOS,
        )
        logger.warning("No hay usuarios en users.json, usando fallback hardcodeado")
        return (
            list(ERROR_RESPONSABLE_URGENCIAS),
            dict(RESPONSABLE_NOMBRES_COMPLETOS),
            {k: v.upper() for k, v in ERROR_RESPONSABLE_ROLES.items()},
        )

    responsables = []
    nombres_completos = {}
    roles = {}
    for u in usuarios:
        if roles_filter and u.get("rol") not in roles_filter:
            continue
        primer_nombre = (u.get("primer_nombre") or "").strip()
        if not primer_nombre:
            continue
        apellido_1 = (u.get("apellido_1") or "").strip()
        nombre_completo = " ".join(n for n in [primer_nombre, apellido_1] if n).upper()

        responsables.append(nombre_completo)

        nombre_full = " ".join(
            p for p in [
                u.get("primer_nombre", ""),
                u.get("segundo_nombre", ""),
                u.get("apellido_1", ""),
                u.get("apellido_2", ""),
            ] if p
        ).upper()
        nombres_completos[nombre_completo] = nombre_full
        roles[nombre_completo] = u.get("rol", "-").upper()

    return responsables, nombres_completos, roles


def get_opciones() -> dict[str, list[str] | dict[str, str]]:
    """Obtener opciones para los selects.

    El dropdown de responsables solo incluye usuarios con rol
    ``"facturador"`` o ``"medico"``. Los roles se proveen como mapa
    para que el frontend pueda actualizar la celda Rol dinámicamente.
    Si no hay usuarios registrados, se usa el fallback hardcodeado.
    """
    from app.constants import (
        ERROR_TIPO_URGENCIAS,
        ERROR_ESTADO_URGENCIAS,
    )

    responsables, responsables_nombres_completos, responsables_roles = _build_user_data(
        roles_filter={"facturador", "medico"},
    )

    return {
        "tipos_error": ERROR_TIPO_URGENCIAS,
        "estados": ERROR_ESTADO_URGENCIAS,
        "responsables": responsables,
        "responsables_nombres_completos": responsables_nombres_completos,
        "responsables_roles": responsables_roles,
    }


def get_errores(
    tipo_error: str | None = None,
    estado: str | None = None,
    responsable: str | None = None,
    rol: str | None = None,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Listar errores con filtros.

    Enriches each error with ``responsable_rol`` from todos los usuarios
    del sistema usando un mapa ``nombre_completo → rol``.
    El filtro ``rol`` se aplica después del enriquecimiento.

    Performs role-based filtering (PM1/R13) and attaches per-record
    ``can_edit`` / ``can_delete`` flags (PM6).

    Args:
        session: optional session dict for testability; falls back to ``flask.session``.
    """
    try:
        sess = session if session is not None else flask.session

        errores = listar_errores(tipo_error, estado, responsable)
        logger.info(
            "Listando errores - tipo: %s, estado: %s, responsable: %s, rol: %s, total: %d",
            tipo_error,
            estado,
            responsable,
            rol,
            len(errores),
        )

        # Build rol_map from ALL system users (sin filtro de rol)
        _, _, responsables_roles = _build_user_data()
        for error in errores:
            # Normalizar: sacar espacios extra del stored value (viene de formato viejo)
            responsable_norm = re.sub(r'\s+', ' ', error.get("responsable", "").strip())
            error["responsable_rol"] = responsables_roles.get(responsable_norm, "-")

        # Filtrar por rol (post-enriquecimiento) — legacy filter param
        if rol:
            errores = [e for e in errores if e.get("responsable_rol", "") == rol]

        # ── PM1 / R13: Role-based filtering ───────────────────────────
        permisos = sess.get("permisos", [])
        session_rol = sess.get("rol", "")
        effective_role = _resolve_effective_role(permisos, session_rol)
        username = sess.get("username", "")

        if effective_role == "facturador":
            # Facturador sees médico-assigned OR self-created records
            errores = [
                e for e in errores
                if e.get("responsable_rol") == "MEDICO"
                or e.get("created_by") == username
            ]
        elif effective_role == "medico":
            # Médico sees only self-assigned records (by full name match)
            medico_name = sess.get("nombre_completo", "").upper() or " ".join(
                p for p in [sess.get("primer_nombre", ""), sess.get("apellido_1", "")]
                if p
            ).upper()
            errores = [
                e for e in errores
                if e.get("responsable", "").upper() == medico_name
            ]
        # admin/auditor/write → no filtering (see all)

        # ── PM6: Per-record can_edit / can_delete flags ───────────────
        for error in errores:
            # can_delete is straightforward (only admin/auditor/write can delete)
            error["can_delete"] = _can_delete(error, effective_role)

            # can_edit flag: True for admin/auditor/write, or facturador on allowed records.
            # Médico always gets can_edit=False (permission matrix says "No" for Editar;
            # médico partial edit is handled at field level in update_error).
            if effective_role in ("admin", "auditor", "write"):
                error["can_edit"] = True
            elif effective_role == "facturador":
                error["can_edit"] = _can_edit(error, effective_role, username)
            else:
                error["can_edit"] = False

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


def add_error(data: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Crear un nuevo error.

    Args:
        data: payload from client (``created_by`` key is stripped/ignored per PM2).
        session: optional session dict for testability; falls back to ``flask.session``.
    """
    try:
        sess = session if session is not None else flask.session

        tipo_error = data.get("tipo_error", "").strip() or "Otros"
        factura = (data.get("factura", "").strip() or "").upper()
        observacion = (data.get("observacion", "").strip() or "").upper()
        observacion_facturador = data.get("observacion_facturador", "").strip() or ""
        estado = data.get("estado", "").strip() or "S"
        responsable = data.get("responsable", "").strip() or ""

        # PM2: validador from session (display name)
        validador = f"{sess.get('primer_nombre', '')} {sess.get('apellido_1', '')}".strip()

        # PM2: created_by from session username (server-side only; stripped from payload)
        created_by = sess.get("username", "")

        # PM4 / R14: facturador create gate — resolve target role
        permisos = sess.get("permisos", [])
        rol = sess.get("rol", "")
        effective_role = _resolve_effective_role(permisos, rol)

        _, _, responsables_roles = _build_user_data()
        target_rol = responsables_roles.get(responsable, "-")

        if not _can_create_for(target_rol, effective_role):
            return {
                "status": "error",
                "data": {},
                "errors": ["No autorizado para crear registros para este rol"],
            }

        nuevo = crear_error(
            tipo_error, factura, observacion, estado, responsable,
            observacion_facturador, validador=validador, created_by=created_by,
        )
        logger.info("Error creado con ID: %s", nuevo["id"])
        return {"status": "success", "data": {"error": nuevo}, "errors": []}
    except Exception as e:
        logger.exception("Error creando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def update_error(error_id: str, data: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Actualizar un error existente.

    Ownership gate (PM3/R1):
    1. Resolve effective role + check ``_can_edit()`` — reject if False.
    2. Admin/auditor/write → full write (no field restrictions).
    3. Facturador on médico record → full write (all fields allowed).
    4. Médico on own → partial write (only ``estado`` / ``observacion_facturador``).
    5. Otherwise → 403.

    Args:
        session: optional session dict for testability; falls back to ``flask.session``.
    """
    try:
        sess = session if session is not None else flask.session

        existente = obtener_error(error_id)
        if not existente:
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        # ── Ownership gate (PM3 / R16) ───────────────────────────────
        permisos = sess.get("permisos", [])
        session_rol = sess.get("rol", "")
        effective_role = _resolve_effective_role(permisos, session_rol)
        username = sess.get("username", "")

        if not _can_edit(existente, effective_role, username):
            return {
                "status": "error",
                "data": {},
                "errors": ["No autorizado para editar este registro"],
            }, 403

        # Determine full-write access
        is_full_write = _has_full_write_access(effective_role, existente, username)

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

        logger.info("Error actualizado: %s", error_id)
        return {"status": "success", "data": {"error": actualizado}, "errors": []}
    except Exception as e:
        logger.exception("Error actualizando error")
        return {"status": "error", "data": {}, "errors": [str(e)]}


def delete_error(error_id: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Eliminar un error.

    Ownership gate (R16/PM3): only admin/auditor/write can delete.
    Facturador can delete médico records only. Médico/read always blocked.

    Args:
        session: optional session dict for testability; falls back to ``flask.session``.
    """
    try:
        sess = session if session is not None else flask.session

        existente = obtener_error(error_id)
        if not existente:
            return {"status": "error", "data": {}, "errors": ["Error no encontrado"]}

        # ── Ownership gate (R16 / PM3) ───────────────────────────────
        permisos = sess.get("permisos", [])
        session_rol = sess.get("rol", "")
        effective_role = _resolve_effective_role(permisos, session_rol)

        if not _can_delete(existente, effective_role):
            return {
                "status": "error",
                "data": {},
                "errors": ["No autorizado para eliminar este registro"],
            }

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