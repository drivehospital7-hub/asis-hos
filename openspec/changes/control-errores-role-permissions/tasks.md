# Tasks: Permisos Granulares por Roles en Control-Errores

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Base |
|------|------|-----------|------|
| 1 | `created_by` field, auditor role, permission helpers + unit tests | PR 1 | feature/control-errores-role-permissions |
| 2 | Role filtering, ownership checks, create validation + integration tests | PR 2 | PR 1 branch |
| 3 | Per-record flags, frontend guards, médico dropdown + integration tests | PR 3 | PR 2 branch |

## Phase 1: Foundation (PR 1)

- [x] 1.1 Add `created_by=""` param to `crear_error()` in `app/utils/errores_storage.py`; store in record dict
- [x] 1.2 Add `"auditor"` to allowed roles in `update_user()` at `app/utils/users_store.py:331`
- [x] 1.3 (RED) Test `_resolve_effective_role()` — parametrized: admin/*, usuario/:write, facturador, medico, read
- [x] 1.4 (GREEN) Implement `_resolve_effective_role()` in `app/services/control_errores_service.py`
- [x] 1.5 (RED) Test `_can_edit()` — per-role: admin/auditor/write always, facturador médico/own, medico self-only, legacy None
- [x] 1.6 (GREEN) Implement `_can_edit(record, effective_role, username)` per PM3
- [x] 1.7 (RED) Test `_can_delete()` — deny facturador/médico/read; allow admin/auditor/write
- [x] 1.8 (GREEN) Implement `_can_delete(record, effective_role)` per PM3
- [x] 1.9 (RED) Test `_can_create_for()` — facturador only médico; others any
- [x] 1.10 (GREEN) Implement `_can_create_for(target_rol, effective_role)` per PM4

## Phase 2: Core Permissions (PR 2)

- [x] 2.1 Update `add_error()`: set `created_by=session["username"]`; strip from client payload per PM2
- [x] 2.2 Add facturador create gate in `add_error()`: resolve responsable_rol; 403 on non-médico per R14/PM4
- [x] 2.3 Refactor service functions to accept session dict as param (testability); update routes in `app/routes/control_errores.py`
- [x] 2.4 Update `get_errores()`: role-based filter per R13/PM1; add per-record `can_edit`/`can_delete` flags per PM6
- [x] 2.5 Update `update_error()`: `_can_edit()` gate before field-level check; facturador full-write on médico records per R1
- [x] 2.6 Update `delete_error()`: `_can_delete()` gate; 403 for facturador/médico per R16/PM3
- [x] 2.7 (INTEGRATION) Test: GET filtered per 5 roles, POST facturador blocked on non-médico, PUT ownership denied, DELETE 403

## Phase 3: Frontend (PR 3)

- [x] 3.1 Replace `window._canWrite` with `window._userRole` + `window._username` in `control_errores.html:2211`
- [x] 3.2 Update `renderRow()` / `renderFilteredTable()`: attach `data-can-edit`/`data-can-delete` from per-record API flags
- [x] 3.3 Update `updateDisabledState()`: gate by role + per-record flags instead of single `_canWrite`
- [x] 3.4 Guard `addNewRow()`: médico early-return (R15); facturador shows médico-only responsable dropdown (R14)
- [x] 3.5 Guard `deleteError()`: médico blocked; facturador checks `can_delete` flag per R5/R16
- [x] 3.6 Guard `exportToCSV()`/`openCargaMasiva()`: block non-write roles (facturador/médico)
- [x] 3.7 Replace remaining `window._canWrite` refs (15 occurrences): image upload/delete, modal rendering
- [x] 3.8 (INTEGRATION) Test: template injection, per-record API flags — 6 new tests, 124/124 passing

## Phase 4: Verification

- [ ] 4.1 Test: legacy records (no `created_by`) — facturador allowed on médico-assigned; blocked on non-médico per PM5
- [ ] 4.2 Test: auditor full access (same as admin/write) per R2/PM2
- [ ] 4.3 Run `python -m pytest -v` full suite; fix regressions in existing test fixtures (add session role fields)
- [ ] 4.4 Smoke test: login per role (admin, auditor, facturador, médico), verify filtering, CRUD, UI guards
