# Proposal: Migrate `cups_sin_contrato` to DB Rule Engine

## Intent

Replace the simplified engine rule (catalog-only `exists_in_db` check) with a full `CupsContratadoEvaluator` that reproduces the legacy detector's multi-table JOIN + exception chain. This makes the engine version functionally equivalent to the 267-line legacy Python detector, unblocking full engine migration for the transversal domain.

## Scope

### In Scope
- New `CupsContratadoEvaluator(AtomicEvaluator)` with operator `"cups_contratado"` in `app/services/engine/evaluators.py`
- Pre-loads 4 DB datasets on first evaluate() (same JOIN chain as legacy)
- Handles all 6 exception branches internally (farmacia skip, urgencias nota_hoja 1/27, CAP+ESS118, CAP+EPSS41, codigo_equiv fallback, FEV autorizado)
- Returns `True` when CUPS IS properly contracted (NOT inverts to MATCH)
- Update seed SQL condition tree: `NOT(cups_contratado(invoice.codigo, ...))`
- Remove legacy `detect_cups_sin_contrato` from `procedimiento_contratado.py`
- Port test scenarios to engine test framework

### Out of Scope
- Changes to `detect_all.py` files (rule name `"cups_sin_contrato"` unchanged, feature flag pattern unchanged)
- Spec-level behavior changes (identical output to legacy)
- Refactoring of `FACTURADORES_URGENCIAS` or `_ENTIDADES_NOTA_URGENCIAS` constants
- DB schema changes

## Capabilities

### New Capabilities
None — pure implementation change. Behavior is identical to the legacy detector.

### Modified Capabilities
None — no spec-level behavior changes. The `motor-reglas` spec already defines the evaluator extension mechanism (R8 Catalog Provider, R15 exists_in_db). The new evaluator uses the same `AtomicEvaluator` contract.

## Approach

Single `CupsContratadoEvaluator` (compound evaluator, ~150-200 lines) registered as operator `"cups_contratado"`:

1. **First-call pre-load**: Query the 5-table JOIN (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`) to build `pares_validos: set[tuple[str,str]]`. Also pre-load `nota_urgencias_cups`, `nota_cap_cups`, and `eps_map`. Cache in `self.*` attributes.

2. **Per-row evaluate()**: Read `codigo` from `row_value`, `codigo_entidad_cobrar` + `tarifario` + `responsable_cierra` + `codigo_equiv` from `context.invoice_data`. Apply the same 6-branch exception chain as the legacy detector.

3. **Condition tree**: Root `NOT(cups_contratado(invoice.codigo, ...))` — evaluator returns True when contracted, NOT inverts to MATCH.

4. **Seed SQL**: Replace current `NOT(exists_in_db(...))` with the new tree referencing `cups_contratado` operator.

5. **Legacy removal**: Replace `detect_cups_sin_contrato` body with a stub delegating to `RuleBasedDetector`, or remove entirely if engine is always on.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/evaluators.py` | New | `CupsContratadoEvaluator` + register in `_register_builtins()` |
| `seed/phase7/insert_procedimiento_contratado.sql` | Modified | Replace condition tree with `cups_contratado` operator |
| `app/services/transversales/procedimiento_contratado.py` | Removed | Legacy `detect_cups_sin_contrato` deleted or stubbed |
| `tests/services/test_detect_cups_sin_contrato.py` | Removed | ~1000-line legacy tests, replaced by engine tests |
| `tests/engine/test_snapshot_phase7_cross_ref.py` | Modified | Add scenarios covering exception chain |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Evaluator bloat (~200 lines) | High | Internal helpers per exception block (same pattern as `CentroCostoCheckEvaluator`) |
| Test coverage gap | Med | Port 30+ legacy scenarios to engine test framework; snapshot-compare output |
| Cache staleness mid-session | Low | Same risk as legacy — acceptable for batch processing |
| Evaluator error crashes pipeline | Low | try/except in evaluate() returns False (fails open) |

## Rollback Plan

1. Revert seed SQL to the original `NOT(exists_in_db(...))` condition tree.
2. Revert `evaluators.py` — remove the new evaluator and its registry entry.
3. Restore `procedimiento_contratado.py` from git.
4. Feature flag `USE_RULE_ENGINE=false` reverts all domains to legacy anyway.

## Dependencies

- None — all DB tables and constants already exist and are used by the legacy detector.

## Success Criteria

- [ ] Engine evaluator produces identical output to legacy detector for all 30+ test scenarios (snapshot test)
- [ ] All exception branches produce correct results: farmacia skip, urgencias nota_hoja, CAP+ESS118, CAP+EPSS41, codigo_equiv fallback, FEV autorizado
- [ ] All existing tests pass (`python -m pytest -v`)
- [ ] Seed SQL idempotent — re-running does not duplicate rows
