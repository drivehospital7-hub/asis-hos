import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from flask_login import LoginManager, current_user, AnonymousUserMixin


class GuestUser(AnonymousUserMixin):
    """Usuario guest cuando no hay base de datos."""
    @property
    def is_authenticated(self):
        return session.get("ce_authenticated", False)

    @property
    def username(self):
        return "admin"


login_manager = LoginManager()


def load_anon_user(user_id=None):
    """User loader que no depende de DB - retorna guest."""
    return GuestUser()

# Endpoints públicos que NO requieren sesión
PUBLIC_ENDPOINTS = frozenset({
    # Auth — login/logout/status siempre accesibles
    "auth.api_login",
    "auth.api_logout",
    "auth.api_status",
    "auth.login",
    # Static — CSS, JS, imágenes
    "static",
    # Control de errores (raíz /) — página + APIs de LECTURA son públicas
    "control_errores.control_errores_page",
    # Abiertas Urgencias — horarios + API
    "abiertas_urgencias.abiertas_urgencias_page",
    "abiertas_urgencias.api_get_schedule",
    "abiertas_urgencias.api_save_schedule",
    "abiertas_urgencias.api_delete_schedule",
    "control_errores.listar_opciones",
    "control_errores.listar_errores",
    "control_errores.check_changes",
    "control_errores.listar_imagenes",
    "control_errores.servir_imagen",
    # Escritura — PUT para actualizar campos individuales (estado sobre todo)
    "control_errores.actualizar_error",
})


def _ensure_secret_key(app: Flask) -> None:
    """Asegura que SECRET_KEY esté seteada, con respaldo a archivo fuera del repo.

    Orden de resolución:
    1. Lo que vino del config class (env var o default)
    2. instance/secret.key (archivo local, inmune a git pull)
    3. Genera una nueva y la persiste en instance/secret.key
    """
    if app.config.get("SECRET_KEY"):
        return  # Ya está seteada desde env var o default

    key_path = Path(app.instance_path) / "secret.key"

    if key_path.exists():
        app.config["SECRET_KEY"] = key_path.read_text().strip()
        return

    # Primera ejecución: generar y persistir
    new_key = secrets.token_hex(32)
    app.config["SECRET_KEY"] = new_key
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(new_key)
    except OSError:
        pass  # Si no puede escribir, la clave en memoria funciona igual


def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.from_object(config)

    # Asegurar SECRET_KEY (env var > instance/secret.key > generar)
    _ensure_secret_key(app)

    # ──────────────────────────────────────────────
    # Session persistente (cookie 30 días)
    # ──────────────────────────────────────────────
    app.config.setdefault("SESSION_PERMANENT", True)
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(days=30))
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")

    # ──────────────────────────────────────────────
    # Middleware global: verifica auth en cada request
    # ──────────────────────────────────────────────
    @app.before_request
    def check_session_auth():
        # Rutas públicas (login, logout, status, estáticos)
        if request.endpoint in PUBLIC_ENDPOINTS:
            return

        # Si ya tiene session nuestra → OK
        if session.get("ce_authenticated"):
            return

        # Si tiene Flask-Login activo → también OK
        if current_user.is_authenticated:
            return

        # No autenticado
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["No autenticado"],
            }), 401

        return render_template("unauthorized.html"), 401

    # Flask-Login con usuario guest (sin DB)
    login_manager.init_app(app)
    login_manager.anonymous_user = GuestUser
    login_manager.user_loader(load_anon_user)

    from app.routes.home import home_bp
    from app.routes.excel_headers import excel_headers_bp
    from app.routes.urgencias import urgencias_bp
    from app.routes.procedimientos import procedimientos_bp
    from app.routes.ordenado_facturado import ordenado_facturado_bp
    from app.routes.notas_api import api_bp
    from app.routes.import_csv import import_csv_bp
    from app.routes.derechos import derechos_bp
    from app.routes.auth import auth_bp
    from app.routes.genderize_api import genderize_bp
    from app.routes.import_facturas import import_facturas_bp
    from app.routes.control_errores import control_errores_bp
    from app.routes.abiertas_urgencias import abiertas_urgencias_bp

    # Control-errores es la raíz (debe registrarse antes de home)
    app.register_blueprint(control_errores_bp)
    app.register_blueprint(abiertas_urgencias_bp, url_prefix="/abiertas-urgencias")
    # Home ahora es /dashboard
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(excel_headers_bp, url_prefix="/odontologia")
    app.register_blueprint(urgencias_bp, url_prefix="/urgencias")
    app.register_blueprint(procedimientos_bp)
    app.register_blueprint(ordenado_facturado_bp, url_prefix="/ordenado-facturado")
    app.register_blueprint(api_bp)
    app.register_blueprint(import_csv_bp)
    app.register_blueprint(derechos_bp, url_prefix="/derechos")
    app.register_blueprint(genderize_bp, url_prefix="/api/genderize")
    app.register_blueprint(import_facturas_bp)

    return app