"""Decorators para control de permisos via sesión.

Reemplaza el viejo sistema con Flask-Login y area_required.
Usa session['permisos'] para verificar acceso.
"""

from functools import wraps

from flask import flash, jsonify, redirect, render_template, request, url_for, session
from app.utils.auth_session import is_authenticated


def login_requerido(f):
    """Decorator: verifica que el usuario tenga sesión activa.

    Si no hay sesión redirige al login o devuelve 401 JSON.
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
            flash("Debe iniciar sesión", "error")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated


def permiso_requerido(*permisos):
    """Decorator: verifica que el usuario tenga AL MENOS UNO de los permisos.

    Admin (permiso '*') pasa cualquier verificación automáticamente.

    Uso:
        @permiso_requerido('odontologia')
        def ruta_protegida(): ...

        @permiso_requerido('control_urgencias:write')
        def modificar(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_permisos = session.get("permisos", [])

            # Admin pasa todo
            if "*" in user_permisos:
                return f(*args, **kwargs)

            # Expandir :write → también tener el base (ej: facturas_abiertas:write → facturas_abiertas)
            # Consistente con sidebar (app-sidebar.tsx) y dashboard (base.py _filter_areas)
            expanded = set(user_permisos)
            for p in user_permisos:
                if p.endswith(":write"):
                    expanded.add(p.removesuffix(":write"))

            # Verificar al menos un permiso requerido
            if any(p in expanded for p in permisos):
                return f(*args, **kwargs)

            # Sin permiso
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": ["Permiso denegado"],
                }), 403

            flash("No tiene permiso para acceder a esta sección", "error")
            return redirect(url_for("home.home_react"))
        return decorated
    return decorator


def admin_requerido(f):
    """Decorator: solo usuarios con rol admin pueden acceder.

    Admin se define como tener permiso '*' en la sesión.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "*" not in session.get("permisos", []):
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({
                    "status": "error",
                    "data": {},
                    "errors": ["Permiso denegado"],
                }), 403
            flash("Acceso denegado", "error")
            return redirect(url_for("home.home_react"))
        return f(*args, **kwargs)
    return decorated
