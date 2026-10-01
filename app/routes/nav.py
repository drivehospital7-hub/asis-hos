"""GET /api/nav — modulos de navegacion filtrados por permisos de sesion.

El sidebar React renderiza SOLO desde aqui (su lista propia ``ALL_NAV``
se elimina en Task 3). Respuesta con envelope canonico::

    {"status": "success", "data": {"modulos": [...]}, "errors": []}

Cada modulo es ``{"label": ..., "href": ..., "icon": ...}`` (``icon`` es el
nombre lucide; el frontend mapea nombre → componente con fallback generico).

Sin ``permiso_requerido``: anonimo → ``{"modulos": []}`` (el endpoint es
publico en ``PUBLIC_ENDPOINTS`` para atravesar el middleware global de
auth; el filtrado por sesion lo hace ``modulos_para`` en servidor).
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, session


logger = logging.getLogger(__name__)

nav_bp = Blueprint("nav", __name__)


@nav_bp.get("/api/nav")
def nav_api():
    """Retorna los modulos visibles para la sesion actual."""
    from app.constants.navigation import modulos_para

    permisos = session.get("permisos", []) or []
    autenticado = bool(session.get("ce_authenticated") or session.get("username") or permisos)
    modulos = modulos_para(permisos, autenticado=autenticado)
    logger.debug("GET /api/nav: %d modulos (autenticado=%s)", len(modulos), autenticado)
    return jsonify({
        "status": "success",
        "data": {
            "modulos": [
                {"label": m["label"], "href": m["href"], "icon": m["icon"]}
                for m in modulos
            ],
        },
        "errors": [],
    })
