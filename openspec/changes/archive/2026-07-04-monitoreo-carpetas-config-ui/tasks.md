# Tasks: Monitoreo de Carpetas — Config UI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 350–500 (store + endpoints + frontend + tests) |
| 400-line budget risk | Moderate |
| Chained PRs recommended | No |
| Chain strategy | N/A |
| Delivery strategy | ask-on-risk |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Store + constants + endpoints + POST /scan wiring | Single PR | Store, endpoints, and frontend are tightly coupled — no reason to split. All non-frontend changes are < 150 lines of net new code. |
| 2 | Frontend (config card, sidebar, permisos) | Same PR | Could technically be a separate PR if frontend needs independent review, but adds churn for no gain. |
| 3 | Tests | Same PR | Tests belong with the code they cover. |

**Decision**: Single PR unless the apply exceeds 400 lines, in which case split off frontend as PR 2.

---

## Phase 1: Store + Constants

- [x] 1.1 Create `app/utils/monitoreo_store.py` — `get_roots()`, `save_roots()`, `reset_roots()` with atomic write via `tempfile.mkstemp` + `Path.replace()`. Priority: JSON file > env var > empty list. Env var parsed as JSON array first, with semicolon-separated fallback. JSON shape includes `roots`, `fuente`, `ultima_actualizacion`.
- [x] 1.2 Add `MONITOREO_CONFIG_FILE = "data/monitoreo_carpetas_config.json"` constant to `app/constants/monitoreo_carpetas.py`
- [x] 1.3 Add `monitoreo_carpetas`, `monitoreo_carpetas:write` to `ALLOWED_PERMISOS` and `PERMISO_MUTUAL_EXCLUSION` in `app/constants/base.py`
- [x] 1.4 Add `Monitoreo de Carpetas` entry to `DASHBOARD_AREAS` in `app/constants/base.py` — slug `monitoreo_carpetas`, permiso `monitoreo_carpetas`, icon `FolderSearch`
- [x] 1.5 Re-export `MONITOREO_CONFIG_FILE` from `app/constants/__init__.py` — not needed, `from ... import *` auto-exports new constants

## Phase 2: Endpoints + POST /scan Wiring

- [x] 2.1 Add `from app.utils.monitoreo_store import get_roots, save_roots, reset_roots` import to `app/routes/monitoreo_carpetas.py`
- [x] 2.2 Create `GET /monitoreo-carpetas/config` — returns `{"status":"success","data":{"roots":[...],"fuente":"...","ultima_actualizacion":"..."},"errors":[]}`. No permission check.
- [x] 2.3 Create `PUT /monitoreo-carpetas/config` — requires `@permiso_requerido('monitoreo_carpetas:write')`. Validates body has `roots` as non-empty `list[str]`. Returns 403/422 as specified.
- [x] 2.4 Create `POST /monitoreo-carpetas/config/reset` — requires `@permiso_requerido('monitoreo_carpetas:write')`. Calls `reset_roots()` and returns current config.
- [x] 2.5 Modify `POST /monitoreo-carpetas/scan` — replaced `os.environ.get(ENV_MONITOREO_ROOTS, ...)` with `get_roots()`, removed inline JSON/semicolon parsing.

## Phase 3: Frontend

- [x] 3.1 Modify `frontend/src/pages/monitoreo-carpetas/main.tsx` — destructure `can_write` from `__INITIAL_DATA__` and pass as prop to `<MonitoreoCarpetasPage can_write={can_write} />`
- [x] 3.2 Modify `frontend/src/pages/monitoreo-carpetas/page.tsx` — accept `can_write: boolean` prop. Config card with dynamic inputs (write mode) or read-only display.
- [x] 3.3 Modify `frontend/src/components/app-sidebar.tsx` — add nav item for "Monitoreo de Carpetas" → `/monitoreo-carpetas` with `permiso: "monitoreo_carpetas"` and `FolderSearch` icon.
- [x] 3.4 Modify `frontend/src/pages/usuarios/page.tsx` — add `monitoreo_carpetas` and `monitoreo_carpetas:write` to `ALL_PERMISOS` and `PERMISO_PAIRS`.

## Phase 4: Tests

- [x] 4.1 Write `tests/services/monitoreo_carpetas/test_monitoreo_store.py` — 14 unit tests covering all get/save/reset scenarios with `tmp_path` fixture.
- [x] 4.2 Write integration test for config endpoints — 10 tests: GET (stored/env/no-auth), PUT (success/403/422), POST /reset (success/403).
- [x] 4.3 Write integration test for `POST /scan` using store — mocks `get_roots()` to return known paths, asserts scan uses them.
- [x] 4.4 Run existing monitoreo_carpetas test suite — 95 original tests + 25 new = 120 passing, zero regressions.
