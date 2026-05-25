"""Routes de autenticación unificada (sin DB, sin Flask-Login).

Login, logout y gestión de usuarios contra el store local (JSON).
"""

import json
import logging
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, redirect, url_for, flash, request, session

from app.utils import auth_session, users_store
from app.utils import templates_store
from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


def _get_manifest_asset(manifest_path: Path, entry_key: str, field: str) -> str:
    """Extract a field from Vite's manifest.json for the given entry."""
    if not manifest_path.exists():
        return ""
    manifest = json.loads(manifest_path.read_text())
    return manifest.get(entry_key, {}).get(field, "")


# =============================================================================
# React shell pages
# =============================================================================


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Página de login — React para GET, form legacy para POST."""
    if auth_session.is_authenticated():
        return redirect(url_for("home.home_react"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Usuario y contraseña son requeridos", "error")
            return redirect(url_for("auth.login"))

        user_data = auth_session.check_credentials(username, password)
        if user_data:
            auth_session.do_login(user_data)
            logger.info("Login exitoso: %s", username)

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            return redirect(url_for("home.home_react"))

        flash("Usuario o contraseña incorrectos", "error")
        logger.warning("Intento de login fallido: %s", username)
        return redirect(url_for("auth.login"))

    # GET: serve React
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/login/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_standalone.html",
        page_title="Iniciar Sesión",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={},
    )




@auth_bp.get("/usuarios")
@admin_requerido
def usuarios_react():
    """React shell for Usuarios."""
    permisos = session.get("permisos", [])
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/usuarios/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    usuarios = users_store.list_users()
    templates = templates_store.list_templates()
    return render_template(
        "react_shell.html",
        page_title="Usuarios del Sistema",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={
            "username": session.get("username", ""),
            "permisos": permisos,
            "usuarios": usuarios,
            "templates": templates,
            "session_username": session.get("username", ""),
        },
    )




@auth_bp.get("/unauthorized")
def unauthorized_react():
    """React shell for Unauthorized (no auth required)."""
    manifest_path = Path(current_app.root_path) / "static" / "react-dist" / "manifest.json"
    entry_js = _get_manifest_asset(manifest_path, "src/pages/unauthorized/index.html", "file")
    entry_css = _get_manifest_asset(manifest_path, "style.css", "file")
    return render_template(
        "react_standalone.html",
        page_title="No autorizado",
        entry_js=entry_js,
        entry_css=entry_css,
        initial_data={},
    )


# =============================================================================
# API endpoints (JSON) — usados por el modal del frontend
# =============================================================================


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """Login vía JSON."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "data": {}, "errors": ["Cuerpo JSON inválido"]}), 400

    user = data.get("user", "")
    passwd = data.get("pass", "")

    if not user or not passwd:
        return jsonify({"status": "error", "data": {}, "errors": ["Usuario y contraseña requeridos"]}), 400

    user_data = auth_session.check_credentials(user, passwd)
    if user_data:
        auth_session.do_login(user_data)
        logger.info("Login exitoso via API: %s", user)
        return jsonify({
            "status": "success",
            "data": {
                "authenticated": True,
                "username": user,
                "rol": user_data["rol"],
            },
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
    auth_session.do_logout()
    return jsonify({"status": "success", "data": {}, "errors": []})


@auth_bp.route("/api/status")
def api_status():
    """Devuelve el estado de autenticación actual."""
    authed = auth_session.is_authenticated()
    return jsonify({
        "status": "success",
        "data": {
            "authenticated": authed,
            "username": session.get("username", "") if authed else "",
        },
        "errors": [],
    })


@auth_bp.route("/api/templates")
@admin_requerido
def api_list_templates():
    """Retorna JSON con todas las plantillas de permisos."""
    templates = templates_store.list_templates()
    return jsonify({
        "status": "success",
        "data": {"templates": templates},
        "errors": [],
    })


@auth_bp.route("/logout")
def logout():
    """Cerrar sesión."""
    auth_session.do_logout()
    flash("Sesión cerrada", "success")
    logger.info("Logout exitoso")
    return redirect(url_for("auth.login"))


# =============================================================================
# Gestión de usuarios (admin only)
# =============================================================================


# Note: GET /usuarios is handled by usuarios_react() above
# The legacy Jinja2 route is at /usuarios/legacy


@auth_bp.route("/usuarios/crear", methods=["POST"])
@admin_requerido
def crear_usuario():
    """Crear usuario en el store local."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rol = request.form.get("rol", "usuario")
    permisos_raw = request.form.getlist("permisos")

    if not username or not password:
        flash("Usuario y contraseña son requeridos", "error")
        return redirect(url_for("auth.usuarios_react"))

    if rol != "admin" and not permisos_raw:
        flash("Debe seleccionar al menos un permiso", "error")
        return redirect(url_for("auth.usuarios_react"))

    permisos = ["*"] if rol == "admin" else permisos_raw

    ok, msg = users_store.create_user(username, password, rol, permisos)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("auth.usuarios_react"))


@auth_bp.route("/usuarios/<username>/editar", methods=["POST"])
@admin_requerido
def editar_usuario(username):
    """Editar un usuario existente.

    Password es opcional — si se envía vacío, no cambia.
    """
    form_username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rol = request.form.get("rol", "usuario")
    permisos_raw = request.form.getlist("permisos")

    # Protección: admin no puede removerse * a sí mismo
    session_username = session.get("username")
    if session_username == username and "*" not in permisos_raw:
        flash("No puedes remover tus propios permisos de administrador", "error")
        return redirect(url_for("auth.usuarios_react"))

    updates = {"rol": rol, "permisos": permisos_raw}
    if password:
        updates["password"] = password

    ok, msg = users_store.update_user(username, updates)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("auth.usuarios_react"))


@auth_bp.route("/usuarios/<username>/eliminar", methods=["POST"])
@admin_requerido
def eliminar_usuario(username):
    """Eliminar un usuario (excepto admin)."""
    if username == "admin":
        flash("No se puede eliminar el usuario admin", "error")
        return redirect(url_for("auth.usuarios_react"))

    ok, msg = users_store.delete_user(username)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("auth.usuarios_react"))
