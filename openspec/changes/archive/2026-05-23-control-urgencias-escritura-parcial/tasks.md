# Tasks: Control Urgencias — Escritura Parcial

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Decision needed before apply | No |

## Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend permission logic | Single PR | Route + service, coupled |
| 2 | Frontend JS guards | Same PR | Independent, but same atomic change |
| 3 | Tests | Same PR | RED phase for TDD |

## Phase 1: Backend Permission Logic

- [x] 1.1 `app/routes/control_errores.py:81` — Change PUT decorator `:write` → `control_urgencias`; add tuple handling at line 85 branching on `isinstance(result, tuple)`
- [x] 1.2 `app/services/control_errores_service.py:109-122` — Replace `session.get("ce_authenticated")` with `session.get("permisos", [])` checking for `"*"` or `"control_urgencias:write"`; return 403 tuple with prohibited field list on partial-write violations

## Phase 2: Frontend JS Guards

- [x] 2.1 `handleCellClick` (line 1671) + `openEditor` (line 1787) — Replace `ceAuth.isAuth()` with `_canWrite`; restrict editable fields for partial-write to `{estado, observacion_facturador}`; observacion/factura show read-only tooltip for `!_canWrite`
- [x] 2.2 Mutation guards (lines 2166, 2245, 2392, 2873) — `addNewRow`, `deleteError`, `exportToCSV`, `openCargaMasiva`: replace guard with `if (!window._canWrite) return;`
- [x] 2.3 Image modal (lines 2480, 2532, 2548) — `openImageModal`, `uploadImages`, `deleteImage`: replace `ceAuth.isAuth()` with `_canWrite`; dropzone/delete buttons visibility tied to `_canWrite`
- [x] 2.4 `_renderPdfThumb` (lines 2469, 2496) — Image delete button `&times;` visibility gated on `_canWrite` instead of `authed` param from `ceAuth.isAuth()`

## Phase 3: Tests (TDD: RED first)

- [x] 3.1 `tests/services/test_control_errores_service.py` — Unit test `update_error()` with 9 scenarios covering all permission types (admin `*`, `:write`, partial-write allowed/prohibited fields, legacy flag regression)
- [x] 3.2 Integration test — Flask test client `PUT /api/control-errores/<id>` with mocked session asserting 200 vs 403 + response body field names
- [x] 3.3 Regression test — Verify auditor/admin (`:write` / `*`) maintain full field update capability without regression (included in 3.1 and 3.2)

## Implementation Order

1. **Write tests first** (RED — Phase 3) to define expected behavior
2. **Backend** (Phase 1) — both tasks are coupled: tuple handling requires decorator change and service change to work together
3. **Frontend** (Phase 2) — independent, but part of same atomic change; all 4 tasks can be done in any order
4. **Final TDD cycle** — run tests (GREEN), verify integration

Dependencies: 1.1 + 1.2 must ship together. Phase 2 independent of Phase 1 (JS guards are UX-only, backend is authoritative). Tests reference `update_error()` so they come first (TDD) but can also validate after implementation.
