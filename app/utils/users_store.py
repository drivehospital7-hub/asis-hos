"""Almacenamiento de usuarios en la base de datos (SQLAlchemy facade).

La base de datos es la ÚNICA fuente de verdad para usuarios, roles,
nombres y responsables. No hay fallback a JSON ni a constantes
hardcodeadas: si la DB no está disponible, las operaciones fallan
con error.

Mantiene la API pública del antiguo store JSON
(check_credentials/get_user/list_users/create_user/update_user/
delete_user) y agrega get_facturadores()/get_validadores(). El esquema y los datos deben
provisionarse explícitamente antes de usar esta fachada.
"""

import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from app.constants.base import (
    ALLOWED_PERMISOS,
    PERMISO_MUTUAL_EXCLUSION,
    PERMISO_RESPONSABLE_FACTURACION,
    VALID_AREA_SLUGS,
)
from app.database import Base, SessionLocal
from app.models import User, UserArea, VALID_ROLES

logger = logging.getLogger(__name__)

def _new_session():
    """Abre una sesión nueva (cerrada por cada función)."""
    return SessionLocal()


def _to_dict(user: User, include_hash: bool = False) -> dict:
    """Convierte un User ORM a dict (sin password_hash por defecto)."""
    data = {
        "username": user.username,
        "rol": user.rol,
        "permisos": user.permisos or [],
        "primer_nombre": user.primer_nombre or "",
        "segundo_nombre": user.segundo_nombre or "",
        "apellido_1": user.apellido_1 or "",
        "apellido_2": user.apellido_2 or "",
        "areas": sorted(ua.area for ua in user.areas),
    }
    if include_hash:
        data["password_hash"] = user.password_hash
    return data


def _check_mutual_exclusion(permisos: list[str]) -> tuple[bool, str]:
    """Verifica que no haya permisos mutuamente excluyentes."""
    for p in permisos:
        conflicto = PERMISO_MUTUAL_EXCLUSION.get(p)
        if conflicto and conflicto in permisos:
            return (
                False,
                f"No puede tener '{p}' y '{conflicto}' simultáneamente: "
                f"son mutuamente excluyentes",
            )
    return True, ""


def _validate_areas(areas: list | None) -> tuple[bool, str]:
    """Valida que cada slug de área esté en VALID_AREA_SLUGS.

    None o lista vacía son válidos (usuario sin área → grupo "Sin área").
    """
    if not areas:
        return True, ""
    if not isinstance(areas, list):
        return False, "Áreas debe ser una lista"
    for a in areas:
        if a not in VALID_AREA_SLUGS:
            return False, f"Área inválida: {a}"
    return True, ""


# =============================================================================
# API pública
# =============================================================================


def check_credentials(username: str, password: str) -> Optional[dict]:
    """Valida credenciales contra la tabla users.

    Returns:
        dict con username, rol, permisos y campos de nombre si es válido.
        None si las credenciales son incorrectas.
    """
    db = _new_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and check_password_hash(user.password_hash, password):
            return _to_dict(user)
        return None
    finally:
        db.close()


