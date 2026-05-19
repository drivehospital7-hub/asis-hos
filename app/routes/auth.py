"""Routes de autenticación (login/logout).

Sistema DUAL:
- API endpoints (JSON) → usado por el easter egg del frontend (admin / admin$)
- Flask-Login routes → usado por el formulario /auth/login tradicional (DB)

Ambos setean `session['ce_authenticated']` para que el `before_request`
en __init__.py funcione con cualquiera de los dos.
"""

import logging

from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import Session

from app.utils.auth_session import check_credentials, do_login, do_logout, is_authenticated

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

# Mapeo de áreas a endpoints
AREA_ENDPOINT_MAP = {
    "odontologia": "excel_headers.excel_headers_page",
    "urgencias": "urgencias.urgencias_page",
    "derechos": "derechos.derechos_page",
    "equipos_basicos": "ordenado_facturado.ordenado_facturado_page",
}


def _check_db_available():
    """Check if DB is available."""
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.close()
        return True
    except Exception:
        return False


def _get_db_session():
    """Get DB session or None if not available."""
    from app.database import SessionLocal
    return SessionLocal()


# =============================================================================
# API endpoints (JSON) — usados por el easter egg del frontend
# =============================================================================


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """Login vía JSON (usado por el modal del frontend)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "data": {}, "errors": ["Cuerpo JSON inválido"]}), 400

    user = data.get("user", "")
    passwd = data.get("pass", "")

    if not user or not passwd:
        return jsonify({"status": "error", "data": {}, "errors": ["Usuario y contraseña requeridos"]}), 400

    if check_credentials(user, passwd):
        do_login()
        logger.info("Login exitoso via API: %s", user)
        return jsonify({
            "status": "success",
            "data": {"authenticated": True},
            "errors": [],
        })

    logger.warning("Intento de login fallido via API: %s", user)
    return jsonify({
        "status": "error",
        "data": {},
        "errors": ["Usuario o contraseña incorrectos"],
    }), 401


@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    """Logout vía JSON."""
    do_logout()
    logger.info("Logout exitoso via API")
    return jsonify({
        "status": "success",
        "data": {},
        "errors": [],
    })


@auth_bp.route("/api/status")
def api_status():
    """Devuelve el estado de autenticación actual."""
    return jsonify({
        "status": "success",
        "data": {"authenticated": is_authenticated()},
        "errors": [],
    })


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Página de login (Flask-Login tradicional)."""
    # Si ya está logueado con cualquiera de los dos sistemas, redirigir
    if is_authenticated() or current_user.is_authenticated:
        return redirect(url_for("home.home_page"))

    if not _check_db_available():
        flash("Base de datos no disponible", "error")
        return render_template("login.html")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Usuario y contraseña son requeridos", "error")
            return render_template("login.html")

        db: Session = _get_db_session()
        try:
            from app.models import User
            user = db.query(User).filter(User.username == username).first()

            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                do_login()  # Sincronizar con nuestra session
                flash(f"Bienvenido {user.username}", "success")
                logger.info("Login exitoso via formulario: %s", username)

                # Redirigir al área por defecto o la primera permitida
                next_page = request.args.get("next")
                if next_page:
                    return redirect(next_page)

                if user.rol == "admin":
                    return redirect(url_for("home.home_page"))
                elif user.areas:
                    area = user.areas[0].area
                    endpoint = AREA_ENDPOINT_MAP.get(area, "home.home_page")
                    return redirect(url_for(endpoint))
                else:
                    return redirect(url_for("home.home_page"))
            else:
                flash("Usuario o contraseña incorrectos", "error")
                logger.warning("Intento de login fallido via formulario: %s", username)
        finally:
            db.close()

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cerrar sesión (Flask-Login)."""
    logout_user()
    do_logout()  # Sincronizar con nuestra session
    flash("Sesión cerrada", "success")
    logger.info("Logout exitoso via formulario")
    return redirect(url_for("home.home_page"))


@auth_bp.route("/usuarios")
@login_required
def listar_usuarios():
    """Listar usuarios (solo admin)."""
    if current_user.rol != "admin":
        flash("Acceso denegado", "error")
        return redirect(url_for("control_errores.control_errores_page"))

    if not _check_db_available():
        flash("Base de datos no disponible", "error")
        return redirect(url_for("home.home_page"))

    db: Session = _get_db_session()
    try:
        from app.models import User, AREAS_VALIDAS
        usuarios = db.query(User).all()
        return render_template("usuarios.html", usuarios=usuarios, areas_validas=AREAS_VALIDAS)
    finally:
        db.close()


@auth_bp.route("/usuarios/crear", methods=["POST"])
@login_required
def crear_usuario():
    """Crear usuario (solo admin)."""
    if current_user.rol != "admin":
        flash("Acceso denegado", "error")
        return redirect(url_for("control_errores.control_errores_page"))

    if not _check_db_available():
        flash("Base de datos no disponible", "error")
        return redirect(url_for("home.home_page"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rol = request.form.get("rol", "usuario")
    areas = request.form.getlist("areas")

    if not username or not password:
        flash("Usuario y contraseña son requeridos", "error")
        return redirect(url_for("auth.listar_usuarios"))

    if rol != "admin" and not areas:
        flash("Debe seleccionar al menos un área", "error")
        return redirect(url_for("auth.listar_usuarios"))

    db: Session = _get_db_session()
    try:
        from app.models import User, AREAS_VALIDAS, UserArea
        # Verificar si existe
        existentes = db.query(User).filter(User.username == username).first()
        if existentes:
            flash(f"El usuario {username} ya existe", "error")
            return redirect(url_for("auth.listar_usuarios"))

        # Crear usuario
        password_hash = generate_password_hash(password)
        nuevo_usuario = User(username=username, password_hash=password_hash, rol=rol)
        db.add(nuevo_usuario)
        db.flush()  # Obtener ID

        # Agregar áreas
        if rol != "admin":
            for area in areas:
                if area in AREAS_VALIDAS:
                    db.add(UserArea(user_id=nuevo_usuario.id, area=area))

        db.commit()
        flash(f"Usuario {username} creado", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error: {str(e)}", "error")
    finally:
        db.close()

    return redirect(url_for("auth.listar_usuarios"))