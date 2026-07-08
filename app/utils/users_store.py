"""Almacenamiento local de usuarios (JSON, sin DB).

Provee persistencia entre sesiones via archivo instance/users.json.
Si el archivo no existe, se crea con los usuarios por defecto al
primer intento de lectura.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from app.constants.base import ALLOWED_PERMISOS, PERMISO_MUTUAL_EXCLUSION

logger = logging.getLogger(__name__)

USERS_FILE = Path("instance") / "users.json"

# Usuarios por defecto (se crean si el archivo no existe)
DEFAULT_USERS = [
    {
        "username": "admin",
        "password": "admin123",
        "rol": "admin",
        "permisos": ["*"],
        "descripcion": "Acceso a todas las áreas",
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "odontologia",
        "password": "odonto123",
        "rol": "usuario",
        "permisos": ["odontologia"],
        "descripcion": "Solo /odontologia",
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "urgencias",
        "password": "urgencias123",
        "rol": "usuario",
        "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
        "descripcion": "/urgencias + control urgencias (solo lectura) + facturas abiertas",
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
    {
        "username": "auditor",
        "password": "auditor123",
        "rol": "usuario",
        "permisos": [
            "control_urgencias",
            "control_urgencias:write",
            "facturas_abiertas",
            "facturas_abiertas:write",
            "equipos_basicos",
        ],
        "descripcion": "Control urgencias + facturas abiertas + cruce reportes (con modificación)",
        "primer_nombre": "",
        "segundo_nombre": "",
        "apellido_1": "",
        "apellido_2": "",
    },
]


def _load_users() -> list:
    """Carga usuarios desde el archivo JSON."""
    if not USERS_FILE.exists():
        _create_default_users()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Error leyendo %s: %s", USERS_FILE, e)
        return []

    # Backfill: ensure all person fields exist for legacy users
    person_fields = ("primer_nombre", "segundo_nombre", "apellido_1", "apellido_2")
    changed = False
    for u in users:
        for field in person_fields:
            if field not in u:
                u[field] = ""
                changed = True

    if changed:
        _save_users(users)

    return users


def _save_users(users: list) -> None:
    """Guarda usuarios al archivo JSON (escritura atómica).

    Escribe a un archivo temporal y luego usa os.replace() para
    reemplazar el archivo original. Esto previene corrupción
    por crash durante la escritura.
    """
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    os.replace(tmp, USERS_FILE)


def _create_default_users() -> None:
    """Crea el archivo con usuarios por defecto (hashea passwords)."""
    users = []
    for u in DEFAULT_USERS:
        users.append(
            {
                "username": u["username"],
                "password_hash": generate_password_hash(u["password"]),
                "rol": u["rol"],
                "permisos": u["permisos"],
                "primer_nombre": u.get("primer_nombre", ""),
                "segundo_nombre": u.get("segundo_nombre", ""),
                "apellido_1": u.get("apellido_1", ""),
                "apellido_2": u.get("apellido_2", ""),
            }
        )
    _save_users(users)
    logger.info(
        "Archivo %s creado con %d usuarios por defecto",
        USERS_FILE,
        len(users),
    )


def _check_mutual_exclusion(permisos: list[str]) -> tuple[bool, str]:
    """Verifica que no haya permisos mutuamente excluyentes.

    Por ejemplo, 'control_urgencias' y 'control_urgencias:write'
    no pueden estar ambos en la misma lista.

    Returns:
        (True, "") si está ok, (False, mensaje) si hay conflicto.
    """
    for p in permisos:
        conflicto = PERMISO_MUTUAL_EXCLUSION.get(p)
        if conflicto and conflicto in permisos:
            return (
                False,
                f"No puede tener '{p}' y '{conflicto}' simultáneamente: "
                f"son mutuamente excluyentes",
            )
    return True, ""


def check_credentials(username: str, password: str) -> Optional[dict]:
    """Valida credenciales contra el store local.

    Returns:
        dict con username, rol, permisos si es válido.
        None si las credenciales son incorrectas.
    """
    users = _load_users()
    for u in users:
        if u["username"] == username and check_password_hash(
            u["password_hash"], password
        ):
            return {
                "username": u["username"],
                "rol": u["rol"],
                "permisos": u["permisos"],
                "primer_nombre": u.get("primer_nombre", ""),
                "segundo_nombre": u.get("segundo_nombre", ""),
                "apellido_1": u.get("apellido_1", ""),
                "apellido_2": u.get("apellido_2", ""),
            }
    return None


def get_user(username: str) -> Optional[dict]:
    """Retorna un usuario completo (con password_hash) o None."""
    users = _load_users()
    for u in users:
        if u["username"] == username:
            return u
    return None


def list_users() -> list:
    """Retorna todos los usuarios (sin password_hash)."""
    users = _load_users()
    return [
        {
            "username": u["username"],
            "rol": u["rol"],
            "permisos": u["permisos"],
            "primer_nombre": u.get("primer_nombre", ""),
            "segundo_nombre": u.get("segundo_nombre", ""),
            "apellido_1": u.get("apellido_1", ""),
            "apellido_2": u.get("apellido_2", ""),
        }
        for u in users
    ]


def get_facturadores() -> list[dict]:
    """Retorna usuarios con rol 'facturador', con nombre_completo compuesto.

    Excluye usuarios sin primer_nombre. Cada dict incluye:
    username, primer_nombre, segundo_nombre, apellido_1, apellido_2,
    nombre_completo (compuesto de primer_nombre + apellido_1 en mayúsculas).
    """
    users = _load_users()
    result = []
    for u in users:
        if u.get("rol") == "facturador" and u.get("primer_nombre", "").strip():
            nombres = [u.get("primer_nombre", ""), u.get("apellido_1", "")]
            nombre_completo = " ".join(n for n in nombres if n).upper()
            result.append({
                "username": u["username"],
                "primer_nombre": u.get("primer_nombre", ""),
                "segundo_nombre": u.get("segundo_nombre", ""),
                "apellido_1": u.get("apellido_1", ""),
                "apellido_2": u.get("apellido_2", ""),
                "nombre_completo": nombre_completo,
                "rol": u["rol"],
            })
    return result


def create_user(
    username: str,
    password: str,
    rol: str,
    permisos: list,
    primer_nombre: str = "",
    segundo_nombre: str = "",
    apellido_1: str = "",
    apellido_2: str = "",
) -> tuple:
    """Crea un nuevo usuario.

    Returns:
        (True, mensaje) si se creó, (False, mensaje) si ya existe.
    """
    users = _load_users()

    if any(u["username"] == username for u in users):
        return False, f"El usuario '{username}' ya existe"

    ok_exclusion, msg_exclusion = _check_mutual_exclusion(permisos)
    if not ok_exclusion:
        return False, msg_exclusion

    users.append(
        {
            "username": username,
            "password_hash": generate_password_hash(password),
            "rol": rol,
            "permisos": permisos,
            "primer_nombre": primer_nombre,
            "segundo_nombre": segundo_nombre,
            "apellido_1": apellido_1,
            "apellido_2": apellido_2,
        }
    )
    _save_users(users)
    return True, f"Usuario '{username}' creado"


def update_user(username: str, updates: dict) -> tuple:
    """Actualiza parcialmente un usuario.

    Los campos en `updates` son opcionales:
      - password: str|None — Si es None o "", se omite (no cambia).
      - rol: str — Debe ser "admin" o "usuario".
      - permisos: list — Cada elemento debe estar en ALLOWED_PERMISOS.

    Returns:
        (True, mensaje) si se actualizó, (False, mensaje) si hay error.
    """
    users = _load_users()
    target = None
    for u in users:
        if u["username"] == username:
            target = u
            break

    if target is None:
        return False, f"Usuario '{username}' no encontrado"

    # Construir dict actualizado
    updated = dict(target)

    # Password opcional
    password = updates.get("password")
    if password and isinstance(password, str) and password.strip():
        updated["password_hash"] = generate_password_hash(password)

    # Rol con validación
    if "rol" in updates:
        rol = updates["rol"]
        if rol not in ("admin", "usuario", "medico", "facturador"):
            return False, "Rol inválido: debe ser admin, usuario, medico o facturador"
        updated["rol"] = rol

    # Permisos con validación
    if "permisos" in updates:
        nuevos_permisos = updates["permisos"]
        if not isinstance(nuevos_permisos, list):
            return False, "Permisos debe ser una lista"

        # Validar contra lista permitida
        for p in nuevos_permisos:
            if p not in ALLOWED_PERMISOS:
                return False, f"Permiso inválido: {p}"

        # Validar exclusión mutua (read vs write del mismo módulo)
        ok_exclusion, msg_exclusion = _check_mutual_exclusion(nuevos_permisos)
        if not ok_exclusion:
            return False, msg_exclusion

        # Protección: si el usuario actual tiene "*" y los nuevos no → rechazar
        if "*" in target.get("permisos", []) and "*" not in nuevos_permisos:
            return (
                False,
                "No puedes remover el permiso de administrador de este usuario",
            )

        updated["permisos"] = nuevos_permisos

    # Person fields (partial update — only if present in updates dict)
    for key in ("primer_nombre", "segundo_nombre", "apellido_1", "apellido_2"):
        if key in updates:
            updated[key] = updates[key]

    # Reemplazar en la lista
    for i, u in enumerate(users):
        if u["username"] == username:
            users[i] = updated
            break

    _save_users(users)
    return True, f"Usuario '{username}' actualizado"


def delete_user(username: str) -> tuple:
    """Elimina un usuario.

    El usuario 'admin' NO puede ser eliminado.

    Returns:
        (True, mensaje) si se eliminó, (False, mensaje) si no existe
        o si es admin.
    """
    if username == "admin":
        return False, "No se puede eliminar el usuario admin"

    users = _load_users()
    filtered = [u for u in users if u["username"] != username]
    if len(filtered) == len(users):
        return False, f"Usuario '{username}' no encontrado"
    _save_users(filtered)
    return True, f"Usuario '{username}' eliminado"
