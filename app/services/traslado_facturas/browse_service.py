"""Explorador de destino en servidor (Traslado de Facturas).

Lista subdirectorios directos bajo las raíces configuradas. Reusa
``_is_under_roots`` de move_service (NO duplicar la verificación).
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.constants.monitoreo_carpetas import MOVE_ERR_TRAVERSAL
from app.services.monitoreo_carpetas.move_service import _is_under_roots

logger = logging.getLogger(__name__)


def list_dirs(path: str | None, roots: list[str]) -> tuple[dict | None, str | None]:
    """Lista subdirectorios directos de ``path`` acotado a ``roots``.

    Args:
        path: Ruta absoluta a explorar. None/vacío = lista las raíces
            como entries.
        roots: Raíces configuradas permitidas.

    Returns:
        ``(data, None)`` con
        ``data = {"actual": str|None, "padre": str|None,
        "dirs": [{"name", "path"}]}``;
        o ``(None, error)`` cuando el path es relativo, contiene ``..``,
        cae fuera de roots, no existe o no es legible (OSError).
    """
    if not roots:
        return None, "No configured roots to browse."
    if not path:
        return {
            "actual": None,
            "padre": None,
            "dirs": [{"name": root, "path": root} for root in roots],
        }, None
    if ".." in path.replace("\\", "/").split("/"):
        logger.warning("[BACK] Browse rejected: traversal in %s", path)
        return None, MOVE_ERR_TRAVERSAL
    candidate = Path(path)
    if not candidate.is_absolute():
        logger.warning("[BACK] Browse rejected: not absolute %s", path)
        return None, MOVE_ERR_TRAVERSAL
    if not _is_under_roots(candidate, roots):
        logger.warning("[BACK] Browse rejected: outside roots %s", path)
        return None, MOVE_ERR_TRAVERSAL
    try:
        resolved = candidate.resolve()
    except OSError as exc:
        logger.warning("[BACK] Browse cannot resolve %s: %s", path, exc)
        return None, str(exc)
    if not resolved.is_dir():
        return None, f"Path does not exist: {path}"
    try:
        entries = sorted(
            (entry for entry in resolved.iterdir() if entry.is_dir()),
            key=lambda entry: entry.name.lower(),
        )
    except OSError as exc:
        logger.warning("[BACK] Browse cannot list %s: %s", path, exc)
        return None, str(exc)
    parent = resolved.parent
    padre = str(parent) if _is_under_roots(parent, roots) else None
    return {
        "actual": str(resolved),
        "padre": padre,
        "dirs": [{"name": entry.name, "path": str(entry)} for entry in entries],
    }, None
