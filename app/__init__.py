import secrets
import logging
from datetime import timedelta
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request, session


logger = logging.getLogger(__name__)


# Endpoints públicos que NO requieren sesión
PUBLIC_ENDPOINTS = frozenset({
    # Auth — login/logout/status siempre accesibles
    "auth.api_login",
    "auth.api_logout",
    "auth.api_status",
    "auth.login",
    "auth.unauthorized_react",
    # Static — CSS, JS, imágenes
    "static",
    # Adjuntos de control de errores: público por diseño (links del Excel
    # exportado deben abrir indefinidamente); la URL lleva el UUID del registro
    # y la ruta valida que el archivo pertenezca a él.
    "control_errores.servir_imagen",
})

# Endpoint de integración LAN que se autentica por bearer token (sin sesión).
INTEGRATION_SUBMIT_ENDPOINT = "integration.control_novedades_submit"


def _ensure_secret_key(app: Flask) -> None:
    """Asegura que SECRET_KEY esté seteada, con respaldo a archivo fuera del repo.

    Orden de resolución:
    1. Lo que vino del config class (env var o default)
    2. instance/secret.key (archivo local, inmune a git pull)
    3. Genera una nueva y la persiste en instance/secret.key
    """
    if app.config.get("SECRET_KEY"):
        return

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
        pass


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
    # Context processor: expone datos de sesión a todas las templates
    # ──────────────────────────────────────────────
    @app.context_processor
    def inject_session_user():
        return {
            "session_username": session.get("username"),
            "session_rol": session.get("rol"),
            "session_permisos": session.get("permisos", []),
        }

    # ──────────────────────────────────────────────
    # Middleware global: verifica auth en cada request
    # ──────────────────────────────────────────────
    def _unauthorized_response():
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["No autenticado"],
        }), 401

    def _handle_bearer_auth():
        """Autentica un request sin sesión vía bearer token de integración.

        Resuelve el token a un usuario de la DB y expone su identidad en
        ``flask.g`` (per-request, NUNCA persistida como cookie de sesión).
        La ruta construye luego una sesión sintética (mismas claves que
        do_login) que aporta username → ``created_by`` y la puerta auth/
        permiso; el ``validador`` persistido se resuelve del payload
        ``nombres``, nunca del token.
        """
        auth_header = request.headers.get("Authorization", "")
        scheme, _, raw_token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not raw_token.strip():
            logger.info("[BACK] Token de integración ausente o malformado")
            return _unauthorized_response()

        from app.utils import token_store
        user = token_store.get_user_for_token(raw_token.strip())
        if user is None:
            logger.warning("[BACK] Token de integración inválido, revocado o vencido")
            return _unauthorized_response()

        # Identidad del validador solo para esta request (flask.g). No se
        # escribe en session: el endpoint es "sin sesión" y no debe acuñar
        # una cookie de sesión reutilizable.
        g.bearer_user = user
        return

    @app.before_request
    def check_session_auth():
        # Endpoint de integración: se autentica por bearer token (sin sesión).
        if request.endpoint == INTEGRATION_SUBMIT_ENDPOINT:
            return _handle_bearer_auth()

        # Rutas públicas (login, logout, status, estáticos)
        if request.endpoint in PUBLIC_ENDPOINTS:
            return

        # Si tiene sesión activa → OK
        if session.get("ce_authenticated"):
            return

        # No autenticado
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "status": "error",
                "data": {},
                "errors": ["No autenticado"],
            }), 401

        return render_template("unauthorized.html"), 401

    from app.routes.home import home_bp
    from app.routes.excel_headers import excel_headers_bp
    from app.routes.urgencias import urgencias_bp
    from app.routes.procedimientos import procedimientos_bp
    from app.routes.ordenado_facturado import ordenado_facturado_bp
    from app.routes.notas_api import api_bp
    from app.routes.import_csv import import_csv_bp
    from app.routes.derechos import derechos_bp
    from app.routes.auth import auth_bp
    from app.routes.import_facturas import import_facturas_bp
    from app.routes.control_errores import control_errores_bp
    from app.routes.abiertas_urgencias import abiertas_urgencias_bp
    from app.routes.odontologia_equipos_basicos import odontologia_equipos_basicos_bp
    from app.routes.monitoreo_carpetas import monitoreo_carpetas_bp
    from app.routes.examenes import examenes_bp
    from app.routes.integration import integration_bp

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
    app.register_blueprint(import_facturas_bp)
    app.register_blueprint(odontologia_equipos_basicos_bp, url_prefix="/odontologia-equipos-basicos")
    app.register_blueprint(monitoreo_carpetas_bp, url_prefix="/monitoreo-carpetas")
    app.register_blueprint(examenes_bp)  # sin prefix: /examenes, /api/examenes, /api/listado
    app.register_blueprint(integration_bp)

    # Prerrequisito de seguridad: HTTPS en la LAN para la integración.
    if not app.config.get("TESTING"):
        from app.routes.integration import _maybe_warn_https
        _maybe_warn_https()

    return app
