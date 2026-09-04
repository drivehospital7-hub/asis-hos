"""Constants for PDF Search module.

Supports multi-root bases for UNC shares (e.g. \\192.168.0.124\\facturacion).

Resolution order for PDF base paths:
1. PDF_BASE_PATHS env var (JSON array or semicolon-separated) — preferred.
2. PDF_BASE_PATH legacy env var (single path, also supports ; / JSON for compat).
3. Default: [] (open mode — any absolute path allowed).

When PDF_BASE_PATHS is empty (open mode), any absolute path that passes
traversal and isdir checks is allowed. Set PDF_BASE_PATHS explicitly to
restrict browsing (e.g. ["C:\\"] or ["\\\\192.168.0.124\\share"]).

PDF_BASE_PATH is kept as alias to the first entry for backward compatibility;
it is "" when no base is configured (open mode).
"""

from __future__ import annotations

import json
import os

CONDICIONES = [
    "Conductor", "Ciclista", "Peatón", "Ocupante"
]

TRANSPORTES = [
    "Automóvil", "Bus", "Buseta", "Camión", "Camioneta",
    "Campero", "Microbus", "Tractocamion", "Motocicleta",
    "Motocarro", "Mototriciclo", "Cuatrimoto",
    "Moto extranjera", "Vehiculo extranjero", "Volqueta",
]

SINONIMOS_DEFAULT = {
    "Ocupante": ["Acompañante", "Pasajero"]
}

# Env var names
ENV_PDF_BASE_PATHS = "PDF_BASE_PATHS"
ENV_PDF_BASE_PATH = "PDF_BASE_PATH"  # legacy single-path
DEFAULT_PDF_BASE = "C:\\"


def _parse_pdf_bases(raw: str) -> list[str]:
    """Parse env var value as JSON array or semicolon-separated list.

    Mirrors app.utils.monitoreo_store._parse_env_var.
    """
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [r for r in parsed if isinstance(r, str) and r.strip()]
        except json.JSONDecodeError:
            pass
    return [p.strip() for p in raw.split(";") if p.strip()]


def _get_pdf_bases() -> list[str]:
    """Resolve PDF base paths with priority: PDF_BASE_PATHS > PDF_BASE_PATH > open mode.

    Returns empty list when no env var is set, meaning open mode (any absolute
    path allowed). Only when an env var is explicitly configured are bases
    restricted.
    """
    env_multi = os.getenv(ENV_PDF_BASE_PATHS, "").strip()
    if env_multi:
        bases = _parse_pdf_bases(env_multi)
        if bases:
            return bases

    env_single = os.getenv(ENV_PDF_BASE_PATH, "").strip()
    if env_single:
        # Legacy var may also contain ; or JSON if user migrated without renaming
        if env_single.startswith("[") or ";" in env_single:
            bases = _parse_pdf_bases(env_single)
            if bases:
                return bases
        return [env_single]

    return []


PDF_BASE_PATHS: list[str] = _get_pdf_bases()

# Backward-compatible alias: first base, or "" in open mode
PDF_BASE_PATH: str = PDF_BASE_PATHS[0] if PDF_BASE_PATHS else ""
