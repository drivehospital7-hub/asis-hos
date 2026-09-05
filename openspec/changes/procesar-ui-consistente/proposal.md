# Proposal: /procesar UI Consistency — Handler Standardization

## Intent

24 handlers across two files produce inconsistent `descripcion`/`procedimiento`/`detalle` columns when fed engine-enriched dicts. 3 P0 handlers (ruta_duplicada, cantidades_urgencias, duplicados_farmacia) produce broken rows. Standardize all handlers to a consistent pattern and add a generic fallback.

## Scope

### In Scope
- Standardize all 24 handlers to consistent pattern (descripcion→problema, procedimiento→_build_procedimiento, detalle→specific value)
- Add generic fallback: when procedimiento and detalle are both empty, use first non-factura key
- Fix P0 handlers: ruta_duplicada, cantidades_urgencias, duplicados_farmacia
- Preserve per-type specific descriptions in detalle
- Snapshot tests comparing legacy vs engine per handler

### Out of Scope
- /procesar React page changes (already renders the columns correctly)
- Engine enrichment changes (row data already present)
- Evidence display changes
- Group-by sparse output (no migrated group-by rules exist yet)

## Capabilities

### New Capabilities
None — pure internal refactor, no spec-level behavior changes.

### Modified Capabilities
None — the /procesar endpoint contract (R1–R4) and column semantics are unchanged.

## Approach

1. **Standardize procedimiento**: replace ad-hoc assignments with `_build_procedimiento(codigo, procedimiento)`. Remove hardcoded strings and column headers.
2. **Standardize detalle**: each handler computes its domain-specific value from available keys. Replace legacy key names with canonical engine keys.
3. **Standardize descripcion**: always `item.get("problema", "")` with domain-specific fallback text when empty.
4. **Generic fallback**: if procedimiento AND detalle are still empty after handler logic, use the first non-factura key:value as detalle.
5. **Fix P0s**:
   - ruta_duplicada: use `identificacion` as detalle when `facturas`/`cantidad` absent
   - cantidades_urgencias: use `problema` for descripcion when `cantidad_esperada` absent
   - duplicados_farmacia: use available fields, skip missing nested structures
6. **Test**: snapshot tests per handler — engine-enriched dict input → compare output fields

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/odontologia/normalized_rows.py` | Modified | 13 handlers in `build_odontologia_normalized_rows()` |
| `app/services/normalized_rows.py` | Modified | 11 handlers in `build_normalized_rows()` |
| `tests/` (new file) | New | Snapshot tests per handler |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy data still uses old dict format | Low | `isinstance(item, dict)` check preserved; legacy path unchanged |
| Generic fallback hides real issues | Low | Only fires when all handlers produce empty; includes debug log |
| Engine row keys vary by Excel sheet version | Medium | Test each handler against real engine output before deploying |

## Rollback Plan

Revert both `normalized_rows.py` files to their current state. Both are pure data transformations (dict→dict), so rollback is a simple file revert. No DB, schema, or frontend changes involved.

## Dependencies

None.

## Success Criteria

- [ ] All 24 handlers produce correct descripcion/procedimiento/detalle with engine-enriched input
- [ ] P0 handlers produce valid (non-broken) rows with engine data
- [ ] Generic fallback fires only when procedimiento and detalle are both empty
- [ ] Snapshot tests pass for all 24 handlers (legacy + engine paths)
- [ ] Existing pytest suite passes with no regressions
