"""Audit query service — query ResultadoAuditoria with filters and pagination.

Provides a single query_audit() function with combined filters and paginated results.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.models import ResultadoAuditoria

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 100
_DEFAULT_OFFSET = 0


def query_audit(
    db_session,
    regla_id: int | None = None,
    factura: str | None = None,
    resultado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    offset: int = _DEFAULT_OFFSET,
) -> dict:
    """Query audit results with optional filters and pagination.

    Args:
        db_session: SQLAlchemy Session
        regla_id: Filter by rule ID
        factura: Filter by factura number
        resultado: Filter by resultado (MATCH, NO_MATCH, etc.)
        desde: Start date (ISO string, inclusive)
        hasta: End date (ISO string, inclusive)
        limit: Max results per page (default 100)
        offset: Pagination offset (default 0)

    Returns:
        dict with keys: items, total, limit, offset
    """
    query = db_session.query(ResultadoAuditoria)

    if regla_id is not None:
        query = query.filter(ResultadoAuditoria.regla_id == regla_id)
    if factura is not None:
        query = query.filter(ResultadoAuditoria.factura == factura)
    if resultado is not None:
        query = query.filter(ResultadoAuditoria.resultado == resultado)
    if desde is not None:
        try:
            dt_desde = datetime.fromisoformat(desde)
            query = query.filter(ResultadoAuditoria.creado_en >= dt_desde)
        except ValueError:
            logger.warning("Invalid desde date: %s", desde)
    if hasta is not None:
        try:
            dt_hasta = datetime.fromisoformat(hasta)
            query = query.filter(ResultadoAuditoria.creado_en <= dt_hasta)
        except ValueError:
            logger.warning("Invalid hasta date: %s", hasta)

    total = query.count()

    items = (
        query
        .order_by(ResultadoAuditoria.creado_en.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "items": [r.to_dict() for r in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
