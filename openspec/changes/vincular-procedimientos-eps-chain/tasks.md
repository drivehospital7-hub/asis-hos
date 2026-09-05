# Tasks: Vincular Procedimientos a EPS (cadena SQLite)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 350–420 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend (service + route + CRUD fix + tests) | PR 1 | ~160 lines; base = main; tests prove atomicity |
| 2 | Frontend (API client + UI components + tests) | PR 2 | ~200 lines; depends on PR 1 API contract |

Backend and frontend are separable as long as the API contract from design.md is stable.

## Phase 1: Backend — Service & Route

- [x] 1.1 Create `app/services/vincular_procedimiento_service.py` — function `ejecutar()` with manual SQLAlchemy transaction (`try: commit / except: rollback`); validates EPS, NotaHoja, Procedimiento existence, checks EpsNota duplicate, creates EpsNota + NotasTecnicas atomically
- [x] 1.2 Add route `POST /api/eps/<int:eps_id>/vincular-procedimiento` in `app/routes/notas_api.py` — validates `{ id_nota_hoja, id_procedimiento, tarifa }`, delegates to service, returns 201/400/404 per spec
- [x] 1.3 Add `"id_nota_hoja"` to the dict in `app/services/eps_contratado_crud.py:get_procedimientos_por_eps()` — extract `nh.id` from the join result

## Phase 2: Frontend — API Client

- [x] 2.1 In `frontend/src/lib/api-catalogo.ts`: add `NotaHoja` interface, `fetchNotasHoja()` (GET /api/notas-hoja), `vincularProcedimiento(epsId, data)` (POST /api/eps/{id}/vincular-procedimiento), and `id_nota_hoja` field to `EpsProcedimientosChain.procedimientos[]` item type

## Phase 3: Frontend — UI Components

- [x] 3.1 Add `NotaHojaTab` component in `frontend/src/pages/catalogo/page.tsx` — CRUD table + modal for single-field `nota`, registers as 4th tab "Notas Hoja" (SQLite), replicates existing tab pattern
- [x] 3.2 Add formulario vincular at bottom of "Ver Procedimientos" modal: two `<select>` dropdowns (NotaHoja, Procedimiento loaded on modal open), tarifa `<input type="number">`, "Vincular" button, inline validation + toast feedback

## Phase 4: Testing

- [x] 4.1 Create `tests/services/test_vincular_procedimiento.py` — integration tests covering: happy path (201 + both rows created), duplicate EpsNota (400), missing fields (400), bad tarifa (400), EPS not found (404), nonexistent entities (400), auth (401)
- [x] 4.2 Add frontend tests in `frontend/src/pages/catalogo/__tests__/api-catalogo.test.ts` — mock fetch for `fetchNotasHoja` (GET), `createNotaHoja`, `updateNotaHoja`, `deleteNotaHoja`, `vincularProcedimiento` (POST)
- [x] 4.3 Run full test suite (backend + frontend); fix any regressions — 613 passed backend, 59 passed frontend. 0 regressions.
