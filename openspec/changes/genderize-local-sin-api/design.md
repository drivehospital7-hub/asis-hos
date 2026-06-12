# Design: Genderize local sin API + export con genero

## Technical Approach

Dos cambios orquestados: (1) `predict_genders()` se simplifica a cache-local puro — cache hit devuelve, cache miss saltea. (2) `get_stats()` incluye `sexo_excel` (M/F) por cada `nombre_no_cache`, y el frontend exporta `nombre\tsexo`. Ruta `/api/genderize/` se elimina.

## Architecture Decisions

### Decision: predict_genders returns only cache hits

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Cache hit devuelve, miss no devuelve nada | Nombres sin cache no aparecen en `all_results` del verifier → no generan discrepancia. Comportamiento exacto por spec | ✅ |
| Devolver `GenderResult(gender=None)` | Caller debe ignorar nulos manualmente; `SexoAPI` se vuelve `?` | ❌ |

### Decision: Keep `api_calls_necesarias` field, set to 0

**Rationale**: Frontend still reads it; setting to 0 is backwards-compatible. Full removal is a separate frontend change.

### Decision: Delete `test_genderize.py` at project root

**Rationale**: 3-line manual script importing `predict_genders`. Not an automated test. No value after API removal.

## Data Flow

### Verify (verificar_y_comparar)

    ExtractResult[] ──→ facturas → unique_names → classify(hijo/hija)
         │                                                    │
    cache[normalized] ←─── _load_cache()                skip (forced)
         │
    cache_hits → all_results (via predict_genders cache-only)
         │
    nuevos (uncached) → predict_genders → empty for misses
         │
    compare sexo_excel vs sexo_api → discrepancies

Previously `predict_genders` called API in batches of 10. Now: cache miss = no result in predict_genders output = no comparison = no discrepancy.

### Export (get_stats)

    for each factura:
      if not cached AND not hijo/hija:
        nombres_no_cache.append({nombre, sexo: r.sexo})  # sexo from ExtractResult

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `genderize_service.py` | Modify | Remove urllib imports, API constants, `RateLimitInfo`; `predict_genders()` cache-only |
| `genderize_verifier.py` | Modify | `get_stats()` → `list[dict]` con nombre+sexo; `verificar_y_comparar()` sin batching |
| `routes/import_facturas.py` | Modify | Remove `HTTPError` import, `except HTTPError` block |
| `routes/genderize_api.py` | Delete | Entire test route file |
| `app/__init__.py` | Modify | Remove import + registration of `genderize_bp` |
| `frontend/…/genderize/page.tsx` | Modify | `StatsData.nombres_no_cache` → `{nombre,sexo}[]`; export `nombre\tsexo`; remove token label |
| `test_genderize.py` | Delete | Manual script, no automated value |
| `tests/services/test_genderize_service.py` | Modify | Drop 3 `urlopen` mock tests; add cache-hit/miss-skip tests |
| `tests/services/test_genderize_verifier.py` | Modify | Update assertions for `list[dict]` and zero api_calls |

## Interfaces / Contracts

### `get_stats()` 3rd return element

```python
# Before:  nombres_no_cache: list[str]
# After:   nombres_no_cache: list[dict]  # [{"nombre": "juan", "sexo": "M"}, ...]
```

### Stats API response (`/api/import/facturas-stats`)

```json
{
  "status": "success",
  "data": {
    "total_excel": 100,
    "nombres_unicos": 30,
    "cache_hits": 20,
    "api_calls_necesarias": 0,
    "nombres_no_cache": [{"nombre": "juan perez", "sexo": "M"}]
  },
  "errors": []
}
```

### Frontend export format

```
\uFEFFjuan perez\tM, maria lopez\tF
```

### Removed: `RateLimitInfo`, `/api/genderize/` endpoint

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | predict_genders cache hit | Mock cache entry → assert `GenderResult`, no network |
| Unit | predict_genders cache miss | Mock empty cache → assert empty results |
| Unit | predict_genders Hijo/Hija de | Assert classified via `_classify()` locally |
| Unit | get_stats format | Mock extractor+cache → assert `list[dict]` with nombre+sexo |
| Unit | verificar_y_comparar no API | Assert predict_genders returns empty → no discrepancies |
| Integration | Stats endpoint shape | POST Excel → assert JSON matches new format |
| Integration | No HTTPError in verify | POST Excel → assert no 502/429 errors |

## Migration / Rollout

No migration required. Cache file format unchanged. No feature flags.

## Open Questions

None.
