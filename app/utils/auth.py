"""Decorators para autenticación y control de áreas."""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def area_required(area: str):
    """
    Decorator que verifica que el usuario tenga acceso al área especificada.
    
    Usage:
        @area_required("odontologia")
        def mi_ruta():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar que esté logueado
            if not current_user.is_authenticated:
                flash("Debe iniciar sesión", "error")
                return redirect(url_for("auth.login", next=request.url))
            
            # Admin tiene acceso a todo
            if current_user.rol == "admin":
                return f(*args, **kwargs)
            
            # Verificar si tiene acceso al área
            user_areas = [ua.area for ua in current_user.areas]
            
            if area not in user_areas:
                flash(f"No tiene acceso al área {area}", "error")
                # Redirigir a su área permitida
                if user_areas:
                    first_area = user_areas[0]
                    return redirect(url_for(f"{first_area}.home"))
                return redirect(url_for("auth.login"))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator que verifica que el usuario sea-admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Debe iniciar sesión", "error")
            return redirect(url_for("auth.login", next=request.url))
        
        if current_user.rol != "admin":
            flash("Acceso denegado", "error")
            return redirect(url_for("home.home"))
        
        return f(*args, **kwargs)
    return decorated_function