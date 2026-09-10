# Tasks: CRUD catálogos modificables + reglas vinculadas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Backend: ~400 lines) → PR 2 (Frontend: ~480 lines) → PR 3 (Tests: ~200 lines) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception (single PR approved by maintainer)
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend service + API routes | PR 1 | Verifiable via curl/API tests |
| 2 | Frontend page + components | PR 2 | Depends on PR 1 endpoints |
| 3 | Tests | PR 3 | Can merge into PR 1 if under 400 |

---

## Phase 1: Backend Service — `catalogos_service.py`

- [x] 1.1 Create `app/services/reglas/catalogos_service.py` with `list_catalogos()` — `SELECT key, descripcion, dominio, value, updated_at` LEFT JOIN `condiciones` + `reglas` for `regla_count`, ordered by key
- [x] 1.2 Implement `get_catalogo(key)` — `SELECT` single row, return `None` if missing; format value as array + count
- [x] 1.3 Implement `create_catalogo(data)` — validate `key` non-empty/unique, `value` must be list (422), `INSERT ... RETURNING *`
- [x] 1.4 Implement `update_catalogo(key, data)` — strip `key` from body, reject non-array value (422), `UPDATE` value/descripcion/dominio, set `updated_at = now()`
- [x] 1.5 Implement `delete_catalogo(key)` — query `condiciones WHERE operador='cat_in' AND valor_esperado=:key JOIN reglas`, raise if any active rule found, allow with warning for draft/retired only
- [x] 1.6 Implement `get_catalogo_reglas(key)` — `SELECT DISTINCT reglas.id, nombre, dominio, estado, version, activo JOIN condiciones ON reglas.id = condiciones.regla_id WHERE condiciones.operador='cat_in' AND condiciones.valor_esperado=:key`

## Phase 2: Backend Routes — `reglas_api.py` + `reglas_admin.py`

- [x] 2.1 Refactor existing `GET /api/catalogos/<key>` to delegate to `catalogos_service.get_catalogo()`; remove inline `CREATE TABLE IF NOT EXISTS`
- [x] 2.2 Add `GET /api/catalogos` — calls `list_catalogos()`, returns success envelope with items list
- [x] 2.3 Add `POST /api/catalogos` — validate body, calls `create_catalogo()`, returns 201 on success, 409 on duplicate, 422 on non-array value
- [x] 2.4 Add `PUT /api/catalogos/<key>` — calls `update_catalogo()`, returns 404 if missing, 422 if non-array value
- [x] 2.5 Add `DELETE /api/catalogos/<key>` — calls `delete_catalogo()`, returns 200 on success, 409 with error if active rules block, 404 if missing
- [x] 2.6 Add `GET /api/catalogos/<key>/reglas` — calls `get_catalogo_reglas()`, returns 404 if catalog key not found
- [x] 2.7 Add `GET /admin/catalogos` in `reglas_admin.py` — same `react_shell.html` pattern, `entry_key = "src/pages/admin-catalogos/index.html"`, page title "Admin Catálogos"

## Phase 3: Frontend — Page + Components

- [x] 3.1 Create `frontend/src/pages/admin-catalogos/index.html` + `main.tsx` + register entry in `vite.config.ts` (`rollupOptions.input`)
- [x] 3.2 Add types `CatalogoListItem`, `CatalogoRow`, `ReglaRef`, `CreateCatalogoPayload` and CRUD functions to `frontend/src/lib/api-reglas.ts`
- [x] 3.3 Build `CatalogosTable` — key, descripción, dominio, value preview (truncated first 3 items), value_count badge, regla_count badge, action buttons (edit, delete, view rules)
- [x] 3.4 Build `CatalogoDialog` — create/edit modal form: key (disabled on edit), descripcion, dominio, tag input for value array; POST on create, PUT on edit
- [x] 3.5 Build `DeleteConfirmDialog` — show regla warning when rules ref the catalog; if 409 from server, display blocking rules inline
- [x] 3.6 Build `ReglasVinculadas` modal — table with regla_id, nombre, dominio badge, estado badge

## Phase 4: Tests — Service + API

- [x] 4.1 Service unit tests: create/read/update/delete catalog, duplicate key → ValueError, non-array value → ValueError, delete with active rules → ValueError, delete with no rules → success
- [x] 4.2 API integration tests in `tests/reglas/test_catalogos_api.py`: auth guard on all endpoints, 201 on create, 409 on duplicate, 200 on list/get/put, 422 on non-array, 409 on delete-with-active-rules, 200 on delete-with-no-rules, 200 on delete-with-draft-only, 404 on missing
