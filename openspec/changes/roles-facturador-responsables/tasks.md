# Tasks: Roles Facturador y Responsables Dinámicos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~130–170 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Store Layer

- [x] 1.1 Expand rol validation in `users_store.update_user()` — accept `"medico"` and `"facturador"` alongside `"admin"`, `"usuario"`; update error message to list all 4
- [x] 1.2 Add `users_store.get_facturadores()` — filter by `rol=="facturador"`, compose `nombre_completo` from `primer_nombre + apellido_1`, exclude entries missing `primer_nombre`
- [x] 1.3 Add tests for `get_facturadores()`: returns only facturadores, excludes without primer_nombre, returns `[]` when none exist

## Phase 2: Backend API + Service

- [x] 2.1 Add `GET /api/users/facturadores` endpoint in `auth.py` with `@login_requerido`; response follows standard `{status, data: {facturadores: [...]}, errors: []}` format
- [x] 2.2 Rewire `control_errores_service.get_opciones()` — pull `responsables` and `responsables_nombres_completos` from `get_facturadores()`, fallback to `ERROR_RESPONSABLE_URGENCIAS` / `RESPONSABLE_NOMBRES_COMPLETOS` when empty
- [x] 2.3 Add tests for `get_opciones()`: dynamic from facturadores, fallback when `[]`, same response shape preserved

## Phase 3: Frontend

- [x] 3.1 Add `"medico"` and `"facturador"` `<option>` to role `<select>` in `frontend/src/pages/usuarios/page.tsx` (both create form and edit modal)
- [x] 3.2 Add `useEffect` fetch to `/api/users/facturadores` on mount in `frontend/src/pages/abiertas-urgencias/page.tsx`; store facturadores list in state; use hardcoded `NOMBRE_MAP` as fallback

## Phase 4: Verification

- [x] 4.1 Run full test suite: `python -m pytest -v` — verify no regressions on existing rol tests and new scenarios pass
- [x] 4.2 Manual check: admin can create/edit user with rol "medico" and "facturador"; filter dropdown in control-errores shows dynamic facturadores
