"""Routes de integración LAN para control-novedades.

Endpoint de envío JSON autenticado por bearer token (sin sesión de browser)
más administración del ciclo de vida de tokens (emitir/rotar/revocar/listar).
Las rutas solo delegan; la lógica vive en services/integration_service.py y
utils/token_store.py.
"""

import logging

from flask import Blueprint, current_app, g, jsonify, request

from app.constants.base import INTEGRATION_HTTPS_REQUIRED
from app.services.integration_service import submit
from app.utils import token_store
from app.utils.auth import admin_requerido

logger = logging.getLogger(__name__)

integration_bp = Blueprint("integration", __name__, url_prefix="/api/integration")


def _warn_insecure(message: str) -> None:
    """Emite un warning de seguridad cuando la integración no va por HTTPS."""
    logger.warning("[BACK] %s", message)


def _maybe_warn_https() -> None:
    """Advierte en el arranque si HTTPS está requerido y el servidor no lo usa."""
    if INTEGRATION_HTTPS_REQUIRED:
        _warn_insecure(
            "La integración LAN exige HTTPS; asegúrese de servir la API por TLS "
            "y no por HTTP en la red."
        )


def _build_synth_session(bearer_user: dict) -> dict:
    """Construye la sesión sintética (mismas claves que do_login) a partir de
    la identidad del validador resuelta del bearer token en ``flask.g``.

    Solo vive durante la request; no se persiste como cookie de sesión.
    """
    return {
        "ce_authenticated": True,
        "username": bearer_user["username"],
        "rol": bearer_user["rol"],
        "permisos": bearer_user["permisos"],
        "primer_nombre": bearer_user.get("primer_nombre", ""),
        "segundo_nombre": bearer_user.get("segundo_nombre", ""),
        "apellido_1": bearer_user.get("apellido_1", ""),
        "apellido_2": bearer_user.get("apellido_2", ""),
    }


@integration_bp.post("/control-novedades")
def control_novedades_submit():
    """Envía una novedad autenticada por bearer token.

    La identidad del validador se resuelve desde el token en _handle_bearer_auth
    (before_request) y se expone en ``flask.g`` (per-request, sin cookie). El
    permiso ``control_urgencias:write`` se valida AQUÍ manualmente leyendo
    ``g.bearer_user`` porque permiso_requerido (app/utils/auth.py) solo lee la
    sesión de browser, y este endpoint es "sin sesión". Luego se delega al
    servicio construyendo la sesión sintética efímera.
    """
    # R1-2/R2-2/R3-4: la integración exige HTTPS en runtime (salvo TESTING).
    if (
        INTEGRATION_HTTPS_REQUIRED
        and not current_app.config.get("TESTING")
        and not request.is_secure
    ):
        _warn_insecure("Petición no TLS al endpoint de integración rechazada")
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["HTTPS requerido para la integración"],
        }), 403

    data = request.get_json(silent=True) or {}
    bearer = g.get("bearer_user")

    # D6: validación manual del permiso de escritura. permiso_requerido lee
    # session['permisos'] (ruta browser) y no g.bearer_user, así que el endpoint
    # de integración (sin sesión) debe verificar la identidad del bearer aquí.
    permisos = bearer.get("permisos", []) if bearer else []
    if "control_urgencias:write" not in permisos and "*" not in permisos:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Permiso denegado"],
        }), 403

    synth_session = _build_synth_session(bearer) if bearer else None
    envelope, status = submit(data, synth_session)
    return jsonify(envelope), status


@integration_bp.get("/tokens")
@admin_requerido
def list_tokens():
    """Lista los tokens activos (sin exponer hashes)."""
    tokens = token_store.list_tokens()
    return jsonify({"status": "success", "data": {"tokens": tokens}, "errors": []})


@integration_bp.post("/tokens")
@admin_requerido
def issue_token():
    """Emite un token para un usuario validador; devuelve el valor en claro una vez."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Campo requerido: username"],
        }), 400
    permanent = data.get("permanent", False)
    if not isinstance(permanent, bool):
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Campo inválido: permanent debe ser booleano"],
        }), 400
    try:
        raw, record = token_store.issue_token(username, permanent=permanent)
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 400
    return jsonify({
        "status": "success",
        "data": {"token": raw, "record": record},
        "errors": [],
    }), 201


@integration_bp.post("/tokens/<int:token_id>/rotate")
@admin_requerido
def rotate_token(token_id: int):
    """Rota un token; devuelve el nuevo valor en claro una vez."""
    try:
        raw, record = token_store.rotate_token(token_id)
    except ValueError as e:
        return jsonify({"status": "error", "data": {}, "errors": [str(e)]}), 404
    return jsonify({
        "status": "success",
        "data": {"token": raw, "record": record},
        "errors": [],
    })


@integration_bp.post("/tokens/<int:token_id>/revoke")
@admin_requerido
def revoke_token(token_id: int):
    """Revoca un token activo."""
    ok = token_store.revoke_token(token_id)
    if not ok:
        return jsonify({
            "status": "error",
            "data": {},
            "errors": ["Token no encontrado o ya revocado"],
        }), 404
    return jsonify({"status": "success", "data": {"revoked": True}, "errors": []})
