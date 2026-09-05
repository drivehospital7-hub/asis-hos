# Tasks: migrar-sala-obs — Replace SalaObservacionEvaluator with Condition Tree

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~330 (130 new SQL + 180 new tests + 20 modified) |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: seeds + SQL migration; PR 2: deprecations + tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Catalogos + OR tree SQL | PR 1 | base = main; data-only |
| 2 | Deprecation + equivalence tests | PR 2 | base = main; needs PR 1 for test data |

## Phase 1: Seeds + SQL Migration

- [x] 1.1 Create `seed/migracion-engine/16_sala_observacion_condiciones.sql`: INSERT 2 catalogos (`sala_codes`, `entidades_ess`) + DELETE old conditions + INSERT OR tree for `sala_observacion_valido` v1
- [x] 1.2 OR tree: 6 AND sub-rules — SOAT >6h (38114), SOAT 2-6h (38915), non-SOAT ESS >6h (05DSB01), non-SOAT non-ESS >6h (129B02), non-SOAT 2-6h (5DSB01), ≤2h (5DSB01 ← bug fix)
- [x] 1.3 Leaf operators: `date.horas` (provider), `cat_in` for catalogos, `gt`/`gte`/`lte` for hours, `eq` + NOT for code mismatch

## Phase 2: Deprecation

- [x] 2.1 In `evaluators.py`: add `DeprecationWarning` to `SalaObservacionEvaluator.evaluate()`; remove from `_register_builtins()`
- [x] 2.2 In `sala_observacion.py`: add module-level `DeprecationWarning`

## Phase 3: Equivalence Tests

- [x] 3.1 Create `tests/engine/test_sala_obs_tree.py`: mock context with `sala_codes` + `entidades_ess`, `_run_legacy(sala_obs_check)`, `_run_tree(conditions)`, `_assert(legacy, tree, expected)` helper
- [x] 3.2 Build in-memory tree matching seed SQL (6 AND sub-rules)
- [x] 3.3 Tests per sub-rule: SOAT >6h, SOAT 2-6h, non-SOAT ESS >6h, non-SOAT non-ESS >6h, non-SOAT 2-6h — 2 cases each (MATCH + NO_MATCH)
- [x] 3.4 Bug-fix: ≤2h + code ≠ 5DSB01 → tree MATCH (legacy NO_MATCH — expected delta)
- [x] 3.5 Bug-fix: ≤2h + code = 5DSB01 → both NO_MATCH
- [x] 3.6 Edge cases: null dates, non-Urgencias tipo, empty code

## Files Affected

| File | Action | Est. Lines |
|------|--------|------------|
| `seed/migracion-engine/16_sala_observacion_condiciones.sql` | Create | ~130 |
| `app/services/engine/evaluators.py` | Modify | ~15 |
| `app/services/urgencias/sala_observacion.py` | Modify | ~3 |
| `tests/engine/test_sala_obs_tree.py` | Create | ~290 |

## Acceptance Criteria

- [x] Seed SQL inserts `sala_codes` (`["5DSB01","05DSB01","129B02","38114","38915"]`) and `entidades_ess` (`["ESS118","ESSC18"]`) catalogos
- [x] OR tree of 6 AND sub-rules in `condiciones`, DELETE old atomic condition
- [x] `SalaObservacionEvaluator` emits `DeprecationWarning` and is removed from `_register_builtins()`
- [x] `sala_observacion.py` emits module-level `DeprecationWarning`
- [x] Equivalence tests pass: `pytest tests/engine/test_sala_obs_tree.py -v`
- [x] Tree matches evaluator for all sub-rules EXCEPT ≤2h bug fix (tree adds detection)
- [x] 5DSB01 is correct code for ≤2h — no false positive when code = 5DSB01
