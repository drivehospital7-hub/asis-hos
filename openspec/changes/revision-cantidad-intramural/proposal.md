# Proposal: Revisión Cantidad Intramural

## Intent

Add a new detector to flag Intramural rows with anomalously high `Cantidad` values that require manual review. This brings the `⚠️ Revisión Necesaria` pattern (already present in Urgencias) to Intramural, using thresholds specific to the area.

## Scope

### In Scope
- New detector `detect_revision_cantidad_intramural()` with 3 rules
- Constants in `app/constants/intramural.py` for all thresholds
- Registration in `app/services/intramural/detect_all.py` under `"⚠️ Revisión Necesaria"`
- Unit tests + integration test

### Out of Scope
- Changes to `tipo_factura_registry.py`, `unified_processor.py`, or `normalized_rows.py` — all already dispatch Intramural correctly
- Exento / límite-específico tables — not needed for v1
- Modifying the Urgencias `revision_cantidad.py` detector

## Capabilities

### New Capabilities
- `revision-cantidad-intramural`: detects anomalously high `Cantidad` values in Intramural rows using thresholds (02+Lab=No→≤2, 03/04→≤12, general→≤1). Flags items for human review, not as definitive errors.

### Modified Capabilities
None — pure new detector following the established pattern.

## Approach

Follow the same architecture as `app/services/urgencias/revision_cantidad.py`: iterate rows, apply rule cascade (02+Lab=No → 03/04 → general), collect items under `"⚠️ Revisión Necesaria"`. Intramural does not need a `Tipo Factura` filter since the caller already dispatches by area. Lower thresholds than Urgencias (2/12/1 vs 2/20/1).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/intramural.py` | Modified | Add threshold constants |
| `app/services/intramural/revision_cantidad_intramural.py` | New | Detector with rule cascade |
| `app/services/intramural/detect_all.py` | Modified | Import, call, error_groups |
| `tests/services/intramural/test_revision_cantidad_intramural.py` | New | Unit tests |
| `tests/services/test_intramural_detect_all.py` | Modified | Integration test |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Threshold mismatch with business | Medium | Flag as review, not error — human decides |
| Collision with existing review filters | Low | Same `"⚠️ Revisión Necesaria"` key; rows are additive |

## Rollback Plan

Revert the single commit: remove import + call from `detect_all.py`, delete detector file, revert constants.

## Dependencies

None — all pipeline infra already supports Intramural.

## Success Criteria

- [ ] Detector applies all 3 rules correctly on known test data
- [ ] Items appear under `"⚠️ Revisión Necesaria"` in output
- [ ] All existing tests pass without modification