def get_user(username: str) -> Optional[dict]:
    """Retorna un usuario completo (con password_hash) o None."""
    db = _new_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        return _to_dict(user, include_hash=True) if user else None
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Retorna un usuario por su id (sin password_hash) o None."""
    db = _new_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return _to_dict(user) if user else None
    finally:
        db.close()


def list_users() -> list:
    """Retorna todos los usuarios (sin password_hash)."""
    db = _new_session()
    try:
        users = db.query(User).order_by(User.username).all()
        return [_to_dict(u) for u in users]
    finally:
        db.close()


def get_facturadores() -> list[dict]:
    """Retorna usuarios elegibles como responsables con identidad compuesta.

    Son elegibles los usuarios con rol ``facturador`` o con el permiso
    ``responsable_facturacion``. Cada dict incluye username, campos de nombre y ``nombre_completo``
    (primer_nombre + apellido_1 en mayúsculas, sin segundo_nombre/
    apellido_2). Excluye usuarios sin primer_nombre. Se conserva el nombre
    de la función por compatibilidad con sus consumidores actuales.
    """
    db = _new_session()
    try:
        users = db.query(User).order_by(User.username).all()
        result = []
        for u in users:
            if u.rol != "facturador" and PERMISO_RESPONSABLE_FACTURACION not in (u.permisos or []):
                continue
            primer_nombre = (u.primer_nombre or "").strip()
            if not primer_nombre:
                continue
            apellido_1 = (u.apellido_1 or "").strip()
            result.append(
                {
                    "username": u.username,
                    "primer_nombre": primer_nombre,
                    "segundo_nombre": (u.segundo_nombre or "").strip(),
                    "apellido_1": apellido_1,
                    "apellido_2": (u.apellido_2 or "").strip(),
                    "nombre_completo": " ".join(
                        n for n in [primer_nombre, apellido_1] if n
                    ).upper(),
                    "rol": u.rol,
                    "areas": sorted(ua.area for ua in u.areas),
                }
            )
        return result
    finally:
        db.close()


def get_validadores() -> list[dict]:
    """Retorna exclusivamente usuarios con rol exacto ``validador``.

    La identidad visible se compone de primer nombre y primer apellido para
    coincidir con el valor persistido en cada novedad. Nunca expone hashes.
    """
    db = _new_session()
    try:
        users = (
            db.query(User)
            .filter(User.rol == "validador")
            .order_by(User.username)
            .all()
        )
        result = []
        for u in users:
            primer_nombre = (u.primer_nombre or "").strip()
            if not primer_nombre:
                continue
            apellido_1 = (u.apellido_1 or "").strip()
            result.append(
                {
                    "username": u.username,
                    "primer_nombre": primer_nombre,
                    "segundo_nombre": (u.segundo_nombre or "").strip(),
                    "apellido_1": apellido_1,
                    "apellido_2": (u.apellido_2 or "").strip(),
                    "nombre_completo": " ".join(
                        n for n in [primer_nombre, apellido_1] if n
                    ).upper(),
                    "rol": u.rol,
                    "areas": sorted(ua.area for ua in u.areas),
                }
            )
        return result
    finally:
        db.close()


def create_user(
    username: str,
    password: str,
    rol: str,
    permisos: list,
    primer_nombre: str = "",
    segundo_nombre: str = "",
    apellido_1: str = "",
    apellido_2: str = "",
    areas: list | None = None,
) -> tuple:
    """Crea un nuevo usuario.

    ``areas`` (opcional): slugs de área organizacional validados contra
    VALID_AREA_SLUGS. Se persisten como filas en user_areas (sin migración).

    Returns:
        (True, mensaje) si se creó, (False, mensaje) si ya existe o hay error.
    """
    db = _new_session()
    try:
        if db.query(User).filter(User.username == username).first():
            return False, f"El usuario '{username}' ya existe"

        if rol not in VALID_ROLES:
            return False, f"Rol inválido: {rol}"

        ok_exclusion, msg_exclusion = _check_mutual_exclusion(permisos)
        if not ok_exclusion:
            return False, msg_exclusion

        ok_areas, msg_areas = _validate_areas(areas)
        if not ok_areas:
            return False, msg_areas

        db.add(
            User(
                username=username,
                password_hash=generate_password_hash(password),
                rol=rol,
                permisos=permisos,
                primer_nombre=primer_nombre,
                segundo_nombre=segundo_nombre,
                apellido_1=apellido_1,
                apellido_2=apellido_2,
                areas=[UserArea(area=a) for a in (areas or [])],
            )
        )
        db.commit()
        logger.info("[BACK] Usuario '%s' creado (rol=%s)", username, rol)
        return True, f"Usuario '{username}' creado"
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_user(username: str, updates: dict) -> tuple:
    """Actualiza parcialmente un usuario.

    Los campos en `updates` son opcionales:
      - password: str|None — Si es None o "", se omite (no cambia).
      - rol: str — Debe estar en VALID_ROLES.
      - permisos: list — Cada elemento debe estar en ALLOWED_PERMISOS.
      - areas: list — Slugs de área validados contra VALID_AREA_SLUGS;
        replace-all (si la key está ausente, las áreas no se tocan).
      - primer_nombre/segundo_nombre/apellido_1/apellido_2 — parciales.

    Returns:
        (True, mensaje) si se actualizó, (False, mensaje) si hay error.
    """
    db = _new_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return False, f"Usuario '{username}' no encontrado"

        # Password opcional
        password = updates.get("password")
        if password and isinstance(password, str) and password.strip():
            user.password_hash = generate_password_hash(password)

        # Rol con validación
        if "rol" in updates:
            rol = updates["rol"]
            if rol not in VALID_ROLES:
                return False, f"Rol inválido: {rol}"
            user.rol = rol

        # Permisos con validación
        if "permisos" in updates:
            nuevos_permisos = updates["permisos"]
            if not isinstance(nuevos_permisos, list):
                return False, "Permisos debe ser una lista"

            for p in nuevos_permisos:
                if p not in ALLOWED_PERMISOS:
                    return False, f"Permiso inválido: {p}"

            ok_exclusion, msg_exclusion = _check_mutual_exclusion(nuevos_permisos)
            if not ok_exclusion:
                return False, msg_exclusion

            # Protección: si el usuario actual tiene "*" y los nuevos no → rechazar
            if "*" in (user.permisos or []) and "*" not in nuevos_permisos:
                return (
                    False,
                    "No puedes remover el permiso de administrador de este usuario",
                )

            user.permisos = nuevos_permisos

        # Áreas con validación. Replace-all para slugs VÁLIDOS; las filas
        # legacy ya persistidas (fuera de VALID_AREA_SLUGS) se conservan:
        # no se borran datos históricos sin migración explícita.
        if "areas" in updates:
            ok_areas, msg_areas = _validate_areas(updates["areas"])
            if not ok_areas:
                return False, msg_areas
            conservadas = sorted(
                {ua.area for ua in user.areas} - set(VALID_AREA_SLUGS)
            )
            user.areas = [
                UserArea(area=a)
                for a in (updates["areas"] or []) + conservadas
            ]

        # Person fields (partial update — solo si están presentes)
        for key in ("primer_nombre", "segundo_nombre", "apellido_1", "apellido_2"):
            if key in updates:
                setattr(user, key, updates[key])

        db.commit()
        return True, f"Usuario '{username}' actualizado"
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_user(username: str) -> tuple:
    """Elimina un usuario.

    El usuario 'admin' NO puede ser eliminado.

    Returns:
        (True, mensaje) si se eliminó, (False, mensaje) si no existe
        o si es admin.
    """
    db = _new_session()
    try:
        if username == "admin":
            return False, "No se puede eliminar el usuario admin"

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            return False, f"Usuario '{username}' no encontrado"

        db.delete(user)
        db.commit()
        logger.info("[BACK] Usuario '%s' eliminado", username)
        return True, f"Usuario '{username}' eliminado"
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()
