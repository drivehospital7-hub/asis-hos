# Tasks: Control-errores-table-description-dominance

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~14 |
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

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All ~14 lines in one commit | PR 1 | Single, tightly coupled — no split needed |

## Phase 1: CSS Column Width Redistribution

- [ ] **1.1** Update 6 `th:nth-child` percentage rules in `app/static/css/legacy/control_errores.css` L245-250: nth-child(1) 10→8%, (2) 10→8%, (3) 11→9%, (5) 13→35%, (6) 8% unchanged, (7) 8→7%. Keep (4) and (8) auto (no rule).
  - **Verify**: Inspect `<th>` elements in `/control-errores` — Description column at ~35%, Factura at 8%, remaining columns match spec.

## Phase 2: Max-width Fix (Remove Global, Add Factura-specific)

- [ ] **2.1** Remove `max-width: 150px` from `.editable-cell[data-type="text"]` rule at L738-745. Leave `white-space`, `overflow`, `text-overflow`, `height`, `line-height` intact.
  - **Verify**: Description cell with >30 chars no longer clipped at 150px.

- [ ] **2.2** Add new rule after L745: `.editable-cell[data-field="factura"], .new-row-cell[data-field="factura"] { max-width: 120px; }`
  - **Verify**: Long factura value (>15 chars) truncates with ellipsis at ~120px.

## Phase 3: JS Facturador Editor Dynamic Sizing

- [ ] **3.1** In `app/templates/control_errores.html` L489-502 (`openFacturadorEditorImpl`):
  - Rename `btn.getBoundingClientRect()` result to `btnRect` (used for positioning at L498-499)
  - Add `const rect = btn.closest('td').getBoundingClientRect();`
  - Change `editor.style.width` from `'300px'` to `rect.width + 'px'`
  - Change `editor.style.height` from `'120px'` to `rect.height + 'px'`
  - Change `editor.style.minHeight` from `'120px'` to `''`
  - **Verify**: Facturador editor opens at actions `<td>` dimensions, not hardcoded 300×120px.

## Phase 4: Verification

- [ ] **4.1** Manual checklist from design: column widths, max-width removed, factura capped, facturador editor sizing, global editor regression, new-row template.
- [ ] **4.2** Run app (`python run_dev.py`) and confirm no JS console errors on `/control-errores`.
