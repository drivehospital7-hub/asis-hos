# Design: reglas-por-tipo-factura

## Technical Approach

2-PR incremental strategy: PR 1 adds internal `tipo_factura_descripcion` filters (no structural changes); PR 2 reorganizes packages, creates per-tipo orchestrators, and introduces a central registry for dispatch by business type instead of HTTP route.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Registry location | `app/services/tipo_factura_registry.py` | Inside `transversales/` | At `services/` root, it dispatches ACROSS packages — not inside any one of them |
| Registry interface | `get_detectors(tipo_factura: str) -> list` returning callables | Return strings, resolve lazily | Direct callables let orchestrators iterate and call without import chains |
| Transversal inclusion | Automatic — base list defined once, unioned per entry | Each entry lists transversals manually | Single source of truth (spec R4); adding a transversal updates one list |
| Unknown tipo_factura | Returns `[]`, no error, no fallback | Raise KeyError, log-and-skip | Spec R2 requires empty list; caller handles empty gracefully |
| centro_costo split | Shared helper `transversales/centro_costo_rules.py` + per-tipo wrappers | Full duplication per file, or single file with parameter | Keeps each per-tipo file <150 lines; common rules (~11) live once |
| normalized_rows builder | One shared `app/services/normalized_rows.py` parametrized by `error_groups: dict` | One builder per package (duplicated 5x) | Same 6-column output format across all tipos; DRY while flexible per tipo |
| mal_capitado relocation | `odontologia/` → `urgencias/` (PR 1) | Move to `transversales/` | Only called by urgencias orchestrator; not a transversal rule |
| detect_copago_entidad relocation | `urgencias/` → `transversales/` (PR 1) | Stay in `urgencias/` | No tipo_factura filter; applies to all entities — truly transversal |
| exporter dispatch | `tipo_factura_descripcion` column → registry → per-tipo orchestrator | Keep `area` param, add second dispatch key | Eliminates the `area == URGENCIAS` if/elif chain; detectors already filter internally |
| area backward compat | Keep `area` field in response; add `tipo_factura` alongside | Remove `area`, replace with `tipo_factura` | Frontend expects `area`; routes unchanged; non-breaking |
| Route changes | None — routes stay `/urgencias`, `/odontologia_equipos_basicos` | New routes per tipo | Routes are UI entry points; dispatch logic is internal |

## Data Flow

```
Excel Upload → Route (POST /urgencias)          [unchanged]
  → exporter.detect_problems_only(area="urgencias")  [area kept for compat]
    → Polars read → _SimpleSheet → get_column_indices [unchanged]
    → tipo_factura_registry.get_detectors("Urgencias")  [NEW]
    → detect_all_problems_urgencias(sheet, indices)     [shrunk — only Urgencias detectors]
    → build_normalized_rows(error_groups, ...)          [shared builder]
    → result { area:"urgencias", tipo_factura:"Urgencias", problemas:{...} }
  → JSON response                                    [backward-compatible]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/tipo_factura_registry.py` | Create | Maps `"Tipo Factura Descripcion"` → `list[Callable]`; auto-includes transversals |
| `app/services/transversales/centro_costo_rules.py` | Create | Shared `apply_common_centro_costo_rules()` for all 4 tipos |
| `app/services/transversales/detect_copago_entidad.py` | Move from urgencias/ | Transversal rule — no tipo_factura dependency |
| `app/services/normalized_rows.py` | Create | Shared `build_normalized_rows(error_groups, ...)` — replaces `urgencias/normalized_rows.py` |
| `app/services/hospitalizacion/__init__.py` | Create | Package init |
| `app/services/hospitalizacion/detect_all.py` | Create | Orquestador: transversales + Hospitalizacion detectors |
| `app/services/hospitalizacion/cantidades_hospitalizacion.py` | Move from urgencias/hospitalizacion.py | Extract `detect_cantidades_hospitalizacion` |
| `app/services/hospitalizacion/hospitalizacion_codes.py` | Move from urgencias/hospitalizacion.py | Extract `detect_hospitalizacion_codes` |
| `app/services/hospitalizacion/cantidades_soat_hospitalizacion.py` | Move from urgencias/ | Same detector, new package |
| `app/services/hospitalizacion/centro_costo_hospitalizacion.py` | Create | Shared rules + Hosp-specific (REGLA8 + crossing rules) |
| `app/services/intramural/__init__.py` | Create | Package init |
| `app/services/intramural/detect_all.py` | Create | Orquestador: transversales only initially |
| `app/services/intramural/centro_costo_intramural.py` | Create | Shared rules + Intramural-specific (REGLA5, REGLA5-REVERSE, INTRAMURAL_OTRAS_ENTIDADES) |
| `app/services/ambulatoria/__init__.py` | Create | Package init |
| `app/services/ambulatoria/detect_all.py` | Create | Orquestador: transversales only initially |
| `app/services/ambulatoria/centro_costo_ambulatoria.py` | Create | Shared rules + Ambulatoria-specific (AMBULATORIA_PYP) |
| `app/services/urgencias/detect_all.py` | Modify | Shrink to Urgencias-only detectors; imports updated |
| `app/services/urgencias/centro_costo_urgencias.py` | Modify | Shrink to shared-rules calls + Urgencias-specific crossing rule |
| `app/services/urgencias/__init__.py` | Modify | Remove hospitalizacion exports; add mal_capitado |
| `app/services/urgencias/normalized_rows.py` | Delete | Replaced by shared `app/services/normalized_rows.py` |
| `app/services/urgencias/hospitalizacion.py` | Delete | Split into individual files in hospitalizacion/ |
| `app/services/urgencias/detect_copago_entidad.py` | Delete | Moved to transversales/ |
| `app/services/odontologia/mal_capitado.py` | Delete (PR1) | Moved to urgencias/ |
| `app/services/urgencias/mal_capitado.py` | Move from odontologia/ (PR1) | Fix wrong package |
| `app/services/exporter.py` | Modify | PR2: dispatch by tipo_factura via registry; PR1: unchanged |
| `app/services/transversales/__init__.py` | Modify (PR1) | Add `detect_copago_entidad` export |
| `app/constants/base.py` | Modify (PR2) | Add `AREA_HOSPITALIZACION`, `AREA_INTRAMURAL`, `AREA_AMBULATORIA` |
| Tests: 9 files | Modify (PR2) | Update import paths for moved detectors |
| Tests: 4 new files | Create (PR2) | `test_hospitalizacion_detect_all`, `test_intramural_detect_all`, `test_ambulatoria_detect_all`, `test_tipo_factura_registry` |

