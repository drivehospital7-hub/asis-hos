"""Rule CRUD with auto-versioning and version management.

All functions accept a SQLAlchemy Session as first argument.
Returns dicts matching the Regla.to_dict() shape with additions.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from app.models import Condicion, Excepcion, Regla

logger = logging.getLogger(__name__)

# Fields that can be updated / compared for no-op detection
_MUTABLE_FIELDS = frozenset({
    "nombre", "descripcion", "dominio", "severidad", "prioridad",
    "activo", "parametros", "parametros_default",
})


def _build_condition_tree(regla: Regla) -> list[dict[str, Any]] | None:
    """Build a nested condition tree from flat condición list.

    Conditions form a self-referencing tree via padre_id.
    Root nodes have padre_id=None. Children are nested under their parent.
    """
    conditions = regla.condiciones or []
    if not conditions:
        return None

    # Index by id
    by_id: dict[int, dict[str, Any]] = {}
    for c in conditions:
        by_id[c.id] = c.to_dict()
        by_id[c.id]["condiciones"] = []

    # Build tree
    roots: list[dict[str, Any]] = []
    for c in conditions:
        node = by_id[c.id]
        if c.padre_id is None:
            roots.append(node)
        elif c.padre_id in by_id:
            by_id[c.padre_id]["condiciones"].append(node)

    return roots


def _has_changes(rule: Regla, data: dict) -> bool:
    """Check if any mutable field actually changed."""
    for field in _MUTABLE_FIELDS:
        if field in data:
            current = getattr(rule, field, None)
            new_val = data[field]
            if current != new_val:
                return True
    return False


def _apply_updates(rule: Regla, data: dict) -> None:
    """Apply partial updates to a Regla instance from a data dict."""
    for field in _MUTABLE_FIELDS:
        if field in data:
            setattr(rule, field, data[field])


def _clone_conditions(db_session, old_rule_id: int, new_rule_id: int) -> None:
    """Clone all conditions from old_rule_id to new_rule_id.

    Handles the self-referencing padre_id mapping.
    """
    old_conds = (
        db_session.query(Condicion)
        .filter(Condicion.regla_id == old_rule_id)
        .all()
    )
    if not old_conds:
        return

    # First pass: create all conditions without padre_id, build mapping
    id_map: dict[int, int] = {}
    new_conds: list[Condicion] = []
    for c in old_conds:
        new_c = Condicion(
            regla_id=new_rule_id,
            padre_id=None,  # Will fix in second pass
            tipo=c.tipo,
            operador=c.operador,
            fuente_datos=c.fuente_datos,
            valor_esperado=copy.deepcopy(c.valor_esperado) if c.valor_esperado else None,
            orden=c.orden,
        )
        db_session.add(new_c)
        db_session.flush()  # Get ID
        id_map[c.id] = new_c.id
        new_conds.append(new_c)

    # Second pass: fix padre_id references
    for old_c, new_c in zip(old_conds, new_conds):
        if old_c.padre_id is not None and old_c.padre_id in id_map:
            new_c.padre_id = id_map[old_c.padre_id]

    db_session.flush()


# ─── Public API ──────────────────────────────────────────────────────


def create_rule(db_session, data: dict) -> dict:
    """Create a new rule as draft, version=1.

    Args:
        db_session: SQLAlchemy Session
        data: Rule data including optional nested 'condiciones' and 'excepciones'

    Returns:
        dict: Created rule serialized
    """
    condiciones_data = data.pop("condiciones", None)
    excepciones_data = data.pop("excepciones", None)

    rule = Regla(
        rule_base_id=None,  # Will be set after insert
        nombre=data.get("nombre", ""),
        descripcion=data.get("descripcion"),
        dominio=data.get("dominio", ""),
        estado="draft",
        version=1,
        prioridad=data.get("prioridad", 100),
        severidad=data.get("severidad", "error"),
        activo=data.get("activo", True),
        parametros=data.get("parametros"),
        parametros_default=data.get("parametros_default"),
    )
    db_session.add(rule)
    db_session.flush()  # Get ID

    # Set rule_base_id = id for the first version
    rule.rule_base_id = rule.id

    # Store condiciones tree
    if condiciones_data:
        _store_condition_tree(db_session, rule.id, None, condiciones_data)

    # Store excepciones
    if excepciones_data:
        for exc_data in excepciones_data:
            exc = Excepcion(
                regla_id=rule.id,
                tipo_efecto=exc_data.get("tipo_efecto", "skip"),
                condicion_json=exc_data.get("condicion_json", {}),
                activo=exc_data.get("activo", True),
            )
            db_session.add(exc)

    db_session.flush()
    db_session.commit()

    return rule.to_dict()


def _store_condition_tree(db_session, regla_id: int, padre_id: int | None, node: dict) -> int | None:
    """Recursively store a condition tree node and return its id."""
    cond = Condicion(
        regla_id=regla_id,
        padre_id=padre_id,
        tipo=node.get("tipo", "atomic"),
        operador=node.get("operador"),
        fuente_datos=node.get("fuente_datos"),
        valor_esperado=node.get("valor_esperado"),
        orden=node.get("orden", 0),
    )
    db_session.add(cond)
    db_session.flush()
    cond_id = cond.id

    # Store children if composite
    children = node.get("condiciones", [])
    if children:
        for child in children:
            _store_condition_tree(db_session, regla_id, cond_id, child)

    return cond_id


def get_rule(db_session, rule_id: int) -> dict | None:
    """Get a single rule with nested condition tree and exceptions.

    Args:
        db_session: SQLAlchemy Session
        rule_id: Rule ID

    Returns:
        dict with 'condiciones' (nested tree) and 'excepciones', or None
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule:
        return None

    result = rule.to_dict()
    result["condiciones"] = _build_condition_tree(rule)

    if rule.excepciones:
        result["excepciones"] = [e.to_dict() for e in rule.excepciones]
    else:
        result["excepciones"] = []

    return result


