"""Bulk move service for Monitoreo de Carpetas.

Validates a bulk move request (dest under configured roots, traversal
guard, batch cap) and executes per-item moves with watcher resync.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.constants.monitoreo_carpetas import (
    MOVE_ERR_BATCH_LIMIT,
    MOVE_ERR_COLLISION,
    MOVE_ERR_DEST_OUTSIDE_ROOTS,
    MOVE_ERR_SRC_MISSING,
    MOVE_ERR_SRC_OUTSIDE_ROOTS,
    MOVE_ERR_TRAVERSAL,
    MOVE_MAX_BATCH,
)

logger = logging.getLogger(__name__)


def _is_under_roots(path: Path, roots: list[str]) -> bool:
    """Check whether resolved path lives under one of the roots."""
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def validate_move_request(
    sources: list[str], dest_dir: str, roots: list[str]
) -> str | None:
    """Validate a bulk move request. Returns error message or None."""
    if not sources:
        return "No sources provided."
    if len(sources) > MOVE_MAX_BATCH:
        logger.warning("[BACK] Move rejected: %d items over limit", len(sources))
        return MOVE_ERR_BATCH_LIMIT
    if ".." in dest_dir.replace("\\", "/").split("/"):
        logger.warning("[BACK] Move rejected: traversal in dest %s", dest_dir)
        return MOVE_ERR_TRAVERSAL
    dest = Path(dest_dir)
    if not _is_under_roots(dest, roots):
        logger.warning("[BACK] Move rejected: dest outside roots %s", dest_dir)
        return MOVE_ERR_DEST_OUTSIDE_ROOTS
    for src in sources:
        if ".." in src.replace("\\", "/").split("/"):
            logger.warning("[BACK] Move rejected: traversal in src %s", src)
            return MOVE_ERR_SRC_OUTSIDE_ROOTS
        if not _is_under_roots(Path(src), roots):
            logger.warning("[BACK] Move rejected: src outside roots %s", src)
            return MOVE_ERR_SRC_OUTSIDE_ROOTS
    return None


def _move_one(src: str, dest: Path) -> str | None:
    """Move one invoice dir. Returns error message or None on success."""
    src_path = Path(src)
    if not src_path.exists():
        return MOVE_ERR_SRC_MISSING
    target = dest / src_path.name
    if target.exists():
        return f"{MOVE_ERR_COLLISION} {target}"
    try:
        shutil.move(str(src_path), str(target))
    except OSError as exc:
        logger.error("[BACK][ERROR] Move failed %s -> %s: %s", src, target, exc)
        return str(exc)
    return None


def execute_move(
    sources: list[str], dest_dir: str, watcher
) -> tuple[list[str], list[dict]]:
    """Execute per-item moves, resync watcher, return (moved, failed)."""
    dest = Path(dest_dir)
    moved: list[str] = []
    failed: list[dict] = []
    for src in sources:
        error = _move_one(src, dest)
        if error is None:
            moved.append(src)
            logger.info("[BACK] Moved %s -> %s", src, dest / Path(src).name)
            watcher.remove_subtree(src)
            watcher.update_subtree(str(dest))
        else:
            failed.append({"src": src, "error": error})
    logger.info("[BACK] Bulk move done: %d moved, %d failed", len(moved), len(failed))
    return moved, failed
