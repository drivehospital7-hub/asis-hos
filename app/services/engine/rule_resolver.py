"""RuleResolver — loads enabled rules by domain, sorted by priority.

Single-flag cutover: filters ONLY by activo (no estado filter).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import and_, exists, or_, select

from app.constants.base import ENGINE_DOMAIN_TRANSVERSAL
from app.models import Regla, ReglaDominio

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def rule_matches_domain(regla_id_column, domain: str):
    """Shared scope predicate: bridge scope contains domain or transversal.

    Single helper for all engine resolution (sdd reglas-multi-dominio, D3):
    portable EXISTS over regla_dominios, indexable on both PG and SQLite.
    """
    return exists(
        select(1)
        .where(ReglaDominio.regla_id == regla_id_column)
        .where(ReglaDominio.dominio.in_([domain, ENGINE_DOMAIN_TRANSVERSAL]))
    )


def rule_has_no_scope(regla_id_column):
    """True when a rule row carries zero bridge entries (legacy fallback)."""
    return ~exists(
        select(1).where(ReglaDominio.regla_id == regla_id_column)
    )


def rule_matches_domain_or_legacy(regla_id_column, domain: str):
    """Bridge scope hit, or legacy single-column semantics for scope-less rows."""
    return or_(
        rule_matches_domain(regla_id_column, domain),
        and_(
            rule_has_no_scope(regla_id_column),
            or_(
                Regla.dominio == domain,
                Regla.dominio == ENGINE_DOMAIN_TRANSVERSAL,
            ),
        ),
    )


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
            .filter(rule_matches_domain_or_legacy(Regla.id, domain))
            .filter(Regla.activo == True)  # noqa: E712
            .order_by(Regla.prioridad.asc())
            .all()
        )
        logger.info("RuleResolver: loaded %d enabled rules for domain=%s", len(rules), domain)
        return rules