def list_rules(
    db_session,
    dominio: str | None = None,
    estado: str | None = None,
    activo: bool | None = None,
) -> list[dict]:
    """List rules with optional filters.

    Args:
        db_session: SQLAlchemy Session
        dominio: Filter by dominio
        estado: Filter by estado
        activo: Filter by activo boolean

    Returns:
        list of rule dicts
    """
    query = db_session.query(Regla)

    if dominio is not None:
        query = query.filter(Regla.dominio == dominio)
    if estado is not None:
        query = query.filter(Regla.estado == estado)
    if activo is not None:
        query = query.filter(Regla.activo == activo)

    rules = query.all()
    return [r.to_dict() for r in rules]


def update_rule(db_session, rule_id: int, data: dict) -> dict:
    """Update a rule with auto-versioning.

    Deprecates the current active version and creates a new version
    with incremented version number. Transactional.

    Args:
        db_session: SQLAlchemy Session
        rule_id: ID of the active rule to update
        data: Partial update fields

    Returns:
        dict with old_rule_id, new_rule_id, old_version, new_version

    Raises:
        ValueError: If rule is not active or not found
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule:
        raise ValueError(f"Rule {rule_id} not found")
    if rule.estado != "active":
        raise ValueError(f"Cannot modify non-active rule (current: {rule.estado})")

    # No-op guard: if nothing changed, return same IDs
    if not _has_changes(rule, data):
        return {
            "old_rule_id": rule_id,
            "new_rule_id": rule_id,
            "old_version": rule.version,
            "new_version": rule.version,
        }

    try:
        # 1. Deprecate current
        old_version = rule.version
        old_rule_id = rule.id
        rule.estado = "deprecated"
        db_session.flush()

        # 1b. Find next available version (avoid collisions with retired versions)
        max_ver_row = (
            db_session.query(Regla.version)
            .filter(Regla.nombre == rule.nombre)
            .order_by(Regla.version.desc())
            .first()
        )
        max_ver = int(max_ver_row[0]) if max_ver_row else 0
        next_version = max(max_ver, rule.version) + 1

        # 2. Create new version
        new_rule = Regla(
            rule_base_id=rule.rule_base_id,
            nombre=rule.nombre,
            descripcion=rule.descripcion,
            dominio=rule.dominio,
            estado="active",
            version=next_version,
            prioridad=rule.prioridad,
            severidad=rule.severidad,
            activo=rule.activo,
            parametros=rule.parametros,
            parametros_default=rule.parametros_default,
        )
        # Apply partial updates
        _apply_updates(new_rule, data)
        db_session.add(new_rule)
        db_session.flush()
        new_rule_id = new_rule.id

        # 3. Clone conditions
        _clone_conditions(db_session, old_rule_id, new_rule_id)

        db_session.commit()
        return {
            "old_rule_id": old_rule_id,
            "new_rule_id": new_rule_id,
            "old_version": old_version,
            "new_version": new_rule.version,
        }
    except Exception:
        db_session.rollback()
        logger.exception("Auto-versioning transaction failed for rule %s", rule_id)
        raise


def delete_rule(db_session, rule_id: int) -> None:
    """Soft-delete a rule by setting estado=retired.

    Args:
        db_session: SQLAlchemy Session
        rule_id: Rule ID

    Raises:
        ValueError: If rule not found or already retired
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule:
        raise ValueError(f"Rule {rule_id} not found")
    if rule.estado == "retired":
        raise ValueError(f"Rule {rule_id} is already retired")

    rule.estado = "retired"
    db_session.commit()


def list_versions(db_session, rule_id: int) -> list[dict]:
    """List all versions of a rule, ordered by version DESC.

    Uses rule_base_id to find related versions.

    Args:
        db_session: SQLAlchemy Session
        rule_id: ID of any version of the rule

    Returns:
        list of version dicts ordered newest first
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule or rule.rule_base_id is None:
        return []

    versions = (
        db_session.query(Regla)
        .filter(Regla.rule_base_id == rule.rule_base_id)
        .order_by(Regla.version.desc())
        .all()
    )
    return [v.to_dict() for v in versions]


def create_version(db_session, rule_id: int) -> dict:
    """Clone the current active version as a new draft.

    The original remains active. The new version has estado=draft.

    Args:
        db_session: SQLAlchemy Session
        rule_id: ID of the active rule to version

    Returns:
        dict: New version serialized
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule:
        raise ValueError(f"Rule {rule_id} not found")

    # Find next available version
    max_ver_row = (
        db_session.query(Regla.version)
        .filter(Regla.nombre == rule.nombre)
        .order_by(Regla.version.desc())
        .first()
    )
    max_ver = int(max_ver_row[0]) if max_ver_row else 0
    next_version = max(max_ver, rule.version) + 1

    new_rule = Regla(
        rule_base_id=rule.rule_base_id,
        nombre=rule.nombre,
        descripcion=rule.descripcion,
        dominio=rule.dominio,
        estado="draft",
        version=next_version,
        prioridad=rule.prioridad,
        severidad=rule.severidad,
        activo=rule.activo,
        parametros=rule.parametros,
        parametros_default=rule.parametros_default,
    )
    db_session.add(new_rule)
    db_session.flush()

    # Clone conditions
    _clone_conditions(db_session, rule.id, new_rule.id)

    db_session.commit()
    return new_rule.to_dict()
