# Tasks: HAZLO E INTEGRAKO — Visual Catalog Management UI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~560 (9 files touched, tests included) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend infra + endpoint; PR 2: Frontend + tests |
| Delivery strategy | exception-ok |
| Chain strategy | single-pr |

Decision needed before apply: Yes (resolved: exception-ok)
Chained PRs recommended: Yes (waived via size:exception)
Chain strategy: single-pr (single PR with size:exception exception)
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: blueprint + relationship endpoint | PR 1 | Standalone, testable via curl/client |
| 2 | Frontend: catalog page + 3 tabs + tests | PR 2 | Depends on PR 1 for endpoint to exist |

## Phase 1: Backend Foundation

- [x] 1.1 Create `app/routes/catalogo.py` — Blueprint `catalogo_bp` with `GET /catalogo` rendering react_shell for `pages/catalogo/index.html`, protected by `@admin_requerido`
- [x] 1.2 Register `catalogo_bp` in `app/__init__.py` (no url_prefix — route is `/catalogo`)
- [x] 1.3 Add `GET /api/eps/<int:id>/procedimientos` in `notas_api.py` — SQLAlchemy chain EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento with joinedload, returns JSON per design contract

## Phase 2: Frontend Foundation

- [x] 2.1 Create `frontend/src/pages/catalogo/index.html` — entry HTML mirroring `usuarios/index.html`, title "Catálogos · Hospital Orito"
- [x] 2.2 Create `frontend/src/pages/catalogo/main.tsx` — `createRoot` + `<AppLayout>` wrapping `<CatalogoPage />`
- [x] 2.3 Create `frontend/src/lib/api-catalogo.ts` — typed fetch wrapper: `fetchEps()`, `fetchProcSqlite()`, `fetchProcPg()`, plus CRUD helpers per entity, with error handling

## Phase 3: Core Frontend — Catalog Page

- [x] 3.1 Create `frontend/src/pages/catalogo/page.tsx` — main page component with 3-tab structure (EpsContratado / Procedimiento CUPS / Tarifas PostgreSQL), each tab with `useState`+`useEffect` data fetch, table render, and create/edit/delete modals
- [x] 3.2 Add `GetProcedimientosPorEps` action column in EpsContratado tab — fetch `GET /api/eps/<id>/procedimientos` and show results in read-only overlay
- [x] 3.3 Wire EPS selector dropdown in PostgreSQL tab — fetch `GET /procedimientos/eps` on mount, filter table by selected EPS

## Phase 4: Integration Wiring

- [x] 4.1 Add `src/pages/catalogo/index.html` to `vite.config.ts` rollupOptions.input
- [x] 4.2 Add `{ label: "Catálogos", href: "/catalogo", icon: BookType, permiso: "*" }` in `app-sidebar.tsx` ALL_NAV array

## Phase 5: Testing

- [x] 5.1 Integration test: Flask test client `GET /catalogo` returns 200 with admin session
- [x] 5.2 Integration test: `GET /api/eps/1/procedimientos` returns JSON with error shape for unknown EPS
- [x] 5.3 Unit tests: relationship query logic (get_procedimientos_por_eps) via eps_contratado_crud
- [x] 5.4 Frontend test: API client unit tests (16 tests covering all CRUD endpoints)
- [x] 5.5 Run all existing tests to verify no regressions (595 passed, 9 pre-existing failures unchanged)
- [x] 5.6 Vite build succeeds with catalogo entry point (verified build)
