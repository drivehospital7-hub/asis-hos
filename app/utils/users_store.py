"""Almacenamiento local de usuarios (JSON, sin DB).

Provee persistencia entre sesiones via archivo instance/users.json.
Si el archivo no existe, se crea con los usuarios por defecto al
primer intento de lectura.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

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
    },
    {
        "username": "odontologia",
        "password": "odonto123",
        "rol": "usuario",
        "permisos": ["odontologia"],
        "descripcion": "Solo /odontologia",
    },
    {
        "username": "urgencias",
        "password": "urgencias123",
        "rol": "usuario",
        "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
        "descripcion": "/urgencias + control urgencias (solo lectura) + facturas abiertas",
    },
    {
        "username": "auditor",
        "password": "auditor123",
        "rol": "usuario",
        "permisos": [
            "control_urgencias",
            "control_urgencias:write",
            "facturas_abiertas",
        ],
        "descripcion": "Control urgencias (con modificación) + facturas abiertas",
    },
]


def _load_users() -> list:
    """Carga usuarios desde el archivo JSON."""
    if not USERS_FILE.exists():
        _create_default_users()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Error leyendo %s: %s", USERS_FILE, e)
        return []


def _save_users(users: list) -> None:
    """Guarda usuarios al archivo JSON."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


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
            }
        )
    _save_users(users)
    logger.info(
        "Archivo %s creado con %d usuarios por defecto",
        USERS_FILE,
        len(users),
    )


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
        {"username": u["username"], "rol": u["rol"], "permisos": u["permisos"]}
        for u in users
    ]


def create_user(
    username: str, password: str, rol: str, permisos: list
) -> tuple:
    """Crea un nuevo usuario.

    Returns:
        (True, mensaje) si se creó, (False, mensaje) si ya existe.
    """
    users = _load_users()

    if any(u["username"] == username for u in users):
        return False, f"El usuario '{username}' ya existe"

    users.append(
        {
            "username": username,
            "password_hash": generate_password_hash(password),
            "rol": rol,
            "permisos": permisos,
        }
    )
    _save_users(users)
    return True, f"Usuario '{username}' creado"


def delete_user(username: str) -> tuple:
    """Elimina un usuario.

    Returns:
        (True, mensaje) si se eliminó, (False, mensaje) si no existe.
    """
    users = _load_users()
    filtered = [u for u in users if u["username"] != username]
    if len(filtered) == len(users):
        return False, f"Usuario '{username}' no encontrado"
    _save_users(filtered)
    return True, f"Usuario '{username}' eliminado"