## Interfaces / Contracts

### `tipo_factura_registry.py`

```python
from typing import Callable

# Private: string keys match EXACT Excel "Tipo Factura Descripcion" values
_TRANSVERSAL_DETECTORS: list[Callable] = [
    detect_decimales,
    detect_tipo_documento_edad,
    detect_codigo_entidad_vs_entidad_afiliacion,
    detect_tipo_usuario,
]

_REGISTRY: dict[str, list[Callable]] = {
    "Urgencias": _TRANSVERSAL_DETECTORS + [detect_cantidades_urgencias, ...],
    "Hospitalización": _TRANSVERSAL_DETECTORS + [detect_cantidades_hospitalizacion, ...],
    "Intramural": _TRANSVERSAL_DETECTORS + [detect_centro_costo_intramural],
    "Ambulatoria": _TRANSVERSAL_DETECTORS + [detect_centro_costo_ambulatoria],
    "Odontología": _TRANSVERSAL_DETECTORS + [...],
}

def get_detectors(tipo_factura: str) -> list[Callable]:
    """Returns detector callables for a tipo_factura. Empty list for unknown values."""
    if not tipo_factura:
        return []
    return _REGISTRY.get(tipo_factura, [])
```

### Orquestador contract (per-tipo `detect_all.py`)

```python
def detect_all_problems_hospitalizacion(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Same signature as detect_all_problems_urgencias.
    Returns (result_dict, responsables_map).
    result_dict: { "area": "hospitalizacion", "problemas": {...}, "totales": {...} }
    """
```

### Shared normalized_rows builder

```python
def build_normalized_rows(
    error_groups: dict[str, list],
    responsables_map: dict[str, str],
    fec_factura_map: dict[str, str] | None = None,
    fecha_cierre_vacia_map: dict[str, bool] | None = None,
) -> list[dict[str, str]]:
    """
    error_groups keys map to tipo_error labels.
    Each value is a list of detector result dicts.
    Returns 6-column normalized rows (same format as current).
    """
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — registry | `get_detectors()` for known/unknown/empty values | Parametrized pytest; mock imports for callable verification |
| Unit — per-tipo orchestrators | Each `detect_all_problems_<tipo>()` returns correct shape | Same pattern as existing `test_urgencias_detect_all.py` |
| Unit — centro_costo split | Each per-tipo file returns only its tipo's errors | Test with mixed-tipo fixture rows; verify no cross-contamination |
| Integration — exporter | `detect_problems_only()` dispatches correctly by tipo_factura | Integration test with multi-tipo Excel fixture |
| Regression | All 36 existing tests pass with updated imports | Run `pytest -v` after each PR; compare against baseline |

### Migration (PR 2)

1. Run `pytest -v --tb=short > baseline.txt` before PR 2
2. After each file move: update imports, run affected test files
3. After all moves: run full suite, diff against baseline
4. New tests for registry + 3 new orchestrators

## PR 1 vs PR 2 Boundary

### PR 1 (~4h, low risk) — Internal Filters Only
- Add `tipo_factura_descripcion` filter to 5 detectors in `urgencias/`
- Move `detect_copago_entidad.py` → `transversales/`
- Move `mal_capitado.py` → `urgencias/`
- Update imports in `urgencias/detect_all.py`, `urgencias/__init__.py`, `transversales/__init__.py`
- Update 3 test file imports
- Zero structural changes to package layout
- `pytest -v` must pass identically

### PR 2 (~8-14h, medium risk) — Structural Reorganization
- Create `hospitalizacion/`, `intramural/`, `ambulatoria/` packages
- Create `tipo_factura_registry.py`
- Move Hospitalizacion detectors out of `urgencias/`
- Split `centro_costo_urgencias.py` into shared helper + 4 per-tipo wrappers
- Create `app/services/normalized_rows.py` (shared builder)
- Create per-tipo `detect_all.py` orchestrators
- Update `exporter.py` dispatch
- Add `area` constants for new tipos
- Update ~9 test file imports; create 4 new test files
- `git mv` for file relocation to preserve history

## Open Questions

- None — all design decisions resolved above. Ready for tasks.
