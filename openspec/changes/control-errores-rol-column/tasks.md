# Tasks: Añadir columna Rol a control-errores y ensanchar la tabla

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 80–110 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full change: service + frontend + CSS + tests | PR 1 | Single PR, all changes depend on each other; no benefit in splitting |

## Phase 1: Service Layer

- [x] 1.1 **`app/services/control_errores_service.py`** — In `get_errores()`, after `listar_errores()`, build `rol_map = {f["nombre_completo"]: f["rol"] for f in get_facturadores()}` and inject `error["responsable_rol"] = rol_map.get(error.get("responsable", ""), "-")` for each error
- [x] 1.2 **Defensive fallback** — Handle `get_facturadores()` returning `[]` (skip map build, set all to `"-"`) and facturador dicts missing `"rol"` key via `.get("rol", "-")`

## Phase 2: Frontend + CSS

- [x] 2.1 **`app/templates/control_errores.html` — Table header + colspans** — Add `<th>Rol</th>` between Responsable and Pendiente (column 7). Update all 4 `colspan="8"` → `colspan="9"` (lines 104, 376, 396, 1256)
- [x] 2.2 **Render functions: `renderTable()`, `renderFilteredTable()`, `addNewRow()`** — Add `<td>${escapeHtml(e.responsable_rol || '-')}</td>` at column 7 in each row builder (after Responsable, before Estado/Pendiente)
- [x] 2.3 **CSV export `exportToCSV()`** — Insert `'Rol'` at position 6 (index) in headers array and `e.responsable_rol || ''` at matching position in row builder (after Responsable, before Observación del Facturador)
- [x] 2.4 **`app/static/css/legacy/control_errores.css` — Column widths** — `nth-child(5)`: 36%→30%, `nth-child(6)`: 15%→10%; add `nth-child(7)`: 8% (ROL); shift old `nth-child(7)`→`nth-child(8)`, `nth-child(8)`→`nth-child(9)`

## Phase 3: Tests

- [x] 3.1 **`tests/services/test_control_errores_service.py`** — Unit test: patch `listar_errores` + `get_facturadores`, assert `responsable_rol` matches mapped role for each error
- [x] 3.2 **Fallback tests** — Patch `get_facturadores` → `[]`, assert all errors get `"-"`. Patch with facturador missing `"rol"` key, assert `"-"` fallback
- [x] 3.3 **`tests/services/test_control_errores_integration.py`** — Integration test: GET `/api/control-errores` with mocked storage, assert every error dict in response contains `responsable_rol`
