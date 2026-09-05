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


def _condition_nodes(data: Any) -> list[dict[str, Any]]:
    """Return a condition payload as a list of root nodes."""
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def _condition_signature(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ignore database/editor IDs when comparing nested condition trees."""
    return [
        {
            key: node.get(key)
            for key in ("tipo", "operador", "fuente_datos", "valor_esperado", "orden")
        }
        | {"condiciones": _condition_signature(_condition_nodes(node.get("condiciones")))}
        for node in nodes
    ]


def _validate_condition_tree(nodes: list[dict[str, Any]]) -> None:
    """Reject malformed composite trees before creating a new rule version."""
    for node in nodes:
        children = _condition_nodes(node.get("condiciones"))
        if node.get("operador") == "NOT" and len(children) != 1:
            raise ValueError("NOT conditions must have exactly one child")
        _validate_condition_tree(children)


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
    if "condiciones" in data:
        current_tree = _build_condition_tree(rule) or []
        submitted_tree = _condition_nodes(data["condiciones"])
        return _condition_signature(current_tree) != _condition_signature(submitted_tree)
    return False


def _apply_updates(rule: Regla, data: dict) -> None:
    """Apply partial updates to a Regla instance from a data dict."""
    for field in _MUTABLE_FIELDS:
        if field in data:
            setattr(rule, field, data[field])


def _ensure_rule_base_id(rule: Regla) -> int:
    """Ensure a persisted rule has a stable lineage identifier."""
    if rule.rule_base_id is None:
        rule.rule_base_id = rule.id
    return rule.rule_base_id


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
            valor_esperado=(
                copy.deepcopy(c.valor_esperado)
                if c.valor_esperado is not None
                else None
            ),
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
        condition_nodes = _condition_nodes(condiciones_data)
        _validate_condition_tree(condition_nodes)
        for node in condition_nodes:
            _store_condition_tree(db_session, rule.id, None, node)

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


def update_rule(
    db_session,
    rule_id: int,
    data: dict,
    responsible: str | None = None,
) -> dict:
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

    if "condiciones" in data:
        _validate_condition_tree(_condition_nodes(data["condiciones"]))

    # No-op guard: if nothing changed, return same IDs
    if not _has_changes(rule, data):
        return {
            "old_rule_id": rule_id,
            "new_rule_id": rule_id,
            "old_version": rule.version,
            "new_version": rule.version,
        }

    change_what = str(data.get("cambio_que", "")).strip()
    change_why = str(data.get("cambio_por_que", "")).strip()
    if not change_what or not change_why:
        raise ValueError("cambio_que y cambio_por_que son requeridos al crear una versión")
    if responsible is not None and not responsible.strip():
        raise ValueError("No se pudo determinar el usuario autenticado")

    try:
        # 1. Deprecate current
        old_version = rule.version
        old_rule_id = rule.id
        rule_base_id = _ensure_rule_base_id(rule)
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
            rule_base_id=rule_base_id,
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
            cambio_que=change_what,
            cambio_por_que=change_why,
            cambio_responsable=responsible,
        )
        # Apply partial updates
        _apply_updates(new_rule, data)
        db_session.add(new_rule)
        db_session.flush()
        new_rule_id = new_rule.id

        # 3. Persist submitted conditions; otherwise preserve the old tree.
        if "condiciones" in data:
            for node in _condition_nodes(data["condiciones"]):
                _store_condition_tree(db_session, new_rule_id, None, node)
        else:
            _clone_conditions(db_session, old_rule_id, new_rule_id)

        db_session.commit()
        return {
            "old_rule_id": old_rule_id,
            "new_rule_id": new_rule_id,
            "old_version": old_version,
            "new_version": new_rule.version,
            "cambio_que": new_rule.cambio_que,
            "cambio_por_que": new_rule.cambio_por_que,
            "cambio_responsable": new_rule.cambio_responsable,
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

    rule_base_id = _ensure_rule_base_id(rule)

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
        rule_base_id=rule_base_id,
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


def publish_rule(
    db_session,
    rule_id: int,
    responsible: str | None = None,
    cambio_que: str | None = None,
    cambio_por_que: str | None = None,
) -> dict:
    """Promote a draft rule to active in the SAME row (draft → active).

    Deprecates (estado="deprecated") the current active version of the same
    rule_base_id, preserving the invariant "at most one active per
    rule_base_id". No new version is created; version/activo/condiciones
    are left untouched. cambio_que/cambio_por_que are optional audit
    metadata; only responsible is required.

    Args:
        db_session: SQLAlchemy Session
        rule_id: ID of the draft rule to publish
        responsible: authenticated username, persisted as cambio_responsable
        cambio_que: optional audit field ("what changed")
        cambio_por_que: optional audit field ("why changed")

    Returns:
        dict: published rule serialized with an extra deprecated_id key
        (id of the deprecated incumbent, or None).

    Raises:
        ValueError: rule not found, not a draft, no responsible, or empty
            condition tree.
    """
    rule: Regla | None = (
        db_session.query(Regla)
        .filter(Regla.id == rule_id)
        .first()
    )
    if not rule:
        raise ValueError(f"Rule {rule_id} not found")
    if rule.estado != "draft":
        raise ValueError(f"Solo se pueden publicar reglas en estado draft (current: {rule.estado})")
    if responsible is None or not responsible.strip():
        raise ValueError("No se pudo determinar el usuario autenticado")
    tree = _build_condition_tree(rule)
    if not tree:
        raise ValueError("No se puede publicar una regla sin condiciones")

    try:
        rule_base_id = _ensure_rule_base_id(rule)

        # Deprecate the current active incumbent of the same lineage (if any).
        incumbent: Regla | None = (
            db_session.query(Regla)
            .filter(
                Regla.rule_base_id == rule_base_id,
                Regla.estado == "active",
                Regla.id != rule.id,
            )
            .first()
        )
        deprecated_id = None
        if incumbent:
            incumbent.estado = "deprecated"
            deprecated_id = incumbent.id

        # Promote the draft in the same row.
        rule.estado = "active"
        rule.cambio_responsable = responsible
        if cambio_que is not None:
            rule.cambio_que = str(cambio_que).strip()
        if cambio_por_que is not None:
            rule.cambio_por_que = str(cambio_por_que).strip()

        db_session.commit()
        return {**rule.to_dict(), "deprecated_id": deprecated_id}
    except Exception:
        db_session.rollback()
        logger.exception("Publish transaction failed for rule %s", rule_id)
        raise
