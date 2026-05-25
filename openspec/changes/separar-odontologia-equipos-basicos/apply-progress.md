# Apply Progress: separar-odontologia-equipos-basicos

**Mode**: Strict TDD (pytest)
**Delivery**: size:exception — single PR, all 25 tasks
**Completed**: 2026-05-25

## Completed Tasks

### Phase 1: Foundation
- [x] 1.1 Added `odontologia_equipos_basicos` to `ALLOWED_PERMISOS` in `app/constants/base.py`
- [x] 1.2 Created `app/constants/equipos_basicos.py` with all EB constants (profesionales, thresholds, centro_costo, revision_headers, columns_to_keep)
- [x] 1.3 Added `from app.constants.equipos_basicos import *` to `app/constants/__init__.py`
- [x] 1.4 Removed EB blocks (PROFESIONALES_EQUIPOS_BASICOS + thresholds) from `app/constants/odontologia.py`
- [x] 1.5 Removed EB constants (CENTRO_COSTO_EQUIPOS_BASICOS, EQUIPOS_BASICOS_REVISION_HEADERS, EQUIPOS_BASICOS_COLUMNS_TO_KEEP) from `app/constants/columnas.py`

### Phase 2: Core
- [x] 2.1 Created `app/routes/odontologia_equipos_basicos.py` — Blueprint with GET (React shell) + POST (upload+detect with area=AREA_EQUIPOS_BASICOS)
- [x] 2.2 Registered blueprint in `app/__init__.py` factory with `url_prefix="/odontologia-equipos-basicos"`
- [x] 2.3 Created `frontend/src/pages/odontologia-equipos-basicos/page.tsx`, `main.tsx`, `index.html` — adapted from odontología page

### Phase 3: Decoupling + Integration
- [x] 3.1 Removed `equipos_basicos: bool` param from `detect_problems_only()` signature; callers pass `area=AREA_EQUIPOS_BASICOS`
- [x] 3.2 Removed `area_effective` variable and `or equipos_basicos` guard from `_do_detect_problems()`; now uses `area` directly
- [x] 3.3 Removed `equipos_basicos = request.form.get(...)` from `app/routes/excel_headers.py`; added `AREA_ODONTOLOGIA` import and explicit area param
- [x] 3.4 Removed checkbox EB block + `actualizarReglasModal()` JS function + its DOMContentLoaded listener from `app/templates/excel_headers.html`
- [x] 3.5 Updated `app/templates/base.html` — added `odontologia_equipos_basicos.excel_headers_react` to nav_items dict and endpoint_map
- [x] 3.6 Updated `app/templates/home.html` — added EB card with `odontologia_equipos_basicos` permiso guard
- [x] 3.7 Updated `frontend/src/components/app-sidebar.tsx` — added "Equipos Básicos" nav item with `odontologia_equipos_basicos` permiso
- [x] 3.8 Updated `app/templates/usuarios.html` — added `odontologia_equipos_basicos` checkbox (label: "Equipos Básicos"); relabeled `equipos_basicos` to "Ordenado y Facturado" (both create form and edit modal)
- [x] 3.9 Updated `frontend/src/pages/usuarios/page.tsx` — added `odontologia_equipos_basicos` to `ALL_PERMISOS` (label: "Equipos Básicos"); relabeled `equipos_basicos` to "Ordenado y Facturado"

### Phase 4: Testing
- [x] 4.1 Tests for GET route (200 with permiso, 403 without, 401 unauthenticated)
- [x] 4.2 Tests for POST processing EB Excel (validates response shape)
- [x] 4.3 Tests for POST rejecting missing file / invalid extension
- [x] 4.4 Tests for exporter TypeError when called with equipos_basicos kwarg
- [x] 4.5 Tests for constants importability (PROFESIONALES_EQUIPOS_BASICOS, thresholds, centro_costo)
- [x] 4.6 Tests for full roundtrip with real EB Excel (clean, empty, missing columns)
- [x] 4.7 Tests for permission isolation (EB user blocked from /odontologia/, vice versa)
- [x] 4.8 Full pytest suite passes (445 passed, 0 failed)

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.5 | N/A (structural) | N/A | ✅ 409/409 | ➖ Structural | ✅ Applied | ➖ Single | ➖ None needed |
| 2.1 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 26/26 pass | ✅ 7+ scenarios | ➖ None needed |
| 2.2 | (covered by 2.1 tests) | Integration | ✅ 445/445 | ✅ Written | ✅ Passed | ➖ Single import | ➖ None needed |
| 2.3 | N/A (frontend) | N/A | N/A (new) | ➖ Structural | ✅ Created | ➖ Single | ➖ None needed |
| 3.1-3.2 | test_exporter_error_paths.py | Unit | ✅ 409/409 | ✅ Written | ✅ 445/445 pass | ✅ 4 test cases | ➖ None needed |
| 3.3 | (covered by 2.1/4.1 tests) | Integration | ✅ 445/445 | ✅ Written | ✅ Passed | ➖ Single | ➖ None needed |
| 3.4 | N/A (template) | N/A | ✅ 445/445 | ➖ Structural | ✅ Applied | ➖ Single | ➖ None needed |
| 3.5-3.9 | N/A (templates/UI) | N/A | ✅ 445/445 | ➖ Structural | ✅ Applied | ➖ Single | ➖ None needed |
| 4.1 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 4/4 pass | ✅ 4 scenarios | ➖ None needed |
| 4.2 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 3/3 pass | ✅ 3 scenarios | ➖ None needed |
| 4.3 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 3/3 pass | ✅ 3 scenarios | ➖ None needed |
| 4.4 | test_odontologia_equipos_basicos.py | Unit | ✅ 409/409 | ✅ Written | ✅ 4/4 pass | ✅ 4 cases | ➖ None needed |
| 4.5 | test_odontologia_equipos_basicos.py | Unit | ✅ 409/409 | ✅ Written | ✅ 5/5 pass | ✅ 5 scenarios | ➖ None needed |
| 4.6 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 3/3 pass | ✅ 3 cases | ➖ None needed |
| 4.7 | test_odontologia_equipos_basicos.py | Integration | ✅ 409/409 | ✅ Written | ✅ 4/4 pass | ✅ 4 scenarios | ➖ None needed |
| 4.8 | Full suite | Regression | ✅ 409/409 | N/A | ✅ 445/445 pass | N/A | ➖ None needed |

