# Design: Import Facturas — Cache-Only Gender System

## Technical Approach

Selective file extraction from `feature/procesamiento-unificado` adapted to `main`, in dependency order: constants → `genderize_service` → `genderize_verifier` → `genderize_extractor` → routes → `__init__.py` → frontend → tests → delete `genderize_api.py`.

The core strategy: **remove the external API dependency entirely**, expand gender to 4 values (F/M/L/U), and handle the 3 data-identification columns the extractor already encounters in the Excel.

## Architecture Decisions

### Decision: GENDER_* constants placement

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New file `app/constants/gender.py` | + Clean isolation, − Extra import in `constants/__init__.py`, breaks existing `from app.constants.base import *` pattern | **Rejected** — adds module overhead, the feature branch places them in `base.py` |
| New section in `base.py` after `ENTIDADES` | + Follows existing pattern (section per domain), + No import changes via wildcard re-export, − No conflict with `DASHBOARD_AREAS` on main | **Accepted** |

**Rationale**: On main, `DASHBOARD_AREAS` ends at line 225. The `GENDER_*` section goes between `ENTIDADES` (line 38) and `AREAS` (line 42), using the same section-comment pattern. No collision with feature branch's different layout.

### Decision: Cache-only genderize_service.py

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep HTTP imports + add `_normalize_gender` | − Still requires API key env vars, − Retry/429 logic remains dead code | **Rejected** — violates "remove API dependency" intent |
| Pure local: no `urllib`, no `HTTPError`, no `GENDERIZE_API_KEY` | + Zero network calls, + No env vars needed, + `_load_cache` handles BOM/zero-width + null→undefined, + Predict returns `list[GenderResult]` (no `RateLimitInfo`) | **Accepted** |

**Rationale**: `predict_genders()` signature changes from `→ tuple[list[GenderResult], RateLimitInfo | None]` to `→ list[GenderResult]`. Callers (`genderize_verifier`, deleted `genderize_api.py`) must adapt. Cache miss → skip silently (no auto-U). "Hijo de"/"Hija de" classified via `_classify()` with no cache needed.

### Decision: get_stats returns 3-tuple + 4-value verifier

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep 2-tuple, add new endpoint | + Backward compat, − Frontend needs second API call | **Rejected** — more complexity |
| 3-tuple `(Stats, facturas, nombres_no_cache)` | + Frontend gets all data in one call, − Old callers must update | **Accepted** |

**Rationale**: On main, `get_stats` is called only by `get_facturas_stats()`. All callers update together. The 3rd element (`list[dict]{"nombre", "sexo"}`) enables the export-no-cache button. `verificar_y_comparar()` maps 4 values without API: male→M, female→F, lastname→L, undefined→U, other→?.

### Decision: Blueprint deletion

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep `genderize_api.py` with disabled routes | + Minimal diff, − Dead code | **Rejected** |
| Full deletion + `__init__.py` cleanup | + No dead code, − Need to ensure `genderize_bp` appears only once | **Accepted** |

**Rationale**: On main, `__init__.py` line 108 imports `genderize_bp` and line 127 registers it. Delete both lines. `genderize_bp` has zero consumers outside `__init__.py`. If missed, pytest catches `ImportError`.

## Data Flow

```
Upload Excel (.xlsx)
       │
       ▼
extract_factura_nombre_sexo() ──→ list[ExtractResult] (now includes 3 new cols)
       │
       ▼
verificar_y_comparar()
       │
       ├── _load_cache()  ← cleans BOM/zero-width, null→"undefined"
       │
       ├── Cache hit → compare sexo_excel vs cached gender (4-value mapping)
       │
       └── Cache miss → skip (no API call), show nombres_no_cache in frontend
       │
       ▼
Frontend: dropdown F/M/L/U, "Sexo JSON" label, 3 new columns, export no-cache
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/base.py` | Modify | Add `GENDER_*` section (GENDER_DISPLAY_MAP, GENDER_CACHE_MAP, GENDER_VALID_SHORT/LONG, 4 values) |
| `app/services/genderize_service.py` | Rewrite | No HTTP imports, no API, `_load_cache` BOM/null cleaning, `_normalize_gender()`, `predict_genders()` returns list only |
| `app/services/genderize_verifier.py` | Modify | `get_stats` returns 3-tuple, `verificar_y_comparar` 4-value mapping + 3 new fields in `Discrepancia` |
| `app/services/genderize_extractor.py` | Modify | 3 new columns (Nº Identificación, Entidad Cobrar, Tipo Identificación) + `ExtractResult` fields |
| `app/routes/import_facturas.py` | Modify | Remove `HTTPError` import/handler, accept F/M/L/U, add `nombres_no_cache` to stats, 3 new fields in discrepancies |
| `app/routes/genderize_api.py` | Delete | Entire file |
| `app/__init__.py` | Modify | Remove `genderize_bp` import (line 108) + registration (line 127) |
| `frontend/src/pages/genderize/page.tsx` | Modify | Dropdown F/M/L/U, "Sexo JSON" label, 3 new cols, export no-cache button |
| `tests/services/test_genderize_service.py` | New | 18 tests |
| `tests/services/test_genderize_verifier.py` | New | 14 tests |
| `test_genderize.py` (root) | Delete | Manual test script |

## Interfaces / Contracts

```python
# genderize_service.py (new signature)
def predict_genders(names: list[str]) -> list[GenderResult]: ...
# Returns list only — no tuple, no RateLimitInfo, no API calls

# genderize_verifier.py (new signature)
def get_stats(excel_path: str) -> tuple[Stats, dict[str, ExtractResult], list[dict]]:
    # 3rd element: [{"nombre": str, "sexo": str}, ...]

# genderize_extractor.py (new fields)
@dataclass
class ExtractResult:
    numero_identificacion: str = ""
    entidad_cobrar: str = ""
    tipo_identificacion: str = ""
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `_load_cache` null→"undefined" | 6 tests: null, valid, mixed, empty, lastname, undefined preserved |
| Unit | `predict_genders` cache-only | 6 tests: cache hit, miss, Hijo de, Hija de, mixed, no auto-U |
| Unit | `override_gender` 4-value | 10 tests: F/M/L/U short + long, invalid raises, nonexistent false |
| Unit | `get_stats` 3-tuple | 8 tests: partial miss, all cached, none cached, Hijo de excluded, sexo preserved, dedup |
| Unit | `verificar_y_comparar` 4-value | 6 tests: U/L/M/F mapping, no discrepancy, sexo_excel preserved, non-cached skip |

## Migration / Rollout

No migration required. Existing `genderize_cache.json` files with `null` genders are mapped to `"undefined"` in memory by `_load_cache()` — no physical rewrite until explicit override. Deploy backend + frontend together to keep API contract in sync.

## Open Questions

None. All decisions are resolved by the feature branch precedent.
