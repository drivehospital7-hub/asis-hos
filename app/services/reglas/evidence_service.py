"""Evidence query service — wraps EvidenceRepository with combined filters and pagination.

Provides a single query_evidence() function that accepts multiple optional
filters and returns paginated results with a total count.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.services.engine.evidence_repository import EvidenceRepository

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 100
_DEFAULT_OFFSET = 0


def query_evidence(
    db_session,
    regla_id: int | None = None,
    factura: str | None = None,
    dominio: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    limit: int = _DEFAULT_LIMIT,
    offset: int = _DEFAULT_OFFSET,
) -> dict:
    """Query evidence records with optional filters and pagination.

    Args:
        db_session: SQLAlchemy Session
        regla_id: Filter by rule ID
        factura: Filter by factura number
        dominio: Filter by domain
        desde: Start date (ISO string, inclusive)
        hasta: End date (ISO string, inclusive)
        limit: Max results per page (default 100)
        offset: Pagination offset (default 0)

    Returns:
        dict with keys: items, total, limit, offset
    """
    from app.models import Evidencia

    query = db_session.query(Evidencia)

    if regla_id is not None:
        query = query.filter(Evidencia.regla_id == regla_id)
    if factura is not None:
        query = query.filter(Evidencia.factura == factura)
    if dominio is not None:
        query = query.filter(Evidencia.dominio == dominio)
    if desde is not None:
        try:
            dt_desde = datetime.fromisoformat(desde)
            query = query.filter(Evidencia.creado_en >= dt_desde)
        except ValueError:
            logger.warning("Invalid desde date: %s", desde)
    if hasta is not None:
        try:
            dt_hasta = datetime.fromisoformat(hasta)
            query = query.filter(Evidencia.creado_en <= dt_hasta)
        except ValueError:
            logger.warning("Invalid hasta date: %s", hasta)

    total = query.count()

    items = (
        query
        .order_by(Evidencia.creado_en.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "items": [e.to_dict() for e in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
