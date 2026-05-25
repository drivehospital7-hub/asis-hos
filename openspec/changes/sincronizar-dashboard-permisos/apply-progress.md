# Apply Progress: sincronizar-dashboard-permisos

**Status**: ✅ Complete

## Summary

### T1: DASHBOARD_AREAS + _filter_areas in `base.py` ✅
- Added 6-entry `DASHBOARD_AREAS` constant: Urgencias, Odontología, Control de Novedades, Facturas Abiertas, Ordenado y Facturado, Derechos
- Each entry includes: title, slug, permiso, href, tone, pending_label, description
- Added `_filter_areas(permisos)` function: empty/None or `"*"` → all 6 areas; otherwise filtered by `a["permiso"] in permisos`
- Each returned area includes `"pending": 0` (removes hardcoded fake counts)

### T2: Filter dashboard in `home.py` ✅
- Imported `_filter_areas` from `app.constants.base`
- Replaced 3-item hardcoded `areas` list with `_filter_areas(permisos)` using `session.get("permisos", [])`

### T3: Route guard in `derechos.py` ✅
- Imported `permiso_requerido` from `app.utils.auth`
- Added `@permiso_requerido("derechos")` between route decorator and view function

### T4: Frontend cleanup in `page.tsx` ✅
- Removed 25-line hardcoded `areas` fallback array
- Now uses `const areas: IndexArea[] = initialData?.areas ?? [];`

### T5: Tests ✅
- 6 unit tests for `_filter_areas`: admin, single, multiple, no match, empty, None
- 2 integration tests for dashboard filtering (admin sees 6, odontologia-only sees 1)
- 2 integration tests for derechos route guard (without permiso → 403, with permiso → 200)

## Test Results

All 33 tests in `tests/services/test_react_frontend.py` pass.
Full suite: 443 passed, 2 failed (both pre-existing, unrelated to this change).

## Files Changed

| File | Action |
|------|--------|
| `app/constants/base.py` | Modified – added DASHBOARD_AREAS + _filter_areas |
| `app/routes/home.py` | Modified – use _filter_areas instead of hardcoded list |
| `app/routes/derechos.py` | Modified – added @permiso_requerido decorator |
| `frontend/src/pages/index/page.tsx` | Modified – removed hardcoded areas fallback |
| `tests/services/test_react_frontend.py` | Modified – added TestDashboardPermisos (9 tests) |
