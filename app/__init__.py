from datetime import timedelta

from flask import Flask, jsonify, render_template, request, session
from flask_login import LoginManager, current_user

login_manager = LoginManager()

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
})


def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.from_object(config)

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

    # Inicializar Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()

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