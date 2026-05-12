"""Módulo de autenticación server-side con Flask session.

Usa Flask session nativa (NO Flask-Login) para mantenerlo simple
y no depender de la base de datos.

Las credenciales están hardcodeadas (admin / admin$) para mantener
compatibilidad con el easter egg del frontend.
"""

from flask import session, jsonify, render_template, request
from functools import wraps

# Único lugar donde están las credenciales
ADMIN_USER = "admin"
ADMIN_PASS = "admin$"


def check_credentials(user: str, passwd: str) -> bool:
    """Valida credenciales contra los valores hardcodeados."""
    return user == ADMIN_USER and passwd == ADMIN_PASS


def do_login() -> None:
    """Marca la sesión como autenticada (cookie persistente 30 días)."""
    session["ce_authenticated"] = True
    session.permanent = True


def do_logout() -> None:
    """Elimina la marca de autenticación de la sesión."""
    session.pop("ce_authenticated", None)


def is_authenticated() -> bool:
    """Verifica si la sesión actual está autenticada."""
    return session.get("ce_authenticated", False)


def login_required(f):
    """Decorador para rutas que requieren autenticación.

    Si no hay sesión:
    - Requests JSON → devuelve 401 JSON
    - Requests HTML → renderiza unauthorized.html
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": ["No autenticado"],
                }), 401
            return render_template("unauthorized.html"), 401
        return f(*args, **kwargs)

    return decorated
