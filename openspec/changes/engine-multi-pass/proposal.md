# Proposal: Engine Multi-Pass Aggregation

## Intent

Extend the rule engine's GroupEvaluator with set-based aggregation and cross-row evaluators to replicate 3 legacy detectors (`sala_observacion`, `detect_duplicados_base`, `duplicados_farmacia`). All changes are additive — existing evaluators, aggregations, rules, and tests are unaffected.

## Scope

### In Scope
- 2 new aggregation functions: `collect_set`, `collect_value_counts`
- 3 new evaluator operators: `set_contains_all`, `set_intersects`, `all_values_match`
- 3 new DB rules: sala_observacion mandatory codes, SOAT prohibited codes, detect_duplicados_base pair counting
- R13 extension in `motor-reglas` spec for new aggregation types
- Set serialization for evidence (convert set → list at output)
- Snapshot parity tests for engine-vs-legacy on both detectors

### Out of Scope
- `collect_boolean` / `any_match` aggregation (covered by `collect_set` + set evaluators)
- Two-phase evaluation engine refactor (Approach B — deferred)
- Compound evaluator monoliths (Approach C — rejected)
- New spec-level capabilities (existing `motor-reglas` spec extended, not replaced)

## Capabilities

> Contract between proposal and specs phases. The `sdd-spec` agent reads this to know which spec files to create or update.

### New Capabilities
None — this is an engine extension, not a new user-facing capability.

### Modified Capabilities
- `motor-reglas` — R13 (Group-By Evaluator) extended: supports `collect_set(field)` and `collect_value_counts(field1, field2)` aggregation functions; evaluator operators `set_contains_all`, `set_intersects`, `all_values_match` added to the engine's comparison vocabulary.

## Approach

Extend existing GroupEvaluator lifecycle (pre-scan → aggregate → evaluate) with 2 new aggregation functions in `_build_group_data()` and 3 new evaluator classes in `EVALUATOR_REGISTRY`. All registrations are additive — no existing code or tests change. DB rules created via data migrations referencing the new operator names. Engine plumbing (`engine.py`, `providers.py`) gets minor updates for group-level data resolution.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/group_evaluator.py` | Modified (+60 lines) | `_build_group_data()`: add `collect_set`, `collect_value_counts` branches |
| `app/services/engine/evaluators.py` | Modified (+90 lines) | Register `SetContainsAll`, `SetIntersects`, `AllValuesMatch` evaluators |
| `app/services/engine/providers.py` | Modified (+10 lines) | Register `group` provider prefix for group-level data resolution |
| `app/services/urgencias/` | New rules | DB migration for sala_observacion cross-row rules |
| `app/services/transversales/` | New rules | DB migration for detect_duplicados_generico pair-counting rule |
| `tests/engine/` | New (+100 lines) | Snapshot parity tests: engine vs legacy for both detectors |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Set serialization for evidence snapshots | Med | Convert `set` to `list` at `_build_group_data()` output; sets are Python-native, not JSON-serializable |
| Condition tree complexity for sala_obs (15+ atomic nodes) | Low | Document each rule's AND/OR tree in migration comments; reuse existing builder |
| Regression in existing group-by rules | Low | All changes additive; existing tests unchanged, new tests are additional |

## Rollback Plan

1. **Feature flag**: `USE_RULE_ENGINE=false` reverts all rules to legacy code. No code revert needed.
2. **DB rules**: Set erroneous rules to `estado=draft` — excluded from engine evaluation.
3. **Code revert**: All changes are additive — revert the single PR.

## Dependencies

- DB schema supports new `Condicion.operador` values (`set_contains_all`, `set_intersects`, `all_values_match`).
- Rule `parametros` JSONB supports `aggregations` array with new function names.
- `detect_all.py` already has `is_rule_engine_enabled()` gate — no plumbing changes needed.

## Success Criteria

- [ ] `collect_set` returns all unique non-None values of a field per group
- [ ] `collect_value_counts` returns correct `(field1, field2) → count` per group
- [ ] `set_contains_all(group_set, expected)` returns True iff group_set ⊇ expected_set
- [ ] `set_intersects(group_set, reference)` returns True iff group_set ∩ reference_set ≠ ∅
- [ ] `all_values_match(pair_counts, min_count)` returns True iff ALL pairs have count ≥ min_count
- [ ] Engine rules match legacy `sala_observacion` output (cross-row portion) — snapshot test
- [ ] Engine rules match legacy `detect_duplicados_base` output (pair-counting) — snapshot test
- [ ] All existing group-by tests (`revision_cantidad`, `doble_tipo_procedimiento`) remain green
