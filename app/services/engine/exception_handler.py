"""ExceptionHandler — applies skip/downgrade/override exceptions to rules.

Queries active exceptions for a rule, checks scope conditions against context,
and returns the applicable effect.

Supports cached-exception pattern: call ``query_exceptions()`` once per rule
before the row loop, then pass the result to ``apply_exceptions()`` via
``cached_exc=`` to avoid per-row DB queries.
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from app.models import Excepcion

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models import Regla
    from app.services.engine.context import EvaluationContext

logger = logging.getLogger(__name__)


# Type alias: apply_exceptions accepts either a full EvaluationContext
# or a plain dict (optimization: skip context creation for exception check).
_ContextOrDict = "EvaluationContext | dict[str, Any]"


class ExceptionHandler:
    """Checks for active exceptions that modify or suspend a rule for a scope.

    Usage:
        handler = ExceptionHandler()

        # Phase 1 (query once before loop):
        excs = handler.query_exceptions(rule, session)

        # Phase 2 (per row — uses cached list):
        effect, overrides = handler.apply_exceptions(rule, ctx, session, cached_exc=excs)

        # Legacy (per row — queries DB each time):
        effect, overrides = handler.apply_exceptions(rule, ctx, session)
    """

    @staticmethod
    def query_exceptions(
        rule: "Regla",
        session: "Session",
    ) -> list[Excepcion]:
        """Query all active exceptions for a rule.

        Intended to be called ONCE per rule before the row loop.  The returned
        list is shared across all rows via ``apply_exceptions(cached_exc=...)``.

        Returns:
            List of active Excepcion ORM objects (may be empty).
        """
        return (
            session.query(Excepcion)
            .filter(Excepcion.regla_id == rule.id)
            .filter(Excepcion.activo == True)  # noqa: E712
            .all()
        )

    def apply_exceptions(
        self,
        rule: "Regla",
        context: "EvaluationContext | dict[str, Any]",
        session: "Session",
        cached_exc: list[Excepcion] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Check for active exceptions affecting this rule + context.

        Args:
            rule: The Regla being evaluated.
            context: Per-row EvaluationContext (with invoice_data) OR a plain
                row_data dict. When a plain dict is passed, ``_matches_scope``
                uses it directly as invoice_data — this avoids an unnecessary
                EvaluationContext creation for the exception check.
            session: SQLAlchemy session (used only when cached_exc is None).
            cached_exc: Pre-queried exception list from ``query_exceptions()``.
                When provided, the DB query is skipped entirely.

        Returns:
            (effect, overrides) where effect is 'normal', 'skip', or 'override'.
            overrides is None unless effect is 'override'.
        """
        if cached_exc is not None:
            exceptions = cached_exc
        else:
            exceptions = self.query_exceptions(rule, session)

        if not exceptions:
            return "normal", None

        # Accept both EvaluationContext.invoice_data and plain dict
        invoice_data: dict[str, Any]
        if isinstance(context, dict):
            invoice_data = context
        else:
            invoice_data = context.invoice_data or {}

        for exc in exceptions:
            if self._matches_scope(exc, invoice_data):
                logger.info(
                    "Exception matched: rule=%s tipo_efecto=%s exc_id=%d",
                    rule.nombre, exc.tipo_efecto, exc.id,
                )
                if exc.tipo_efecto == "skip":
                    return "skip", None
                elif exc.tipo_efecto == "override":
                    return "override", exc.parametros_override

        return "normal", None

    def _matches_scope(self, exception: Excepcion, invoice_data: dict) -> bool:
        """Check if the exception's scope condition matches the invoice data.

        The condicion_json is a dict like {"convenio": "PyP"} — all keys must match.
        """
        scope = exception.condicion_json or {}
        if not scope:
            return True  # Empty scope matches everything

        for key, expected in scope.items():
            actual = invoice_data.get(key)
            if actual != expected:
                return False
        return True
