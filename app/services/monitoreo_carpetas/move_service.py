"""Bulk move service for Monitoreo de Carpetas.

Validates a bulk move request (free destination, traversal guard,
batch cap, sources under configured roots) and executes per-item
moves with watcher resync.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.constants.monitoreo_carpetas import (
    MOVE_ERR_BATCH_LIMIT,
    MOVE_ERR_COLLISION,
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
    """Validate a bulk move request. Returns error message or None.

    Destination may be any absolute local or UNC path (inside or outside
    the configured roots). Sources must still live under the roots.
    """
    if not sources:
        return "No sources provided."
    if len(sources) > MOVE_MAX_BATCH:
        logger.warning("[BACK] Move rejected: %d items over limit", len(sources))
        return MOVE_ERR_BATCH_LIMIT
    if not dest_dir or not dest_dir.strip():
        return MOVE_ERR_TRAVERSAL
    if ".." in dest_dir.replace("\\", "/").split("/"):
        logger.warning("[BACK] Move rejected: traversal in dest %s", dest_dir)
        return MOVE_ERR_TRAVERSAL
    dest = Path(dest_dir)
    if not dest.is_absolute():
        logger.warning("[BACK] Move rejected: dest not absolute %s", dest_dir)
        return MOVE_ERR_TRAVERSAL
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


def _copy_one(src: str, dest: Path) -> str | None:
    """Copy one invoice dir. Returns error message or None on success."""
    src_path = Path(src)
    if not src_path.exists():
        return MOVE_ERR_SRC_MISSING
    target = dest / src_path.name
    if target.exists():
        return f"{MOVE_ERR_COLLISION} {target}"
    try:
        shutil.copytree(str(src_path), str(target), symlinks=False)
    except OSError as exc:
        logger.error("[BACK][ERROR] Copy failed %s -> %s: %s", src, target, exc)
        return str(exc)
    return None


def execute_move(
    sources: list[str], dest_dir: str, watcher, operation: str = "move"
) -> tuple[list[str], list[dict]]:
    """Execute per-item moves (or copies), resync watcher, return (moved, failed).

    Destination may live outside the watched roots. The watcher only
    resyncs the destination subtree when it falls under the watched
    roots; otherwise the source entries are simply removed (move) or
    nothing is resynced (copy).

    Args:
        operation: "move" (default, preserves legacy callers) or "copy".
            Copy keeps the source in place, so only the destination
            subtree is resynced (no ``remove_subtree``).
    """
    dest = Path(dest_dir)
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("[BACK][ERROR] Move failed: cannot create dest %s: %s", dest, exc)
        return [], [{"src": src, "error": str(exc)} for src in sources]
    try:
        watched_roots: list[str] = watcher.get_roots()
    except AttributeError:
        watched_roots = []
    # Unknown roots (empty) default to resync to preserve legacy behavior;
    # when roots are known, only resync destinations under watch.
    dest_watched = not watched_roots or _is_under_roots(dest, watched_roots)
    is_copy = operation == "copy"
    _transfer_one = _copy_one if is_copy else _move_one
    verb = "Copied" if is_copy else "Moved"
    moved: list[str] = []
    failed: list[dict] = []
    for src in sources:
        error = _transfer_one(src, dest)
        if error is None:
            moved.append(src)
            logger.info("[BACK] %s %s -> %s", verb, src, dest / Path(src).name)
            if not is_copy:
                watcher.remove_subtree(src)
            if dest_watched:
                watcher.update_subtree(str(dest))
        else:
            failed.append({"src": src, "error": error})
    logger.info("[BACK] Bulk %s done: %d ok, %d failed", operation, len(moved), len(failed))
    return moved, failed
