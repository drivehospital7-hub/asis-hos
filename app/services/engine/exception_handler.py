"""ExceptionHandler — applies skip/downgrade/override exceptions to rules.

Queries active exceptions for a rule, checks scope conditions against context,
and returns the applicable effect.
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


class ExceptionHandler:
    """Checks for active exceptions that modify or suspend a rule for a scope.

    Usage:
        handler = ExceptionHandler()
        effect, overrides = handler.apply_exceptions(rule, context, session)
        # effect: 'normal', 'skip', 'override'
        # overrides: dict of param overrides (only for 'override')
    """

    def apply_exceptions(
        self,
        rule: "Regla",
        context: "EvaluationContext",
        session: "Session",
    ) -> tuple[str, dict[str, Any] | None]:
        """Check for active exceptions affecting this rule + context.

        Returns:
            (effect, overrides) where effect is 'normal', 'skip', or 'override'.
            overrides is None unless effect is 'override'.
        """
        exceptions = (
            session.query(Excepcion)
            .filter(Excepcion.regla_id == rule.id)
            .filter(Excepcion.activo == True)  # noqa: E712
            .all()
        )

        if not exceptions:
            return "normal", None

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
