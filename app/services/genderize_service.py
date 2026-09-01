"""Servicio Genderize con cache local (sin API)."""
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

from app.constants.base import GENDER_CACHE_MAP, GENDER_DISPLAY_MAP, GENDER_VALID_LONG

# Cache local — configurable via GENDERIZE_CACHE_FILE env var
# NOTA: NO crear archivo vacío al importar — si no existe, _load_cache devuelve {}.
# El archivo se crea SOLO cuando se guarda algo explícitamente (_save_cache).
_CACHE_FILE_DEFAULT = Path("D:/CODE/genderize_cache.json")
CACHE_FILE = Path(os.getenv("GENDERIZE_CACHE_FILE") or _CACHE_FILE_DEFAULT)

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
        raw: dict[str, dict] = json.loads(CACHE_FILE.read_text(encoding="utf-8-sig"))
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
    """Guarda cache a JSON. Crea el directorio si no existe."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
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


def _resolve_gender_filter(gender: str | None) -> str | None:
    """Valida y resuelve filtro de género."""
    if not gender or gender.strip().lower() == "all":
        return None
    raw = gender.strip()
    upper = raw.upper()
    if upper in GENDER_DISPLAY_MAP:
        return GENDER_DISPLAY_MAP[upper]
    lower = raw.lower()
    if lower in GENDER_VALID_LONG:
        return lower
    raise ValueError(
        f"genero invalido: '{gender}'. Debe ser All/F/M/L/U o female/male/lastname/undefined"
    )


def _filtered_sorted(cache: dict, q: str | None, gender_filter: str | None) -> list[tuple[str, dict]]:
    """Filtra por search y género, ordena por _normalize."""
    out: list[tuple[str, dict]] = []
    for key, val in cache.items():
        if q and q not in _normalize(key):
            continue
        if gender_filter and val.get("gender") != gender_filter:
            continue
        out.append((key, val))
    out.sort(key=lambda kv: _normalize(kv[0]))
    return out


def _by_gender_counts(filtered: list[tuple[str, dict]]) -> dict[str, int]:
    """Cuenta por short code."""
    counts: dict[str, int] = {}
    for _, val in filtered:
        short = GENDER_CACHE_MAP.get(val.get("gender", ""), val.get("gender", ""))
        counts[short] = counts.get(short, 0) + 1
    return counts


def _clean_key(key: str) -> str:
    """Limpia BOM/ZW y trim."""
    return key.replace("\ufeff", "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "").strip()


def _load_raw_cache() -> list[tuple[str, dict]] | None:
    """Lee raw JSON preservando duplicados literales (object_pairs_hook).

    Usa hook inteligente: inner gender objects → dict, outer cache → list
    para no perder keys duplicadas idénticas (ej: dos \"angela\" con distinto gender).
    None si falta/corrupto.
    """
    def _hook(pairs: list[tuple[str, object]]) -> object:
        # Inner gender entry contiene key "gender" → dict
        if any(k == "gender" for k, _ in pairs):
            return dict(pairs)
        # Outer cache (keys son nombres, valores son dicts) → list para preservar duplicados
        return pairs

    try:
        text = CACHE_FILE.read_text(encoding="utf-8-sig")
        pairs: list[tuple[str, dict]] = json.loads(text, object_pairs_hook=_hook)  # type: ignore[assignment]
        # json.loads con hook puede devolver [] para {} o list para cache
        if isinstance(pairs, dict):
            # Fallback: si por alguna razón devuelve dict (ej: cache vacía no list), convertir
            return list(pairs.items())  # type: ignore[return-value]
        return pairs  # type: ignore[return-value]
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    except Exception:
        logger.exception("[BACK][ERROR] Error leyendo cache para alerts")
        return None


def _collect_alerts(raw_pairs: list[tuple[str, dict]]) -> tuple[list[str], list[dict], int, dict[str, list[str]], dict[str, list]]:
    """Analiza raw_pairs: cleaned, invalid, nulls, grupos normalizados.

    raw_pairs preserva duplicados literales (mismo \"angela\" dos veces).
    Retorna también group_genders para no perder el segundo valor de keys duplicadas.
    """
    cleaned_keys: list[str] = []
    invalid_genders: list[dict] = []
    recovered_nulls = 0
    group_norm: dict[str, list[str]] = {}
    group_genders: dict[str, list] = {}
    for raw_key, val in raw_pairs:
        g = val.get("gender") if isinstance(val, dict) else None
        if g is None:
            recovered_nulls += 1
        elif g not in GENDER_VALID_LONG:
            invalid_genders.append({"key": raw_key, "gender": g})
        clean = _clean_key(raw_key)
        if clean != raw_key:
            cleaned_keys.append(raw_key)
        norm = _normalize(clean)
        group_norm.setdefault(norm, []).append(raw_key)
        group_genders.setdefault(norm, []).append(g)
    return cleaned_keys, invalid_genders, recovered_nulls, group_norm, group_genders


def list_cache(
    search: str | None = None,
    gender: str | None = "All",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Lista cache con filtro NFD, género, sort y paginación."""
    cache = _load_cache()
    q = _normalize(search) if search and search.strip() else None
    gender_filter = _resolve_gender_filter(gender)
    filtered = _filtered_sorted(cache, q, gender_filter)
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 50)))
    by_gender = _by_gender_counts(filtered)
    total = len(filtered)
    start = (page - 1) * page_size
    slice_items = filtered[start : start + page_size]
    items = []
    for key, val in slice_items:
        g_long = val.get("gender")
        items.append(
            {
                "nombre_normalizado": key,
                "gender": g_long,
                "gender_short": GENDER_CACHE_MAP.get(g_long, ""),
                "probability": val.get("probability"),
                "count": val.get("count"),
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "by_gender": by_gender}


def get_cache_alerts() -> dict:
    """Escanea raw JSON antes de limpiar: BOM/ZW, colisiones, invalid, nulls."""
    raw_pairs = _load_raw_cache()
    if raw_pairs is None:
        return {
            "collisions": [],
            "cleaned_keys": [],
            "invalid_genders": [],
            "recovered_nulls": 0,
            "total_collisions": 0,
        }
    cleaned_keys, invalid_genders, recovered_nulls, group_norm, group_genders = _collect_alerts(raw_pairs)
    collisions: list[dict] = []
    for norm_key, raws in group_norm.items():
        if len(raws) > 1:
            genders = group_genders.get(norm_key, [])
            collisions.append(
                {
                    "normalized_key": norm_key,
                    "raw_keys": raws,
                    "genders": genders,
                    "same_value": len(set(str(g) for g in genders)) == 1,
                }
            )
    return {
        "collisions": collisions,
        "cleaned_keys": cleaned_keys,
        "invalid_genders": invalid_genders,
        "recovered_nulls": recovered_nulls,
        "total_collisions": len(collisions),
    }
