# Proposal: Control-errores-table-description-dominance

## Intent

Description column on `/control-errores` is squeezed by rigid widths (13%) and a shared `max-width:150px` that also caps Factura. The facturador editor popup hardcodes 300×120px instead of matching the cell like the global editor already does.

## Scope

### In Scope
- Redistribute column widths so Description dominates (~30%+), Factura stays compact (~8%)
- Remove `max-width:150px` from Description; add `max-width:120px` to Factura only
- Change facturador editor from hardcoded 300×120 to dynamic `rect.width/height`

### Out of Scope
- Editor save/close/keyboard behavior
- Readonly tooltip (`showObservacionReadOnly`) — already dynamic
- Mobile breakpoints, table wrapper `max-width:70rem`
- Backend or API changes

## Capabilities

### New Capabilities
None — pure UI improvement, no new spec-level behavior.

### Modified Capabilities
None — existing `control_errores` spec requirements unchanged.

## Approach

**CSS columns** (`control_errores.css` lines 245-250):
- Validador: 10% → 8%
- Factura: 10% → 8%
- Creado: 11% → 9%
- Categoría: auto (unchanged)
- Descripción: 13% → 35% (or `minmax(25%, 1fr)` via min-width)
- Facturador Cierra: 8% (unchanged)
- Pendiente: 8% → 7%
- Acciones: auto (unchanged)

**CSS max-width** (same file, line 738-745):
- Remove `max-width:150px` from `.editable-cell[data-type="text"]` — let column width govern Description
- Add `.editable-cell[data-field="factura"] { max-width: 120px }` — keep Factura narrow

**JS facturador editor** (`control_errores.html` lines 499-502):
- Replace `width: '300px'` → `width: rect.width + 'px'`
- Replace `height: '120px'` / `minHeight: '120px'` → `height: rect.height + 'px'`
- Same pattern as `openEditor()` (lines 722-724)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/static/css/legacy/control_errores.css` | Modified | Column widths (L245-250), max-width on text cells (L738-745), add Factura-specific rule |
| `app/templates/control_errores.html` | Modified | `openFacturadorEditorImpl()` width/height (L499-502) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Description wraps awkwardly on short content | Low | Use `min-width` fallback on th, test with real data |
| Factura loses max-width cap | Low | Add Factura-specific rule BEFORE removing generic one |
| Facturador editor mispositions if button layout is unusual | Low | Use `rect` from `<td>` parent, not the icon button itself |

## Rollback Plan

Single-commit change — `git revert` the commit restores all 3 CSS rules + 3 JS lines.

## Dependencies

None.

## Success Criteria

- [ ] Description column ~3× wider than Factura with long content
- [ ] Factura stays compact (~120px max)
- [ ] Facturador editor matches cell size, not hardcoded 300×120
- [ ] All editors open, save, and close correctly — no regression
