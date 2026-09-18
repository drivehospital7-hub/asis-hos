"""Disk-backed result cache for the /procesar formatted export.

POST /procesar persists the full deduped list as JSON and returns an
opaque ``export_id``; thin GET rebuilds the styled workbook from cache.
Disk (not RAM) so waitress multi-worker deployments share state.
Dedicated ``app/data/temp_exports/`` avoids ``cleanup_temp_excel``
collisions. No background thread: lazy purge on put/get plus sweep.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROCESAR_EXPORT_TTL_SECONDS = 18000
"""Cache lifetime: 5 hours."""

PROCESAR_EXPORT_MAX_ENTRIES = 50
"""Max cached exports kept on disk."""

PROCESAR_EXPORT_MAX_TOTAL_BYTES = 100 * 1024 * 1024
"""Max bytes across all cached exports (mirrors the upload cap)."""

PROCESAR_EXPORT_MAX_ENTRY_BYTES = 20 * 1024 * 1024
"""Max bytes per cached export (GET rejects over-cap with 413)."""

PROCESAR_EXPORT_MAX_ROWS = 20000
"""Max rows per cached export (GET rejects over-cap with 413)."""

_EXPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


def temp_export_directory(*, create: bool = True) -> Path:
    """Directorio ``app/data/temp_exports`` (resuelto)."""
    base = (Path(__file__).resolve().parent.parent / "data" / "temp_exports").resolve()
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def _entry_path(export_id: str) -> Path | None:
    """Safe path for ``export_id`` or None when malformed/traversal."""
    if not _EXPORT_ID_RE.match(export_id or ""):
        return None
    base = temp_export_directory()
    candidate = (base / f"{export_id}.json").resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def _is_expired(payload: dict) -> bool:
    created = payload.get("created", 0)
    return (time.time() - float(created)) > PROCESAR_EXPORT_TTL_SECONDS


def sweep_expired() -> int:
    """Delete expired entries. Returns the removed count."""
    base = temp_export_directory()
    removed = 0
    for path in base.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if _is_expired(payload):
                path.unlink(missing_ok=True)
                removed += 1
        except (OSError, ValueError):
            continue
    if removed:
        logger.info("[BACK] Procesar export sweep: %d expired removed", removed)
    return removed


def _evict_over_caps() -> None:
    """Oldest-first eviction while over entry-count or total-bytes caps."""
    base = temp_export_directory()
    try:
        entries = [(p, p.stat()) for p in base.glob("*.json")]
    except OSError:
        return
    entries.sort(key=lambda item: item[1].st_mtime)
    total = sum(st.st_size for _, st in entries)
    while len(entries) > PROCESAR_EXPORT_MAX_ENTRIES or total > PROCESAR_EXPORT_MAX_TOTAL_BYTES:
        oldest, oldest_stat = entries.pop(0)
        try:
            oldest.unlink(missing_ok=True)
        except OSError:
            continue
        total -= oldest_stat.st_size
        logger.info("[BACK] Procesar export evicted: %s", oldest.name)


def put(rows: list[dict[str, Any]]) -> str:
    """Persist ``rows`` and return an opaque export id."""
    export_id = secrets.token_urlsafe(24)
    payload = {"id": export_id, "created": time.time(), "rows": list(rows)}
    base = temp_export_directory()
    fd, tmp_name = tempfile.mkstemp(dir=base, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp_name, base / f"{export_id}.json")
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    sweep_expired()
    _evict_over_caps()
    logger.info("[BACK] Procesar export cached: %s (%d rows)", export_id, len(rows))
    return export_id


def get(export_id: str) -> list[dict[str, Any]] | None:
    """Return cached rows or None when missing/invalid/expired."""
    path = _entry_path(export_id)
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
        return None
    try:
        if _is_expired(payload):
            path.unlink(missing_ok=True)
            return None
    except OSError:
        return None
    return payload["rows"]
