# Proposal: CUPS Equivalentes — Intramural

## Intent

Add CUPS equivalentes validation for Intramural: flag rows where `Código` = "906317" (should be "1906317", Hepatitis B rápida) or "906249" (should be "906249PR", VIH Prueba rápida). These are data entry errors where the operator writes an incorrect CUPS code instead of the valid equivalent.

## Scope

### In Scope
- New detector `app/services/intramural/cups_equivalentes.py` following Urgencias pattern
- Constants dict `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL` in `app/constants/intramural.py`
- Wire into `_get_intramural_detectors()` and `detect_all_problems_intramural()`
- Replace empty placeholders in `problemas["cups_equivalentes"]` and `totales["cups_equivalentes"]`

### Out of Scope
- No changes to non-Intramural domains (Urgencias cups_equivalentes stays as-is)
- No changes to CODIGOS_EXCLUIDOS_VACUNACION — coexists with this rule
- No CUPS validation beyond these two mappings

## Capabilities

### New Capabilities
- `cups-equivalentes-intramural`: detect incorrect CUPS codes 906317 and 906249 in Intramural rows and suggest the correct equivalent

### Modified Capabilities
- None (pure additive, no spec-level behavior changes)

## Approach

1. Add `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL = {"906317": "1906317", "906249": "906249PR"}` to constants
2. Create `detect_cups_equivalentes_intramural()` mirroring Urgencias' `detect_cups_equivalentes()` — iterate rows, match `codigo` against dict keys, emit `{"factura", "codigo", "codigo_equiv", "accion", "procedimiento"}`
3. Register in `_get_intramural_detectors()`, call in `detect_all_problems_intramural()`, populate the existing placeholders

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/intramural.py` | Modified | Add `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL` dict |
| `app/services/intramural/cups_equivalentes.py` | **New** | Detector function |
| `app/services/intramural/detect_all.py` | Modified | Import, register, and wire the new detector |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 906249 is already in CODIGOS_EXCLUIDOS_VACUNACION | Low | Different detection contexts (centro_costo vs cups_equivalentes) — coexists without conflict |
| 906317 not in CODIGOS_PYM_RUTAS but 1906317 is | None | Rule only flags the error, doesn't validate the replacement |
| Conflict with Urgencias cups_equivalentes | None | Filtered by Tipo Factura = "Intramural" — different domain |

## Rollback Plan

Revert the 3 file changes — remove the constant dict, delete the detector file, and unwire from detect_all.py.

## Dependencies

None.

## Success Criteria

- [ ] 906317 flagged with action "Usar 1906317" when detected in Intramural rows
- [ ] 906249 flagged with action "Usar 906249PR" when detected in Intramural rows
- [ ] Existing Urgencias cups_equivalentes tests pass unaffected
- [ ] Empty placeholders replaced with real data
