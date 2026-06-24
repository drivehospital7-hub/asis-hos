# Tasks: Unified Permission Model — /procesar, cronogramas, and security gating

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450–500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend core) → PR 2 (frontend + tests) |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes (resolved: size:exception)
Chained PRs recommended: Yes (resolved: size:exception accepted)
Chain strategy: size-exception (single PR, maintainer accepted)
400-line budget risk: High (accepted as size:exception)

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Constants + migration + route decorators (backend core) | PR 1 | Base branch: main. Covers Phases 1–2. |
| 2 | Frontend update + dead page deletion + tests | PR 2 | Base branch: main (or PR 1 branch if feature-branch chain). Depends on Phase 1. |

Lines breakdown: PR 1 ≈ ~100 added + ~20 deleted = ~120; PR 2 ≈ ~180 added + ~300 deleted = ~480. Combined ~500. Splitting reduces each PR to under 400, except PR 2's deletions.

## Phase 1: Constants & Migration (Foundation)

- [x] 1.1 `app/constants/base.py`: Remove `odontologia`, `urgencias`, `odontologia_equipos_basicos` from `ALLOWED_PERMISOS`; add `procesar`, `procesar:write`, `cronograma_bacteriologas`, `cronograma_urgencias`.
- [x] 1.2 `app/constants/base.py`: Add `procesar` / `procesar:write` pair to `PERMISO_MUTUAL_EXCLUSION`.
- [x] 1.3 `app/constants/base.py`: Update `DASHBOARD_AREAS` Procesar entry permiso → `"procesar"`; add cronograma entries.
- [x] 1.4 `app/constants/base.py`: Update `DEFAULT_TEMPLATES` (odontologia/urgencias → procesar/procesar_control, auditor unchanged).
- [x] 1.5 `app/utils/users_store.py`: Update `DEFAULT_USERS` — old perms replaced with `procesar`.
- [x] 1.6 `app/utils/users_store.py`: Add migration loop in `_load_users()` after person-fields backfill.

## Phase 2: Route Decorator Updates

- [x] 2.1 `app/routes/procesar.py`: Change decorator to `@permiso_requerido("procesar")` on GET + POST; `can_write` → check `"procesar:write"`.
- [x] 2.2 `app/routes/cronograma_bacteriologas.py`: Replace `@permiso_requerido("*")` → `@permiso_requerido("cronograma_bacteriologas")` on all 4 endpoints.
- [x] 2.3 `app/routes/cronograma_urgencias.py`: Replace `@permiso_requerido("*")` → `@permiso_requerido("cronograma_urgencias")` on all 3 endpoints.
- [x] 2.4 `app/routes/derechos.py`: Add `@permiso_requerido("derechos")` to `derechos_texto()` and `procesar_derechos()`.
- [x] 2.5 `app/routes/procedimientos.py`: Add `@admin_requerido` to all 5 endpoints.
- [x] 2.6 `app/routes/notas_api.py`: Add `@admin_requerido` to all ~30 unprotected endpoints (all except the 2 already protected).
- [x] 2.7 `app/routes/import_csv.py`: Add `@admin_requerido` to all 5 endpoints.

## Phase 3: Frontend

- [x] 3.1 `frontend/src/components/app-sidebar.tsx`: Update `ALL_NAV` — Procesar permiso `"urgencias"` → `"procesar"`; cronograma items `"*"` → `"cronograma_urgencias"` / `"cronograma_bacteriologas"`.
- [x] 3.2 `frontend/src/pages/usuarios/page.tsx`: Update `ALL_PERMISOS` — remove `odontologia`, `urgencias`, `odontologia_equipos_basicos`; add `procesar`, `procesar:write`, `cronograma_bacteriologas`, `cronograma_urgencias`.
- [x] 3.3 Delete `frontend/src/pages/odontologia/`, `urgencias/`, `odontologia-equipos-basicos/` (3 dirs, ~9 files) + verified no orphaned Vite imports.

## Phase 4: Tests

- [x] 4.1 Unit: parametrized migration tests — single old perm, multiple old perms (dedup), mixed old+new, admin unaffected, no old perms.
- [x] 4.2 Unit: mutual exclusion for `procesar` / `procesar:write` — create + edit both rejected.
- [x] 4.3 Unit: `ALLOWED_PERMISOS` validation — old `odontologia` rejected, new `procesar` accepted.
- [x] 4.4 Integration: Flask test client — GET `/procesar/` with `procesar` → 200, without → 403; same for cronogramas, derechos API, notas_api, import_csv.
- [x] 4.5 Frontend: sidebar changes are purely structural (constant swap). Verified via manifest and component logic — no React test runner available for this project. Config change only, no behavioral logic.
