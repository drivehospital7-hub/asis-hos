"""Servicio Genderize con cache local."""
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request

logger = logging.getLogger(__name__)
GENDERIZE_API_URL = "https://api.genderize.io"
GENDERIZE_API_KEY = os.getenv("GENDERIZE_API_KEY")

# Cache local
CACHE_FILE = Path(__file__).parent.parent / "data" / "genderize_cache.json"
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
    """Carga cache desde JSON."""
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    """Guarda cache a JSON."""
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


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


@dataclass
class RateLimitInfo:
    limit: int
    remaining: int
    reset: int


def predict_genders(names: list[str]) -> tuple[list[GenderResult], RateLimitInfo | None]:
    """Predict gender con cache local."""
    if not names:
        return [], None

    cache = _load_cache()
    results: list[GenderResult] = []
    api_names: list[tuple[str, str, str | None]] = []  # (original, normalized, forced_gender)

    for original in names:
        original, forced = _classify(original)
        normalized = _normalize(original)
        
        # Lookup en cache
        if normalized in cache:
            logger.info("Cache hit: %s", normalized)
            cached = cache[normalized]
            results.append(GenderResult(
                name=original,
                gender=forced or cached["gender"],
                probability=cached["probability"],
                count=cached["count"],
            ))
        else:
            api_names.append((original, normalized, forced))

    # Si hay nombres sin cache, consultar API
    if api_names:
        originals = [n[0] for n in api_names]
        normals = [n[1] for n in api_names]
        forceds = [n[2] for n in api_names]
        
        params = [(f"name[{i}]", n) for i, n in enumerate(originals)]
        if GENDERIZE_API_KEY:
            params.append(("apikey", GENDERIZE_API_KEY))
        query = urlencode(params)
        url = f"{GENDERIZE_API_URL}?{query}"
        
        logger.info("API call para %d nombres", len(api_names))
        
        try:
            request = Request(url)
            with urlopen(request, timeout=30) as response:
                data: list[dict[str, Any]] = json.load(response)
                api_results = {item["name"]: item for item in data}
                rate_limit = RateLimitInfo(
                    limit=int(response.headers.get("X-Rate-Limit-Limit", 0)),
                    remaining=int(response.headers.get("X-Rate-Limit-Remaining", 0)),
                    reset=int(response.headers.get("X-Rate-Limit-Reset", 0)),
                )
        except HTTPError as e:
            logger.exception("Error HTTP genderize: %s", e.code)
            raise

        # Guardar en cache y agregar resultados
        for original, normalized, forced in api_names:
            api_item = api_results.get(original, {})
            gender = forced or api_item.get("gender")
            
            # Guardar en cache (key = normalized)
            cache[normalized] = {
                "gender": gender,
                "probability": api_item.get("probability"),
                "count": api_item.get("count"),
            }
            
            results.append(GenderResult(
                name=original,
                gender=gender,
                probability=api_item.get("probability"),
                count=api_item.get("count"),
            ))
        
        _save_cache(cache)

    # Ordenar resultados igual al input
    results_dict = {r.name: r for r in results}
    ordered = [results_dict[n] for n in names if n in results_dict]

    return ordered, rate_limit if api_names else None