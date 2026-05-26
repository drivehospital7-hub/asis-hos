# Proposal: Reordenar Tabla de Resultados

## Intent

Remove dead "Acción" column (Controlar button) from results table in all 3 areas, and add "Fec. Factura" as first column so users can validate invoice dates inline.

## Scope

### In Scope
- Delete "Acción" column from React frontend (odontología, urgencias, equipos básicos)
- Add "Fec. Factura" as first column in same 3 tables
- Extract `fec_factura` from raw sheet in each `detect_all.py` (same pattern as `responsable_cierra`)
- Pass `fec_factura` per row to frontend via normalized rows + JSON response

### Out of Scope
- Excel export sheets (CruceFacturas/Revisión) unchanged
- No new detection features or detector changes
- No spec-level behavior changes

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — existing specs (`odontologia-equipos-basicos`, `control_errores`) don't specify table column layout in the React results view.

## Approach

Follow existing `responsable_cierra` pattern:

1. **`detect_all.py` (3 files)**: Scan raw sheet building `{factura: fec_factura}` map
2. **`normalized_rows.py` (2 files)**: Accept `fec_factura_map` param, add `fec_factura` to every row
3. **Routes (3 files)**: Include `fec_factura` in `all_items`, prepend `"Fec. Factura"` to `columnas`
4. **React pages (3 files)**: Remove `<th>Acción</th>` + `<td><Button>Controlar</Button></td>`; add `<th>Fec. Factura</th>` first, render `item.fec_factura`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/*/detect_all.py` (3) | Modified | Build `fec_factura_map`; pass to normalized_rows |
| `app/services/*/normalized_rows.py` (2) | Modified | Accept map, emit `fec_factura` per row |
| `app/routes/{excel_headers,urgencias,odontologia_equipos_basicos}.py` | Modified | JSON + columnas update |
| `frontend/src/pages/{odontologia,urgencias,odontologia-equipos-basicos}/page.tsx` | Modified | Remove Acción, add Fec. Factura first |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `fec_factura` missing in some Excel files | Med | Empty string fallback — no crash |
| Column count mismatch backend vs frontend | Low | Verify `columnas` length equals `<th>` count in review |

## Rollback Plan

```bash
git checkout -- frontend/src/pages/*/page.tsx
git checkout -- app/routes/excel_headers.py app/routes/urgencias.py app/routes/odontologia_equipos_basicos.py
git checkout -- app/services/*/detect_all.py app/services/*/normalized_rows.py
pytest -v
```

## Dependencies

None.

## Success Criteria

- [ ] "Controlar" button absent from all 3 tables
- [ ] "Fec. Factura" is first column in all 3 tables
- [ ] Each row shows its invoice date (or empty if unavailable)
- [ ] `pytest -v` passes with no regressions
- [ ] "Acción" column absent from JSON response in all 3 routes