### Test Summary
- **Total tests written**: 26 (in test_odontologia_equipos_basicos.py)
- **Total tests passing**: 26
- **Total full suite**: 445 passing, 0 failed
- **Layers used**: Unit (9), Integration (17)
- **Approval tests** (refactoring): 0 (pre-existing tests updated: test_constants_package.py line 250, test_exporter_error_paths.py line 202)
- **Pure functions created**: 0 (framework integration tests)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `app/constants/base.py` | Modified | Added `odontologia_equipos_basicos` to `ALLOWED_PERMISOS` |
| `app/constants/equipos_basicos.py` | **Created** | Module with all EB constants (profesionales, thresholds, centro_costo, headers, columns) |
| `app/constants/__init__.py` | Modified | Added re-export from `equipos_basicos` |
| `app/constants/odontologia.py` | Modified | Removed EB-specific constants section |
| `app/constants/columnas.py` | Modified | Removed `CENTRO_COSTO_EQUIPOS_BASICOS`, `EQUIPOS_BASICOS_REVISION_HEADERS`, `EQUIPOS_BASICOS_COLUMNS_TO_KEEP` |
| `app/routes/odontologia_equipos_basicos.py` | **Created** | Blueprint with GET (React shell) + POST (upload/process) |
| `app/__init__.py` | Modified | Import + register new blueprint with url_prefix |
| `app/routes/excel_headers.py` | Modified | Removed `equipos_basicos` form field + param; added `AREA_ODONTOLOGIA` to call |
| `app/services/exporter.py` | Modified | Removed `equipos_basicos` param from both functions; simplified `_do_detect_problems` |
| `app/templates/excel_headers.html` | Modified | Removed checkbox EB + `actualizarReglasModal()` JS |
| `app/templates/base.html` | Modified | Added EB to nav_items dict and endpoint_map |
| `app/templates/home.html` | Modified | Added EB card with permiso check |
| `app/templates/usuarios.html` | Modified | Added `odontologia_equipos_basicos` checkbox; relabeled `equipos_basicos` to "Ordenado y Facturado" |
| `frontend/src/pages/odontologia-equipos-basicos/page.tsx` | **Created** | React page for EB (adapted from odontología) |
| `frontend/src/pages/odontologia-equipos-basicos/main.tsx` | **Created** | React entry point for EB |
| `frontend/src/pages/odontologia-equipos-basicos/index.html` | **Created** | HTML shell for EB |
| `frontend/src/components/app-sidebar.tsx` | Modified | Added "Equipos Básicos" nav item |
| `frontend/src/pages/usuarios/page.tsx` | Modified | Added `odontologia_equipos_basicos` to ALL_PERMISOS; relabeled `equipos_basicos` |
| `frontend/vite.config.ts` | Modified | Added EB page entry to rollupOptions.input |
| `tests/services/test_odontologia_equipos_basicos.py` | **Created** | 26 tests covering all spec scenarios (R1-R6) |
| `tests/services/test_constants_package.py` | Modified | Updated `is` to `==` for EB columns assertion |
| `tests/services/test_exporter_error_paths.py` | Modified | Updated `equipos_basicos=True` to `area="equipos_basicos"` |
| `tests/conftest.py` | Modified | Added `fresh_client` fixture for session-isolated tests |

## Deviations from Design

None — implementation matches design exactly.

## Issues Found

1. **Session leakage in Flask test client**: The `app_client` fixture reuses session cookies across tests. Resolved by adding a `fresh_client` fixture that provides a clean test client with no prior session state for tests that require session isolation.

2. **`EQUIPOS_BASICOS_COLUMNS_TO_KEEP` identity change**: Previously this was `COLUMNS_TO_KEEP` (same object reference). Now it's a separate frozenset with identical values. The pre-existing `is` assertion in `test_constants_package.py` was updated to `==`.

3. **Exporter test required update**: Pre-existing `test_detection_raises_in_equipos_basicos_returns_error_dict` was passing `equipos_basicos=True` kwarg which no longer exists. Updated to use `area="equipos_basicos"`.

## Status

**25/25 tasks complete. Ready for verify.**
