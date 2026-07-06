# Archive Report: Monitoreo de Carpetas — Config UI

**State**: `archived`
**Archived at**: `openspec/changes/archive/2026-07-04-monitoreo-carpetas-config-ui/`
**Date**: 2026-07-04

---

## Change Summary

Add admin UI to edit network folder scan roots without infrastructure changes (env var edits + restart). A JSON store with atomic write (`tempfile.mkstemp` + `Path.replace()`) provides persistence from the browser. Backend endpoints (`GET/PUT/config`, `POST/config/reset`, modified `POST/scan`) route through the store with env var fallback. Frontend adds a config card (textarea + Guardar/Restaurar) gated by `monitoreo_carpetas:write` permission. Permissions and sidebar nav item added.

---

## Delivery Checklist

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | `GET /config` returns persisted roots or env var | ✅ | `test_get_config_returns_stored_roots`, `test_get_config_fallback_env` pass |
| 2 | `PUT /config` persists atomically and reflects immediately | ✅ | `test_put_config_success`, atomic write tests pass |
| 3 | `POST /config/reset` deletes persisted, GET returns env var | ✅ | `test_post_reset_success`, `test_reset_deletes_json` pass |
| 4 | `POST /scan` uses store if exists, fallback to env var | ✅ | `test_post_scan_uses_store`, `test_post_scan_fallback` pass |
| 5 | Admin edits from UI; without `:write` read-only | ✅ | `can_write` prop controls Input vs display-only in page.tsx |
| 6 | Permissions appear in user lists | ✅ | `monitoreo_carpetas` + `monitoreo_carpetas:write` in `ALL_PERMISOS`, `PERMISO_PAIRS`, usuarios/page.tsx |
| 7 | Nav item visible according to permission | ✅ | Sidebar item with `permiso: "monitoreo_carpetas"` in app-sidebar.tsx |
| 8 | Existing tests pass | ✅ | 95 original + 25 new = 120 passing, zero regressions |

**All success criteria met.**

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `app/utils/monitoreo_store.py` | **Create** | `get_roots()`, `save_roots()`, `reset_roots()` with atomic tempfile+replace. JSON shape: `roots`, `fuente`, `ultima_actualizacion`. Env var parse: JSON array → semicolon → empty. |
| `app/constants/monitoreo_carpetas.py` | **Modify** | Added `MONITOREO_CONFIG_FILE = "data/monitoreo_carpetas_config.json"` |
| `app/constants/base.py` | **Modify** | Added `monitoreo_carpetas`, `monitoreo_carpetas:write` to `ALLOWED_PERMISOS`, `PERMISO_MUTUAL_EXCLUSION`, `DASHBOARD_AREAS` |
| `app/routes/monitoreo_carpetas.py` | **Modify** | +3 endpoints: `GET /config`, `PUT /config` (+permiso check), `POST /config/reset` (+permiso check). Modified `POST /scan` to use `get_roots()` instead of `os.environ.get()` |
| `frontend/src/pages/monitoreo-carpetas/main.tsx` | **Modify** | Destructure `can_write` from `__INITIAL_DATA__`, pass as prop |
| `frontend/src/pages/monitoreo-carpetas/page.tsx` | **Modify** | Config card: dynamic input array (write mode) or read-only display. Guardar/Restaurar default buttons. |
| `frontend/src/components/app-sidebar.tsx` | **Modify** | Nav item "Monitoreo de Carpetas" → `/monitoreo-carpetas`, `permiso: "monitoreo_carpetas"`, `FolderSearch` icon |
| `frontend/src/pages/usuarios/page.tsx` | **Modify** | Added `monitoreo_carpetas`, `monitoreo_carpetas:write` to `ALL_PERMISOS` and `PERMISO_PAIRS` |
| `app/data/monitoreo_carpetas_config.json` | **Create** | Created on first `save_roots()` call (runtime artifact, not committed) |
| `tests/services/monitoreo_carpetas/test_monitoreo_store.py` | **Create** | 14 unit tests: get/save/reset/fallback/atomicity/corrupt recovery |
| `tests/services/monitoreo_carpetas/test_integration.py` | **Modify** | +10 config endpoint tests + 1 scan-with-store test |

---

## Final Test Results

- **Total tests**: 120 (95 original + 25 new)
- **Passed**: 120
- **Failed**: 0
- **Skipped**: 0
- **Duration**: 6.10s
- **Coverage**: Not configured (no threshold)

```
python -m pytest tests/services/monitoreo_carpetas/ -v
collected 120 items
... (all 120 passed in 6.10s)
```

**Spec compliance**: 12/12 scenarios covered by passing tests
**Critical issues**: None
**Warnings**: None

---

## Spec Sync

| Domain | Action | Details |
|--------|--------|---------|
| `folder-scanner-config` | **Created** | New full spec — 4 requirements (R1–R4), 12 scenarios. Persistent at `openspec/specs/folder-scanner-config/spec.md`. |
| `folder-scanner` | **Updated** | R1: "Scan Configured Roots" modified — scanner reads from folder-scanner-config store instead of direct env var access. Updated scenarios include corrupt-store fallback. |

---

## Lessons Learned

1. **`__init__.py` re-export gap**: `app/constants/__init__.py` does not include `from app.constants.monitoreo_carpetas import *`. No code currently relies on it (store imports directly), but future code doing `from app.constants import MONITOREO_CONFIG_FILE` would fail. Consider adding it for forward-compatibility.

2. **Orphan file write in test**: `test_get_config_returns_stored_roots` writes a config JSON to `tmp_path` but mocks `get_roots` at the route level, making the file write dead code. The test assertion is correct — just test hygiene.

---

## SDD Cycle Complete

The full SDD cycle has been completed for this change:

| Phase | Artifact | Status |
|-------|----------|--------|
| Proposal | `proposal.md` | ✅ |
| Spec (delta) | `specs/folder-scanner/spec.md` | ✅ |
| Spec (new) | `specs/folder-scanner-config/spec.md` | ✅ (synced to main) |
| Design | `design.md` | ✅ |
| Tasks | `tasks.md` | ✅ (14/14 complete) |
| Verify | `verify-report.md` | ✅ (PASS) |
| Archive | `archive-report.md` | ✅ |
