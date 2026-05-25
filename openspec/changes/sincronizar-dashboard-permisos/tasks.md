# Tasks: Sincronizar Dashboard con Permisos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~90–130 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | PR | Notes |
|------|------|----|-------|
| 1 | All 5 tasks | Single PR | Under 200 lines, no chain needed |

## Phase 1: Foundation

- [ ] **1.1** `app/constants/base.py` — Add `DASHBOARD_AREAS` constant (list of 6 area dicts: title, slug, permiso, href, tone, pending_label, description) and `_filter_areas(permisos: list[str]) -> list[dict]` helper (admin `"*"` returns all, otherwise filter by `a["permiso"] in permisos`, each gets `pending: 0`).

## Phase 2: Backend Implementation

- [ ] **2.1** `app/routes/home.py` — Import `DASHBOARD_AREAS` and `_filter_areas` from constants. Replace hardcoded `areas` list (41-44) with `_filter_areas(session.get("permisos", []))`. Remove fake pending counts.

- [ ] **2.2** `app/routes/derechos.py` — Import `permiso_requerido` from `app.utils.auth`. Add `@permiso_requerido("derechos")` between `@derechos_bp.get("/derechos")` and `def derechos_react()`.

## Phase 3: Frontend

- [ ] **3.1** `frontend/src/pages/index/page.tsx` — Remove hardcoded `areas` fallback array (lines 45–70). Replace with `const areas: IndexArea[] = initialData?.areas ?? [];`

## Phase 4: Testing

- [ ] **4.1** `tests/services/test_react_frontend.py` — Add class `TestDashboardPermisos`: unit tests for `_filter_areas` (single match, admin `"*"` returns 6, empty `[]` returns 0, unmatched permiso returns 0).

- [ ] **4.2** Same file — Integration test: admin (`"*"`) sees all 6 areas in /dashboard HTML.

- [ ] **4.3** Same file — Integration test: user with only `"odontologia"` sees 1 area in /dashboard HTML.

- [ ] **4.4** Same file — Integration test: user without `"derechos"` receives 403 on GET /derechos; user with `"derechos"` receives 200.

## Dependency Graph

```
Phase 1 (T1: base.py) ──┬── Phase 2 (T2: home.py)
                         └── Phase 2 (T3: derechos.py)  ← independent, no dep on T1
Phase 3 (T4: page.tsx)   ← independent, no deps
Phase 4 (T5: tests)      ← depends on T1, T2, T3
```

T3 and T4 have zero dependencies — could run first. T4 is purely frontend. T5 must run last.
