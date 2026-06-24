"""EvidenceRepository — read-only query access to evidence records.

Provides paginated query methods for evidence retrieval by rule, factura,
dominio, and date range. All methods are static and read-only.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models import Evidencia

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EvidenceRepository:
    """Read-only query access to evidence records."""

    @staticmethod
    def find_by_rule(session: "Session", regla_id: int, limit: int = 100, offset: int = 0) -> list[Evidencia]:
        """Return evidence records for a given rule_id, ordered by creation time."""
        return (
            session.query(Evidencia)
            .filter(Evidencia.regla_id == regla_id)
            .order_by(Evidencia.creado_en.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def find_by_factura(session: "Session", factura: str, limit: int = 100, offset: int = 0) -> list[Evidencia]:
        """Return evidence records for a given factura, ordered by creation time."""
        return (
            session.query(Evidencia)
            .filter(Evidencia.factura == factura)
            .order_by(Evidencia.creado_en.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def find_by_domain(session: "Session", dominio: str, limit: int = 100, offset: int = 0) -> list[Evidencia]:
        """Return evidence records for a given dominio, ordered by creation time."""
        return (
            session.query(Evidencia)
            .filter(Evidencia.dominio == dominio)
            .order_by(Evidencia.creado_en.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def find_by_date_range(
        session: "Session",
        start: "datetime",
        end: "datetime",
        limit: int = 100,
        offset: int = 0,
    ) -> list[Evidencia]:
        """Return evidence records with creado_en between start and end (inclusive)."""
        from datetime import datetime  # noqa: F811 — keep import local for TYPE_CHECKING compat

        return (
            session.query(Evidencia)
            .filter(Evidencia.creado_en >= start)
            .filter(Evidencia.creado_en <= end)
            .order_by(Evidencia.creado_en.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def count_by_rule(session: "Session", regla_id: int) -> int:
        """Return total count of evidence records for a given rule_id."""
        return (
            session.query(Evidencia)
            .filter(Evidencia.regla_id == regla_id)
            .count()
        )

    @staticmethod
    def count_by_domain(session: "Session", dominio: str) -> int:
        """Return total count of evidence records for a given dominio."""
        return (
            session.query(Evidencia)
            .filter(Evidencia.dominio == dominio)
            .count()
        )
