"""Dedup display-only para /procesar: una fila por (factura, grupo_error).

Alcance: SOLO lo que se muestra en /procesar. El Excel exportado, la
evidencia y la auditoría quedan intactos (operan sobre normalized_rows
sin filtrar, antes de este punto).

Reglas de desempate (documentadas por requerimiento):
    1. Menor ``prioridad`` gana (RuleResolver ordena ASC; default 100).
    2. Empate de prioridad -> severidad ``error > warning > info``.
    3. Empate total -> menor regla id.
    4. Empate total e ids iguales/ausentes -> primer match (orden original).
    Nunca se muestran todos en empate: siempre queda exactamente uno.

Supuestos:
    - Clave (factura, tipo_error_final ya remapeado). ``tipo_factura`` no
      forma parte de la clave: si una factura viniera con dos tipos (dato
      inconsistente), igual se muestra una sola fila, la ganadora, bajo su
      propio tipo_factura.
    - Prioridad y severidad se arrastran desde DB (``Regla.prioridad`` /
      ``Regla.severidad``) con UNA batch query parseando ``item.regla``
      ("#id"), mismo patrón lazy best-effort que
      ``_resolve_lazy_regla_templates`` en normalized_rows.py. Si la DB
      falla, se sigue sin romper (meta vacía -> defaults).
    - Items legacy sin regla -> prioridad 100 (default del modelo) y
      severidad del item si la trae, si no "error" (default del modelo).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Default de ``Regla.prioridad`` (app/models.py). Items sin regla caen acá.
DEFAULT_PRIORIDAD = 100

#: Orden de severidad para el 1er desempate. Desconocida -> al fondo.
SEVERIDAD_RANK = {"error": 0, "warning": 1, "info": 2}
_UNKNOWN_SEVERIDAD_RANK = 99

#: Centinela para "sin regla id" en el 2do desempate (ids reales ganan).
_NO_REGLA_ID = 10**9


def _parse_regla_id(regla: object) -> int | None:
    """Parsea '#60' -> 60. None si no es un id numérico."""
    text = str(regla or "").strip().lstrip("#").strip()
    if text.isdigit():
        return int(text)
    return None


def _severidad_rank(severidad: object) -> int:
    """Rankeable de severidad: error < warning < info < desconocida."""
    return SEVERIDAD_RANK.get(str(severidad or "").strip().lower(),
                              _UNKNOWN_SEVERIDAD_RANK)


def _fetch_regla_meta(regla_ids: set[int]) -> dict[int, dict]:
    """Batch query id -> {"prioridad", "severidad"}. Best-effort: {} si falla."""
    if not regla_ids:
        return {}
    try:
        from app.database import get_session  # lazy: evita ciclo de import
        from app.models import Regla

        session = get_session()
        try:
            rows = (
                session.query(Regla.id, Regla.prioridad, Regla.severidad)
                .filter(Regla.id.in_(sorted(regla_ids)))
                .all()
            )
        finally:
            session.close()
    except Exception as exc:
        logger.debug("Dedup /procesar sin meta DB (best-effort): %s", exc)
        return {}
    meta: dict[int, dict] = {}
    for rid, prioridad, severidad in rows:
        meta[rid] = {
            "prioridad": prioridad if prioridad is not None else DEFAULT_PRIORIDAD,
            "severidad": severidad or "error",
        }
    return meta


def _winner_key(item: dict, position: int, meta: dict[int, dict]) -> tuple:
    """Clave de comparación: menor gana (prioridad, severidad, regla id, orden)."""
    rid = _parse_regla_id(item.get("regla"))
    if rid is not None and rid in meta:
        prioridad = meta[rid]["prioridad"]
        severidad = meta[rid]["severidad"]
    else:
        prioridad = DEFAULT_PRIORIDAD
        severidad = item.get("severidad") or "error"
    return (
        prioridad,
        _severidad_rank(severidad),
        rid if rid is not None else _NO_REGLA_ID,
        position,
    )


def _pick_winner(items: list[dict], meta: dict[int, dict]) -> dict:
    """Elige un ganador por (prioridad, severidad, regla id, primer match)."""
    best = items[0]
    best_key = _winner_key(best, 0, meta)
    for position, item in enumerate(items[1:], start=1):
        key = _winner_key(item, position, meta)
        if key < best_key:
            best, best_key = item, key
    return best


def dedup_procesar_items(
    all_items: list[dict],
    regla_meta: dict[int, dict] | None = None,
) -> list[dict]:
    """Dedup display-only: una fila por (factura, tipo_error).

    Args:
        all_items: filas ya normalizadas (tipo_error final remapeado) con
            keys factura, tipo_error, regla ("#id" o ""), tipo_factura, etc.
        regla_meta: override id -> {"prioridad", "severidad"} (tests/hermético).
            None = batch query lazy a DB (best-effort).

    Returns:
        Ganadores en orden estable (primera aparición de cada clave).
        Los dicts se devuelven SIN mutar ni recortar: resto de grupos intacto.
    """
    if not all_items:
        return []
    if regla_meta is None:
        regla_ids = set()
        for item in all_items:
            rid = _parse_regla_id(item.get("regla"))
            if rid is not None:
                regla_ids.add(rid)
        regla_meta = _fetch_regla_meta(regla_ids)

    groups: dict[tuple[str, str], list[dict]] = {}
    order: list[tuple[str, str]] = []
    for item in all_items:
        key = (str(item.get("factura", "")), str(item.get("tipo_error", "")))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(item)

    winners = [_pick_winner(groups[key], regla_meta) for key in order]
    logger.info(
        "Dedup /procesar display: %d items -> %d (clave factura+grupo)",
        len(all_items), len(winners),
    )
    return winners
