# Tasks: Perfiles de Usuarios — Plantillas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500–560 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Tasks 1–4 + 7–8 (backend, ~378 lines)<br>PR 2: Tasks 5–6 (React + Jinja2 UI, ~120 lines) |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Store + API + tests (T1–T4, T7–T8) | PR 1 → main | Backend: templates.json CRUD, endpoint, all tests. Self-contained, no UI. |
| 2 | React + Jinja2 UI (T5–T6) | PR 2 → main | Frontend: dropdown + pre-fill. Depends on PR 1 for endpoint. |

---

## Dependency Graph

```
T1 (Constants) ──→ T2 (Store CRUD) ──→ T3 (API endpoint) ──→ T5 (React UI)
                                    │                       └── T6 (Jinja2 UI)
                                    │
                                    └── T4 (initial_data)
                                    │
                                    └── T7 (Store tests)
                                    │
                                    └── T8 (API tests)
```

---

## Phase 1: Foundation (PR 1)

- [x] **T1** Add `DEFAULT_TEMPLATES` (list of 3 dicts: odontologia, urgencias, auditor) to `app/constants/base.py`. No deps. Small.

- [x] **T2** Create `app/utils/templates_store.py` — module-level fns: `list_templates()`, `get_template(name)`, `create_template(name, descripcion, permisos)`, `update_template(name, updates)`, `delete_template(name)`. Atomic write via `_save_templates()` (temp + os.replace). Default seeding via `_ensure_default_templates()` on first load. Delete guard for default template names. Deps: T1. Medium.

## Phase 2: API (PR 1)

- [x] **T3** Add `GET /auth/api/templates` endpoint with `@admin_requerido` in `app/routes/auth.py`. Returns `{"status": "success", "data": {"templates": [...]}, "errors": []}`. Deps: T2. Small.

- [x] **T4** Add `"templates": templates_store.list_templates()` to `initial_data` dict in `@auth_bp.get("/usuarios")` route. Deps: T2. Small.

## Phase 3: UI (PR 2)

- [x] **T5** Modify `frontend/src/pages/usuarios/page.tsx` — fetch `/auth/api/templates` on mount, add `<select>` dropdown "Basado en plantilla" above permisos checkboxes, pre-fill `formPermisos` on select, clear when "-- Seleccionar --", hide dropdown + checkboxes when `formRol === "admin"`. Deps: T3. Medium.

- [x] **T6** Modify `app/templates/usuarios.html` — add `<select id="template-select">` dropdown above permisos fieldset (both create form and edit modal), JS fetch templates on DOMContentLoaded, checkbox pre-fill on select, hide when rol=admin (same `togglePermisos()` pattern). Deps: T3. Medium.

## Phase 4: Tests (PR 1)

- [x] **T7** Create `tests/utils/test_templates_store.py` — unit tests for all CRUD operations (list, get, create, create duplicate, update name, update permisos, delete custom, delete default blocked, delete missing), `_ensure_default_templates` first-boot seeding, corrupt file returns empty list, atomic write pattern. Follow mock pattern from `test_users_store.py`. Deps: T2. Large.

- [x] **T8** Create or extend route test file — Flask test client: `GET /auth/api/templates` returns 200 with 3 templates, 401 without session, 403 for non-admin session. Deps: T3. Small.

---

## Task Detail

### T1: Add DEFAULT_TEMPLATES to constants

**File**: `app/constants/base.py`
**Acceptance**: `from app.constants.base import DEFAULT_TEMPLATES` yields a list of 3 dicts with `nombre`, `descripcion`, `permisos` keys matching the design. Names: "Odontología", "Urgencias", "Auditor".

### T2: Create templates_store.py

**File**: `app/utils/templates_store.py` (NEW)
**Acceptance**:
- `list_templates()` returns copies of all templates from `instance/templates.json`
- `get_template("odontologia")` returns full dict; `get_template("ghost")` returns `None`
- `create_template("nueva", "...", ["odontologia"])` saves and returns `(True, msg)`; duplicate returns `(False, "ya existe")`
- `update_template("odontologia", {"nombre": "odonto_v2"})` renames; `update_template("odontologia", {"permisos": [...]})` updates permisos
- `delete_template("mi_perfil")` removes; `delete_template("odontologia")` returns `(False, "No se puede eliminar la plantilla por defecto")`
- First call when file missing creates 3 defaults via `_ensure_default_templates()`
- Atomic write: write to `.tmp` → `os.replace()`
- `_load_templates()` returns `[]` on corrupt JSON (logged error)

### T3: GET /auth/api/templates

**File**: `app/routes/auth.py`
**Acceptance**:
- `GET /auth/api/templates` with valid admin session → `{"status":"success","data":{"templates":[...]},"errors":[]}`
- No session → 401 redirect
- Session without `*` permiso → 403

### T4: Templates in initial_data

**File**: `app/routes/auth.py` (the `/auth/usuarios` GET route)
**Acceptance**: `render_template("react_shell.html", ..., initial_data={..., "templates": [...]})` — React page receives templates array at bootstrap.

### T5: React dropdown + pre-fill

**File**: `frontend/src/pages/usuarios/page.tsx`
**Acceptance**:
- Templates fetched on mount from `/auth/api/templates` (or from initial_data)
- `<select>` dropdown "Basado en plantilla" rendered above permisos checkboxes
- Selecting a template sets `formPermisos` to template's `permisos` (replaces current)
- Selecting "-- Seleccionar --" (`""`) clears all checkboxes
- Dropdown hidden when `formRol === "admin"` (checkboxes hidden too)
- In edit mode, dropdown shown but defaults to "-- Seleccionar --"
- All permisos checkboxes editable after pre-fill

### T6: Jinja2 dropdown + pre-fill

**File**: `app/templates/usuarios.html`
**Acceptance**:
- `<select id="template-select">` rendered above `#permisos-group` in create form
- Same dropdown in edit modal, above permisos fieldset
- JS on DOMContentLoaded: fetch `/auth/api/templates` → populate options
- JS `onchange`: uncheck all checkboxes, check only those matching template's `permisos`
- Dropdown hidden when rol=admin (via `togglePermisos()` extended)
- "-- Seleccionar --" (`""`) option clears all checkboxes

### T7: Store unit tests

**File**: `tests/utils/test_templates_store.py` (NEW)
**Acceptance**:
- Test classes for each operation, matching `test_users_store.py` patterns
- `test_list_templates`: mocked file with 3 entries returns 3 dicts
- `test_get_template_exists` / `test_get_template_missing`
- `test_create_template_success` / `test_create_template_duplicate`
- `test_update_template_name` / `test_update_template_permisos`
- `test_delete_template_custom` / `test_delete_template_default_blocked` / `test_delete_template_missing`
- `test_default_templates_seeded_on_first_load`: temp dir, no file → call `_load_templates()` → 3 templates created
- `test_corrupt_json_returns_empty_list`
- `test_atomic_write_uses_temp_and_replace`
- Mock `TEMPLATES_FILE` path, mock `_save_templates` for mutation tests, real temp file for seeding tests

### T8: API integration tests

**File**: `tests/services/test_templates_api.py` (NEW) or extend existing route test
**Acceptance**:
- `GET /auth/api/templates` with admin session → 200, `data.templates` has 3 items
- Without session → 302 redirect to login
- With non-admin session (permisos不含 `*`) → 403
- Use `app_client` fixture, mock/isolate `TEMPLATES_FILE` to temp path
