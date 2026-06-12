"""Servicio Genderize con cache local (sin API)."""
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from app.constants.base import GENDER_DISPLAY_MAP, GENDER_VALID_LONG

# Cache local — configurable via GENDERIZE_CACHE_FILE env var
_CACHE_FILE_DEFAULT = Path(__file__).parent.parent / "data" / "genderize_cache.json"
CACHE_FILE = Path(os.getenv("GENDERIZE_CACHE_FILE") or _CACHE_FILE_DEFAULT)
CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
if not CACHE_FILE.exists():
    CACHE_FILE.write_text("{}")

# Patrones para "Hijo de" / "Hija de"
_RE_HIJO = re.compile(r"^Hijo de\s+", re.IGNORECASE)
_RE_HIJA = re.compile(r"^Hija de\s+", re.IGNORECASE)


def _normalize(name: str) -> str:
    """Normaliza nombre: mayúsculas → minúsculas, quitar tildes."""
    # Quitar tildes
    nfd = unicodedata.normalize("NFD", name)
    sin_tilde = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # A minúsculas
    return sin_tilde.lower().strip()


def _load_cache() -> dict[str, dict]:
    """Carga cache desde JSON, limpiando BOM/zero-width chars de keys."""
    try:
        raw: dict[str, dict] = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        # Limpiar BOM (U+FEFF) y otros caracteres invisibles de keys
        # para que nombres pegados con caracteres ocultos matcheen correctamente
        cleaned: dict[str, dict] = {}
        for k, v in raw.items():
            clean_key = k.replace("\ufeff", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").strip()
            # Mapear null → "undefined" en memoria
            # La cache física NO se reescribe a menos que se haga un override explícito
            if v.get("gender") is None:
                v["gender"] = "undefined"
            cleaned[clean_key] = v
        return cleaned
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    """Guarda cache a JSON."""
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_gender(value: str) -> str:
    """Normaliza un valor de género a su forma larga canónica.

    Acepta short codes (F/M/L/U) y long forms (female/male/lastname/undefined).
    """
    upper = value.strip().upper()
    if upper in GENDER_DISPLAY_MAP:
        return GENDER_DISPLAY_MAP[upper]
    lower = value.strip().lower()
    if lower in GENDER_VALID_LONG:
        return lower
    raise ValueError(f"genero invalido: '{value}'. Debe ser F/M/L/U o female/male/lastname/undefined")


def override_gender(normalized_name: str, new_gender: str) -> bool:
    """Sobrescribe el género de un nombre en el cache.

    Args:
        normalized_name: Nombre normalizado (key del cache).
        new_gender: Nuevo género: short code (F/M/L/U) o long form (female/male/lastname/undefined).

    Returns:
        True si se actualizó, False si no existía en cache.

    Raises:
        ValueError: Si new_gender no es un valor válido.
    """
    gender = _normalize_gender(new_gender)

    cache = _load_cache()
    if normalized_name not in cache:
        logger.warning("Nombre no encontrado en cache: %s", normalized_name)
        return False

    cache[normalized_name]["gender"] = gender
    _save_cache(cache)
    logger.info("Override cache: %s → %s", normalized_name, gender)
    return True


def _classify(name: str) -> tuple[str, str | None]:
    """Clasifica nombre y determina género forzado."""
    if _RE_HIJO.match(name):
        return name, "male"
    elif _RE_HIJA.match(name):
        return name, "female"
    return name, None


@dataclass
class GenderResult:
    name: str
    gender: str | None
    probability: float | None
    count: int | None


def predict_genders(names: list[str]) -> list[GenderResult]:
    """Predict gender usando solo cache local (sin API).

    Cache hit → retorna GenderResult con datos cacheados.
    Cache miss → skip silencioso (no asigna U, no muta cache).
    "Hijo de"/"Hija de" → clasificado localmente via _classify().
    """
    if not names:
        return []

    cache = _load_cache()
    results: list[GenderResult] = []

    for original in names:
        original, forced = _classify(original)
        normalized = _normalize(original)

        # Cache hit → devolver valor cacheado
        if normalized in cache:
            logger.info("Cache hit: %s", normalized)
            cached = cache[normalized]
            results.append(GenderResult(
                name=original,
                gender=forced or cached["gender"],
                probability=cached["probability"],
                count=cached["count"],
            ))
        elif forced:
            # Hijo de/Hija de sin cache → clasificar localmente
            results.append(GenderResult(
                name=original,
                gender=forced,
                probability=None,
                count=None,
            ))
        # Cache miss → skip (no API call, no auto-U)

    # Ordenar resultados igual al input
    results_dict = {r.name: r for r in results}
    ordered = [results_dict[n] for n in names if n in results_dict]

    return ordered