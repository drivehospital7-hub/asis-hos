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


@dataclass
class RuleBatch:
    """Detections of one resolved rule: nombre, grupo, items."""

    nombre: str
    grupo: str
    dominio: str
    items: list[dict[str, Any]] = field(default_factory=list)


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

    batches: list[RuleBatch] = []
    seen: set[str] = set()
    for rule in RuleResolver().resolve(domain, session):
        if rule.nombre in seen:
            continue
        seen.add(rule.nombre)
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
