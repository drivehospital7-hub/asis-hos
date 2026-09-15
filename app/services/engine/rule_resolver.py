"""RuleResolver — loads enabled rules by domain, sorted by priority.

Single-flag cutover: filters ONLY by activo (no estado filter).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models import Regla

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RuleResolver:
    """Loads enabled rules from the database for a given domain.

    Usage:
        resolver = RuleResolver()
        rules = resolver.resolve("odontologia", session)
    """

    def resolve(self, domain: str, session: "Session") -> list[Regla]:
        """Load enabled rules matching the domain OR transversal, ordered by priority.

        Transversal rules apply to ALL domains.

        Args:
            domain: Domain filter (e.g., 'odontologia', 'urgencias').
            session: SQLAlchemy session.

        Returns:
            List of Regla instances, ordered by prioridad ASC.
        """
        rules = (
            session.query(Regla)
            .filter(
                (Regla.dominio == domain) | (Regla.dominio == "transversal")
            )
            .filter(Regla.activo == True)  # noqa: E712
            .order_by(Regla.prioridad.asc())
            .all()
        )
        logger.info("RuleResolver: loaded %d enabled rules for domain=%s", len(rules), domain)
        return rules
