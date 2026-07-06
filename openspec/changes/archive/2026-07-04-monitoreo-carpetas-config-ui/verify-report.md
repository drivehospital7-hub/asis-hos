## Verification Report

**Change**: monitoreo-carpetas-config-ui
**Version**: folder-scanner-config/spec.md (12 scenarios across 4 requirements)
**Mode**: Standard

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 14 |
| Tasks complete | 14 |
| Tasks incomplete | 0 |

All 14 tasks checked as done. 25 new tests (14 store + 10 config endpoints + 1 scan-with-store) + 95 existing = 120 total.

### Build & Tests Execution

**Tests**: ✅ 120 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
python -m pytest tests/services/monitoreo_carpetas/ -v
collected 120 items
... (all 120 passed in 6.10s)
```

**Coverage**: ➖ Not explicitly verified (no coverage threshold configured for this change)

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| R1: Read Roots with Fallback | Manual JSON exists | `test_monitoreo_store.py::TestGetRoots::test_manual_json_exists` | ✅ COMPLIANT |
| R1: Read Roots with Fallback | Fallback to env var (JSON array) | `test_monitoreo_store.py::TestGetRoots::test_fallback_to_env_var_json` | ✅ COMPLIANT |
| R1: Read Roots with Fallback | Neither configured (no JSON, no env) | `test_monitoreo_store.py::TestGetRoots::test_neither_configured` | ✅ COMPLIANT |
| R1: Read Roots with Fallback | JSON corrupt → fallback | `test_monitoreo_store.py::TestGetRoots::test_corrupt_json_falls_back` + `test_corrupt_json_no_env_fallback` | ✅ COMPLIANT |
| R2: Save Roots Atomically | First save (no JSON exists) | `test_monitoreo_store.py::TestSaveRoots::test_first_save_creates_json` | ✅ COMPLIANT |
| R2: Save Roots Atomically | Overwrite existing | `test_monitoreo_store.py::TestSaveRoots::test_overwrite_existing` | ✅ COMPLIANT |
| R2: Save Roots Atomically | Write failure (disk full) | `test_monitoreo_store.py::TestSaveRoots::test_atomic_write_preserves_original_on_failure` | ✅ COMPLIANT |
| R3: Reset to Env Default | Reset from manual | `test_monitoreo_store.py::TestResetRoots::test_reset_deletes_json` | ✅ COMPLIANT |
| R3: Reset to Env Default | Reset with no JSON (no-op) | `test_monitoreo_store.py::TestResetRoots::test_reset_noop_when_absent` | ✅ COMPLIANT |
| R4: Env Var Parsing | JSON array env | `test_monitoreo_store.py::TestGetRoots::test_fallback_to_env_var_json` | ✅ COMPLIANT |
| R4: Env Var Parsing | Semicolon env | `test_monitoreo_store.py::TestGetRoots::test_fallback_to_env_var_semicolon` | ✅ COMPLIANT |
| R4: Env Var Parsing | Empty env | `test_monitoreo_store.py::TestGetRoots::test_empty_env_var_with_json_absent` | ✅ COMPLIANT |

**Compliance summary**: 12/12 scenarios compliant

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Store: `get_roots` returns JSON > env var > empty | ✅ Implemented | `_read_config()` → `os.environ.get(...)` → `return []`. Fallback chain verified. |
| Store: `save_roots` uses tempfile + `Path.replace` | ✅ Implemented | `tempfile.mkstemp(dir=tmp_dir, suffix=".tmp")` + `Path(tmp_path).replace(CONFIG_FILE)`. Atomic write with cleanup on failure. |
| Store: `reset_roots` deletes JSON file | ✅ Implemented | `CONFIG_FILE.unlink()` inside `if CONFIG_FILE.exists()` guard. Silent no-op. |
| Endpoints: GET /config returns config | ✅ Implemented | Route `@monitoreo_carpetas_bp.get("/config")` returns `get_roots()` JSON. No auth/permission decorator. |
| Endpoints: PUT /config validates and saves | ✅ Implemented | Validates `roots` is a non-empty `list[str]`, calls `save_roots()`. Returns 422 on validation failure. |
| Endpoints: POST /config/reset deletes and returns env var | ✅ Implemented | Calls `reset_roots()`, then `get_roots()` which falls back to env var. |
| Endpoints: PUT and POST /config/reset require `monitoreo_carpetas:write` | ✅ Implemented | Both have `@permiso_requerido("monitoreo_carpetas:write")` |
| Endpoints: POST /scan uses `get_roots()` instead of `os.environ` | ✅ Implemented | `roots, _fuente, _ultima_actualizacion = get_roots()` at line 159. No direct `os.environ.get(ENV_MONITOREO_ROOTS, ...)` |
| Permissions: `monitoreo_carpetas` and `:write` in `ALLOWED_PERMISOS` | ✅ Implemented | base.py lines 92-93 |
| Permissions: `monitoreo_carpetas` + `:write` in `PERMISO_MUTUAL_EXCLUSION` | ✅ Implemented | base.py lines 104-105 |
| Permissions: `DASHBOARD_AREAS` has monitoreo_carpetas entry | ✅ Implemented | base.py lines 238-245 with slug `monitoreo_carpetas`, permiso `monitoreo_carpetas`, icon absent (icon not used in DASHBOARD_AREAS) |
| Frontend: Config card shows with `can_write`, read-only without | ✅ Implemented | `can_write` prop controls Input vs read-only display (page.tsx L220-243), add button (L204-209), action buttons (L248-259) |
| Frontend: Sidebar has Monitoreo de Carpetas nav item | ✅ Implemented | app-sidebar.tsx line 32 with `FolderSearch` icon, permiso `monitoreo_carpetas` |
| Frontend: Usuarios page has new permisos in `ALL_PERMISOS` | ✅ Implemented | usuarios/page.tsx lines 49-51. Also in `PERMISO_PAIRS` (lines 59-60). |
| Frontend: `main.tsx` passes `can_write` from `__INITIAL_DATA__` | ✅ Implemented | main.tsx lines 8, 16. `initial_data` set in route (monitoreo_carpetas.py lines 57-60). |

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Persistence backend: JSON file | ✅ Yes | `monitoreo_carpetas_config.json` in `app/data/` |
| Write strategy: atomic tempfile+replace | ✅ Yes | `tempfile.mkstemp` + `Path.replace()` |
| GET /config auth: no permission check | ✅ Yes | No auth decorator on GET /config endpoint |
| Frontend data flow: `can_write` prop from `main.tsx` | ✅ Yes | Prop flows through `__INITIAL_DATA__` → `main.tsx` → `page.tsx` |
| PUT validation: basic list-of-strings check | ✅ Yes | No reachability/UNC validation — just `list[str]` check |

### Issues Found

**CRITICAL**: None

**WARNING**: None

**SUGGESTION**: 
1. `app/constants/__init__.py` does NOT include `from app.constants.monitoreo_carpetas import *`. Task 1.5 marked this as "not needed", but if any future code does `from app.constants import MONITOREO_CONFIG_FILE`, it will fail. Currently no code relies on this re-export (the store imports directly), so this is a suggestion for forward-compatibility.
2. `test_integration.py::TestConfigEndpoints::test_get_config_returns_stored_roots` writes a config JSON file to `tmp_path` but then mocks `get_roots` at the route level, making the file write dead code. The test still validates the route response correctly — this is just a test hygiene observation. Consider removing the orphan file write or making it a true store-level integration test.

### Verdict
**PASS**

All 14 tasks complete, 12/12 spec scenarios covered by passing tests, 120/120 tests pass. All correctness requirements verified by static evidence. No critical or warning issues found. Design decisions faithfully implemented.
