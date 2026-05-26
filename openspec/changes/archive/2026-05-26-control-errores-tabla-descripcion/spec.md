# Spec: Control-errores-table-description-dominance

## Purpose

Redistribute `/control-errores` table column widths so the Description column dominates (~35%), Factura stays compact (~120px max), and the facturador editor popup matches cell size dynamically instead of hardcoding 300×120px.

## Requirements

### R1: Column widths redistribute to Description dominance

The table header percentage widths MUST be redistributed so Description occupies ~35%, Factura stays at 8%, and remaining columns shrink proportionally.

| Column            | Original | Implementado |
|-------------------|----------|-------------|
| Validador (th:1)  | 10%      | 6%          |
| Factura (th:2)    | 10%      | 8%          |
| Creado (th:3)     | 11%      | 8%          |
| Categoría (th:4)  | auto     | 11%         |
| Descripción (th:5)| 13%      | **36%**     |
| Responsable (th:6)| 8%       | **15%**     |
| Pendiente (th:7)  | 8%       | 6%          |
| Acciones (th:8)   | auto     | 10%         |

#### Scenario: Description column renders at ~36% width

- GIVEN the control-errores table is rendered with typical data
- WHEN the table loads
- THEN the Description column (th:nth-child(5)) MUST occupy ~36% of table width
- AND Factura (th:nth-child(2)) MUST occupy ~8%

#### Scenario: Remaining columns have explicit widths

- GIVEN the percentage widths are applied
- WHEN the table renders
- THEN Validador MUST be 6%, Creado MUST be 8%, Categoría MUST be 11%
- AND Responsable MUST be 15%, Pendiente MUST be 6%, Acciones MUST be 10%

### R2: Factura has bounded max-width

Factura cells MUST NOT exceed 120px width regardless of content length. The global `max-width: 150px` on `.editable-cell[data-type="text"]` MUST be removed so it no longer caps Description.

#### Scenario: Long Factura values are truncated

- GIVEN a factura cell with a value exceeding 120px rendered width
- WHEN the cell renders
- THEN the cell content MUST be truncated with ellipsis
- AND the cell width MUST NOT exceed 120px

#### Scenario: Description column is not capped by max-width

- GIVEN a description cell with content wider than 150px
- WHEN the cell renders
- THEN the cell MAY expand beyond 150px
- AND the column width (35%) MUST govern the available space
- AND the global max-width:150px rule MUST NOT apply

### R3: Facturador editor matches cell size dynamically

The `openFacturadorEditorImpl()` function MUST set editor width and height from `rect.width` and `rect.height` (via `getBoundingClientRect()`) instead of hardcoded `300px` and `120px`. This MUST match the pattern already used by `openEditor()`.

#### Scenario: Facturador editor opens at cell dimensions

- GIVEN a facturador cell is clicked to edit
- WHEN the editor opens
- THEN `editor.style.width` MUST equal `rect.width + 'px'`
- AND `editor.style.height` MUST equal `rect.height + 'px'`
- AND `editor.style.minHeight` MUST NOT be set to `'120px'`

#### Scenario: Facturador editor handles deep-nested button layout

- GIVEN the edit button is nested in a `<td>` with unusual padding
- WHEN `getBoundingClientRect()` is called on the button
- THEN the editor MUST use the button's `rect.width` and `rect.height` for sizing
- AND the editor MUST still position at `btn.getBoundingClientRect()` coordinates (no regression)

## Constraints

- CSS changes are in `app/static/css/legacy/control_errores.css` only
- JS changes are in `app/templates/control_errores.html` only (within `openFacturadorEditorImpl`)
- The Factura max-width rule MUST be added BEFORE the generic `max-width:150px` removal to avoid a gap where Factura has no cap
- No backend, API, or database changes
- The table wrapper `max-width: 70rem` is out of scope

## Acceptance Criteria

- [ ] `th:nth-child(5)` (Descripción) width is 36%
- [ ] All 8 columns have explicit widths summing to 100% (6/8/8/11/36/15/6/10)
- [ ] `.editable-cell[data-field="factura"]` has `max-width: 120px`
- [ ] `.editable-cell[data-type="text"]` no longer has `max-width: 150px`
- [ ] `editor.style.width` uses `Math.max(260, rect.width) + 'px'`
- [ ] `editor.style.height` uses `Math.max(90, rect.height) + 'px'`
- [ ] Headers don't overlap — `<th>` has `overflow: hidden; text-overflow: ellipsis`
- [ ] Facturador editors open, display content, and close correctly — no regression vs global editor
