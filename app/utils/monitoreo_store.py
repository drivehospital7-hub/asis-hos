"""Persistencia JSON para rutas raíz de Monitoreo de Carpetas.

Priority: JSON file > env var > empty list.
Env var supports JSON array or semicolon-separated fallback.
Atomic writes via tempfile.mkstemp + Path.replace().
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.constants.monitoreo_carpetas import ENV_MONITOREO_ROOTS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_FILE = DATA_DIR / "monitoreo_carpetas_config.json"


def _read_config() -> dict[str, Any] | None:
    """Read config JSON file. Returns None if file doesn't exist or is corrupt."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Error leyendo archivo de configuración de monitoreo: %s", CONFIG_FILE)
        return None


def _parse_env_var(raw: str) -> list[str]:
    """Parse MONITOREO_CARPETAS_ROOTS env var value.

    Supports JSON array first, then semicolon-separated fallback.
    """
    raw = raw.strip()
    if not raw:
        return []

    if raw.startswith("["):
        try:
            roots: list[str] = json.loads(raw)
            if isinstance(roots, list):
                return [r for r in roots if isinstance(r, str) and r.strip()]
        except json.JSONDecodeError:
            pass

    return [p.strip() for p in raw.split(";") if p.strip()]


def get_roots() -> tuple[list[str], str, str | None]:
    """Read root directories with priority: JSON file > env var > [].

    Returns:
        (roots, fuente, ultima_actualizacion)
        fuente is "manual" if from JSON file, "env" if from env var or empty.
    """
    # Priority 1: JSON file
    config = _read_config()
    if config is not None:
        roots: list[str] = config.get("roots", [])
        if roots:
            return roots, "manual", config.get("ultima_actualizacion")

    # Priority 2: Environment variable
    env_raw = os.environ.get(ENV_MONITOREO_ROOTS, "").strip()
    if env_raw:
        roots = _parse_env_var(env_raw)
        return roots, "env", None

    # Priority 3: Empty
    return [], "env", None


def save_roots(roots: list[str]) -> None:
    """Save root directories to JSON file with atomic write.

    Args:
        roots: Non-empty list of strings.

    Raises:
        ValueError: If roots is empty or contains non-strings.
    """
    if not roots:
        raise ValueError("roots debe ser una lista no vacía de strings")
    if not all(isinstance(r, str) for r in roots):
        raise ValueError("Todos los elementos de roots deben ser strings")

    data = {
        "roots": roots,
        "fuente": "manual",
        "ultima_actualizacion": datetime.now().isoformat(),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Put temp file in same directory as config file for atomic cross-drive safety
    tmp_dir = CONFIG_FILE.parent
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=tmp_dir, suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        Path(tmp_path).replace(CONFIG_FILE)
        logger.info("Rutas de monitoreo guardadas: %s", roots)
    except Exception:
        # Cleanup temp file on failure
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise



