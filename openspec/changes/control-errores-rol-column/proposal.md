# Proposal: Añadir columna Rol a control-errores y ensanchar la tabla

## Intent

The control-errores dashboard shows the responsible user's name but not their role (e.g., "facturador", "medico"). Operators need the role visible to quickly assess assignments without cross-referencing users. The table also needs to be wider to accommodate the extra column.

## Scope

### In Scope
- Enrich `get_errores()` in service layer: inject `responsable_rol` from `get_facturadores()` role map (same pattern as `imagenes_count`)
- Add "Rol" column to JS rendering functions: `renderTable()`, `renderFilteredTable()`, `addNewRow()`
- Update 5 hardcoded `colspan="8"` → `colspan="9"` (empty-state, new-row, export)
- Sync CSV export header and row builder with new column order
- Adjust CSS column widths: Descripción 36%→30%, Responsable 15%→10%, new Rol at 8%
- Tests: unit test for rol enrichment, integration test for rol in GET response

### Out of Scope
- Schema changes or data migration (rol enriched dynamically)
- Backend role CRUD or user management changes
- Other new columns or table restyling beyond width adjustment

## Capabilities

### New Capabilities
- `error-control-dashboard`: Table rendering and CSV export for the control-errores page — column definitions, dynamic enrichment, responsive width layout

### Modified Capabilities
- `control_errores`: R10 colspan requirement SHALL change from `8` to `9`; Validador remains first `<th>`; new Rol column added

## Approach

Service-layer enrichment (Approach 1 from exploration): `get_errores()` builds a `nombre_completo → rol` map from `get_facturadores()` and injects `responsable_rol` into each error dict. No JSON storage change. Frontend reads `e.responsable_rol`, displays `-` fallback. CSS frees 11% total width from Descripción and Responsable columns, allocates 8% to new Rol column. Same `overflow-x: auto` wrapper handles overflow.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/control_errores_service.py` | Modified | `get_errores()` injects `responsable_rol` |
| `app/templates/control_errores.html` | Modified | New column in 3 render funcs, colspans 8→9, CSV sync |
| `app/static/css/legacy/control_errores.css` | Modified | nth-child(9) added; widths 6-9 adjusted |
| `tests/services/test_control_errores_service.py` | Modified | Unit test for rol enrichment |
| `tests/services/test_control_errores_integration.py` | Modified | Integration test for GET response |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fallback empty roles (no facturadores) | Low | UI shows `-` gracefully |
| Missed `colspan="8"` in template | Low | Grep for all `colspan="8"` in template before/after |
| CSV column order desync | Low | Keep header array and row builder adjacent in code |

## Rollback Plan

Revert the 5 modified files. No schema migration or data changes to undo — rollback is idempotent.

## Dependencies

None.

## Success Criteria

- [ ] Rol column renders for every error, populated from `get_facturadores()`
- [ ] Empty rol displays `-` (not blank or error)
- [ ] All `colspan="8"` updated to `colspan="9"` — no broken table cells
- [ ] CSV export includes Rol column with correct data order
- [ ] Existing tests pass, new tests cover enrichment logic
