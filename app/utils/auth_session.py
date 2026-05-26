"""Autenticación via Flask session (sin DB, sin Flask-Login).

Almacena datos del usuario en la sesión:
  - ce_authenticated : bool
  - username          : str
  - rol               : str  ("admin" | "usuario")
  - permisos          : list[str]

Las funciones check_credentials / do_login / do_logout / is_authenticated
reemplazan completamente el viejo módulo que usaba credenciales hardcodeadas.
"""

from typing import Optional

from flask import session

from app.utils import users_store


def check_credentials(username: str, password: str) -> Optional[dict]:
    """Valida credenciales contra el store local (JSON).

    Returns:
        dict con username, rol, permisos si es válido.
        None si las credenciales son incorrectas.
    """
    return users_store.check_credentials(username, password)


def do_login(user_data: dict) -> None:
    """Marca la sesión como autenticada y guarda datos del usuario."""
    session["ce_authenticated"] = True
    session["username"] = user_data["username"]
    session["rol"] = user_data["rol"]
    session["permisos"] = user_data["permisos"]
    session["primer_nombre"] = user_data.get("primer_nombre", "")
    session["segundo_nombre"] = user_data.get("segundo_nombre", "")
    session["apellido_1"] = user_data.get("apellido_1", "")
    session["apellido_2"] = user_data.get("apellido_2", "")
    session.permanent = True


def do_logout() -> None:
    """Limpia los datos de autenticación de la sesión."""
    for key in (
        "ce_authenticated", "username", "rol", "permisos",
        "primer_nombre", "segundo_nombre", "apellido_1", "apellido_2",
    ):
        session.pop(key, None)


def is_authenticated() -> bool:
    """Verifica si la sesión actual está autenticada."""
    return session.get("ce_authenticated", False)


def has_permission(*requeridos: str) -> bool:
    """Verifica si el usuario tiene AL MENOS UNO de los permisos requeridos.

    Admin (permiso '*') automáticamente pasa cualquier verificación.
    """
    user_permisos = session.get("permisos", [])
    if "*" in user_permisos:
        return True
    return any(p in user_permisos for p in requeridos)
