"""Persistencia de sinónimos custom en archivo JSON."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta al archivo de sinónimos persistidos
_SYNONYMS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "sinonimos.json"


def cargar_sinonimos() -> dict[str, list[str]]:
    """Carga los sinónimos persistidos desde el archivo JSON.

    Returns:
        Dict con términos y sus listas de sinónimos.
        Vacío si el archivo no existe o está corrupto.
    """
    if not _SYNONYMS_FILE.exists():
        return {}

    try:
        data = json.loads(_SYNONYMS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("sinonimos.json no es un dict, reiniciando")
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Error al leer sinonimos.json: %s", e)
        return {}


def guardar_sinonimos(sinonimos: dict[str, list[str]]) -> None:
    """Guarda los sinónimos en el archivo JSON.

    Args:
        sinonimos: Dict con términos y sus listas de sinónimos.
    """
    try:
        _SYNONYMS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SYNONYMS_FILE.write_text(
            json.dumps(sinonimos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Sinónimos guardados (%d términos)", len(sinonimos))
    except OSError as e:
        logger.exception("Error al guardar sinonimos.json: %s", e)
        raise
