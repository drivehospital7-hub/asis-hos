"""domain_detection — dynamic domain rule evaluation for detect_all orchestrators.

Resolves enabled rules for a domain via RuleResolver (dominio + transversal,
activo-only) and evaluates each DISTINCT nombre exactly once via
RuleBasedDetector, threading the AREA dominio. No hardcoded rule names:
enabling/disabling rules in the admin UI changes detection with zero code
edits. Transversal rules apply to every domain (resolver OR clause).

Skill asis-hos-detector-pattern: orchestrators call this helper (detection
lives in detectors/engine); results bucket by rule-declared grupo_error so
/​procesar grouping comes from the DB with the GRUPO_ERROR_MAPPING flag ON.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.services.engine.rule_resolver import RuleResolver

if TYPE_CHECKING:
    from openpyxl.worksheet.worksheet import Worksheet
    from sqlalchemy.orm import Session
    from app.services.engine.evidence_collector import EvidenceCollector

logger = logging.getLogger(__name__)

#: grupo_error whose findings feed TWO legacy buckets. Centralized here so
#: detect_all orchestrators stay free of rule names (legacy-presentation
#: split, not discovery).
GRUPO_CODIGO_ENTIDAD = "Codigo-Entidad-vs-Afiliacion"

#: The single rule of the grupo above that owns the codigo_entidad bucket;
#: every other grupo batch feeds the tipo_identificacion_entidad bucket.
REGLA_CODIGO_ENTIDAD = "codigo_entidad"

#: Request-scoped simulator override (set only by simulation_scope).
#: When not None, detect_domain_rules evaluates ONLY these rule ids.
_SIM_ONLY_RULE_IDS: ContextVar[frozenset[int] | None] = ContextVar(
    "sim_only_rule_ids", default=None
)

#: Request-scoped simulator override. When True, evidence/audit persistence
#: is forced off even if the caller passed persist=True (dry-run).
_SIM_NO_PERSIST: ContextVar[bool] = ContextVar("sim_no_persist", default=False)


@dataclass
class RuleBatch:
    """Detections of one resolved rule: nombre, grupo, items."""

    nombre: str
    grupo: str
    dominio: str
    items: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def simulation_scope(rule_ids: set[int] | frozenset[int] | None) -> Iterator[None]:
    """Scope the engine to a rule subset with persistence forced off.

    Used ONLY by the /admin/reglas simulator (dry-run): rules outside
    ``rule_ids`` are skipped and no evidence/audit rows are written.
    ``None`` means "all enabled rules" (still no persistence).
    Selected ids evaluate even when the rule is inactive, so admins can
    dry-run disabled rules without enabling them in production.
    Resets both overrides on exit; safe for nested/concurrent requests
    via ContextVar.
    """
    only = None if rule_ids is None else frozenset(rule_ids)
    token_ids = _SIM_ONLY_RULE_IDS.set(only)
    token_persist = _SIM_NO_PERSIST.set(True)
    try:
        yield
    finally:
        _SIM_ONLY_RULE_IDS.reset(token_ids)
        _SIM_NO_PERSIST.reset(token_persist)


def _load_selected_rules(session: "Session", domain: str, only_ids: frozenset[int]) -> list:
    """Load selected rules by id for a domain, regardless of activo flag.

    Simulator-only helper: mirrors the resolver domain semantics (exact
    domain OR transversal) so a disabled rule can be dry-run without
    enabling it. Best-effort: [] on any failure.
    """
    from app.models import Regla  # lazy: avoid import cycle

    try:
        rows = (
            session.query(Regla)
            .filter(Regla.id.in_(sorted(only_ids)))
            .filter((Regla.dominio == domain) | (Regla.dominio == "transversal"))
            .order_by(Regla.prioridad.asc())
            .all()
        )
        return list(rows or [])
    except Exception:
        logger.warning("simulation_scope: could not load selected rules", exc_info=True)
        return []


def detect_domain_rules(
    session: "Session",
    domain: str,
    data_sheet: "Worksheet | None" = None,
    indices: dict[str, int | None] | None = None,
    rows: list[dict[str, Any]] | None = None,
    persist: bool = False,
    evidence_collector: "EvidenceCollector | None" = None,
) -> list[RuleBatch]:
    """Evaluate every enabled rule for a domain exactly once per nombre.

    Args:
        session: Open SQLAlchemy session (lifecycle owned by the caller).
        domain: Area dominio (e.g., 'odontologia'); threaded into every
            detector so area isolation holds.
        data_sheet: openpyxl Worksheet with invoice data.
        indices: Column name → 0-based column index mapping.
        rows: Optional RowStore precargados (fast path).
        persist: Forwarded to detectors (defaults to False: no evidence/audit
            writes unless the caller opts in explicitly).
        evidence_collector: Shared collector, or None for per-rule default.

    Returns:
        Batches in resolver prioridad order, deduped by nombre (same nombre
        seeded in several dominios evaluates once — the engine loads the
        exact-domain row first).
    """
    # Lazy import mirrors the detect_all pattern: keeps the patch target
    # app.services.engine.rule_based_detector.RuleBasedDetector stable.
    from app.services.engine.rule_based_detector import RuleBasedDetector

    # Simulator scope (ContextVar): restrict to selected rule ids and
    # never persist evidence/audit (dry-run). Default: current behavior.
    only_ids = _SIM_ONLY_RULE_IDS.get()
    if _SIM_NO_PERSIST.get():
        persist = False

    batches: list[RuleBatch] = []
    seen: set[str] = set()

    def _evaluate(rule) -> None:
        if rule.nombre in seen:
            return
        seen.add(rule.nombre)
        if only_ids is not None and rule.id not in only_ids:
            return
        items = RuleBasedDetector(rule.nombre, session, dominio=domain).detect(
            data_sheet, indices, persist=persist, rows=rows,
            evidence_collector=evidence_collector,
        )
        batches.append(RuleBatch(
            nombre=rule.nombre,
            grupo=getattr(rule, "grupo_error", None) or rule.nombre,
            dominio=rule.dominio,
            items=items,
        ))

    for rule in RuleResolver().resolve(domain, session):
        _evaluate(rule)
    if only_ids is not None:
        # Selected but inactive rules never come from the resolver
        # (activo-only): load them explicitly so the simulator can
        # dry-run disabled rules without enabling them in production.
        for rule in _load_selected_rules(session, domain, only_ids):
            _evaluate(rule)
    logger.info(
        "domain_detection: evaluated %d rule(s) for domain=%s: %s",
        len(batches), domain, [b.nombre for b in batches],
    )
    return batches


def group_by_grupo(batches: list[RuleBatch]) -> dict[str, list[dict[str, Any]]]:
    """Bucket batch items by grupo_error (resolver prioridad order kept)."""
    grupos: dict[str, list[dict[str, Any]]] = {}
    for batch in batches:
        grupos.setdefault(batch.grupo, []).extend(batch.items)
    return grupos


def items_by_nombre(batches: list[RuleBatch]) -> dict[str, list[dict[str, Any]]]:
    """Index batch items by rule nombre (legacy-presentation splits only)."""
    return {batch.nombre: batch.items for batch in batches}


def split_codigo_entidad(
    grupos: dict[str, list[dict[str, Any]]],
    batches: list[RuleBatch],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split grupo Codigo-Entidad-vs-Afiliacion into two legacy buckets.

    Returns:
        (tipo_identificacion_entidad_items, codigo_entidad_items).
        Unknown future grupo batches default to the first bucket.
    """
    by_nombre = items_by_nombre(batches)
    codigo = list(by_nombre.get(REGLA_CODIGO_ENTIDAD, []))
    codigo_ids = {id(item) for item in codigo}
    tipo_entidad = [
        item for item in grupos.get(GRUPO_CODIGO_ENTIDAD, [])
        if id(item) not in codigo_ids
    ]
    return tipo_entidad, codigo
