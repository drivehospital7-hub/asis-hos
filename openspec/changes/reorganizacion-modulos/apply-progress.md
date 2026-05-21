# Apply Progress — Phase 1: constants/ package

**Change**: reorganizacion-modulos
**Mode**: Strict TDD
**Batch**: Phase 1 (T-01 + T-02)
**Status**: ✅ Complete

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| T-01 | `tests/services/test_constants_package.py` | Unit | ✅ 83/90 baseline | ✅ 6 failed (file not found) | ✅ 41/41 passed | ➖ Single (purely structural) | ✅ No changes needed |
| T-02 | `tests/services/test_constants_package.py` | Unit | ✅ 83/90 baseline | ✅ Same 6 (created same batch) | ✅ 41/41 passed | ➖ Single (purely structural) | ✅ No changes needed |

### Test Summary
- **Total tests written**: 41
- **Total tests passing**: 41
- **Layers used**: Unit (41)
- **Approval tests** (refactoring): 41
- **Pure functions created**: 0 (constants only)
- **Triangulation skipped**: Structural refactor — 1:1 constant extraction, no branching logic

## Completed Tasks

- [x] **T-01** — Created `app/constants/` package structure
- [x] **T-02** — Created domain modules with all constants migrated
- [ ] **T-03** — Skipped: `app/constants.py` not deleted yet (Phase 7). Imports work via package re-export anyway.

## Files Created

| File | Action | Lines | What It Contains |
|------|--------|-------|------------------|
| `app/constants/__init__.py` | Created | 12 | Re-exports from all 5 domain modules |
| `app/constants/base.py` | Created | 58 | General purpose: sheets, suffixes, areas, thresholds, images |
| `app/constants/columnas.py` | Created | 73 | Column definitions, headers, centros de costo |
| `app/constants/colores.py` | Created | 32 | Color constants for conditional formatting |
| `app/constants/odontologia.py` | Created | 232 | CUPS PyP, profesionales (odonto + EB), IDE PyP, mal capitado |
| `app/constants/urgencias.py` | Created | 495 | IDE Contrato rules, SOAT, hospitalización, CAPITA, reverse rules |
| `tests/services/test_constants_package.py` | Created | 265 | Approval tests for all domain modules |

## Deviations from Design

1. **No `equipos_basicos.py`**: The original tasks.md suggested a separate module, but the user's instructions didn't include it. EB constants were merged into `odontologia.py` (professionals, thresholds) and `columnas.py` (headers/columns to maintain `is COLUMNS_TO_KEEP` object identity).

2. **Python resolves package, not file**: In Python 3.14, `app/constants/__init__.py` takes precedence over `app/constants.py` even though the file still exists. This means the re-exports are ALREADY active, not just for Phase 7.

3. **`EQUIPOS_BASICOS_COLUMNS_TO_KEEP` and `EQUIPOS_BASICOS_REVISION_HEADERS`** placed in `columnas.py` (not `odontologia.py`) to maintain object identity with `COLUMNS_TO_KEEP` without requiring cross-module imports (impossible while `constants.py` shadows the package).

## Verification

- ✅ `pytest tests/` — 124 pass, 7 fail (all pre-existing, same baseline)
- ✅ `pytest tests/services/test_constants_package.py` — 41/41 pass
- ✅ `python run_dev.py` — starts without errors
- ✅ `from app.constants import ALL_200+_CONSTANTS` — all importable
- ✅ `python -c "from app.constants import *"` — no errors
- ✅ `app/constants.py` still exists (not deleted — Phase 7)
