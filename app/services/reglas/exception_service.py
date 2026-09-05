"""Exception CRUD service — manage Excepcion records linked to a rule.

Provides list, create operations for rule exceptions.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models import Excepcion

logger = logging.getLogger(__name__)


def list_exceptions(db_session, rule_id: int) -> list[dict[str, Any]]:
    """List all exceptions for a given rule.

    Args:
        db_session: SQLAlchemy Session
        rule_id: Rule ID

    Returns:
        list of exception dicts
    """
    exceptions = (
        db_session.query(Excepcion)
        .filter(Excepcion.regla_id == rule_id)
        .all()
    )
    return [e.to_dict() for e in exceptions]


def create_exception(db_session, rule_id: int, data: dict) -> dict[str, Any]:
    """Create a new exception for a rule.

    Args:
        db_session: SQLAlchemy Session
        rule_id: Rule ID
        data: Exception data with tipo_efecto, condicion_json, activo

    Returns:
        dict: Created exception serialized

    Raises:
        ValueError: If tipo_efecto is missing
    """
    if "tipo_efecto" not in data:
        raise ValueError("Campo requerido: tipo_efecto")

    exc = Excepcion(
        regla_id=rule_id,
        tipo_efecto=data["tipo_efecto"],
        condicion_json=data.get("condicion_json", {}),
        parametros_override=data.get("parametros_override"),
        activo=data.get("activo", True),
    )
    db_session.add(exc)
    db_session.commit()

    return exc.to_dict()
