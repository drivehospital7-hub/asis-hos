# Tasks: Engine Multi-Pass Aggregation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~470 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Phase 1 + T3.1-3) → PR 2 (Phases 2 + T3.4-5 + 4.1) |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Engine core + evaluator unit tests | PR 1 | Base=main. ~265 lines. Aggregations, evaluators, GroupProvider plus T3.1-3. |
| 2 | Seeds, wiring, integration tests | PR 2 | Base=main. ~205 lines. Migrations, detect_all wiring, T3.4-5, T4.1. |

## Phase 1: Engine Extensions

- [x] 1.1 group_evaluator.py: Add `_agg_collect_set()` — iterate rows, collect unique non-None values → list
- [x] 1.2 group_evaluator.py: Add `_agg_collect_value_counts()` — count (f1,f2) pairs → list-of-dicts
- [x] 1.3 group_evaluator.py: Wire both in `_build_group_data()` switch for `"collect_set"` and `"collect_value_counts"`
- [x] 1.4 evaluators.py: Create `SetContainsAllEvaluator` — `set(row_value) ⊇ set(expected)`, operator=`set_contains_all`
- [x] 1.5 evaluators.py: Create `SetIntersectsEvaluator` — `set(row_value) ∩ set(expected) ≠ ∅`, operator=`set_intersects`
- [x] 1.6 evaluators.py: Create `AllValuesMatchEvaluator` — all entries have `count >= threshold`, operator=`all_values_match`
- [x] 1.7 evaluators.py: Register all 3 in `_register_builtins()`
- [x] 1.8 providers.py: Create `GroupProvider(prefix="group")` — resolves `group.{field}` → `context.invoice_data.get(field)`, register in `PROVIDER_REGISTRY`

## Phase 2: Seeds + Rules (blocked — see notes)

- [ ] 2.1 Create migration `add_sala_obs_rules.py` — BLOCKED: no Alembic migration infrastructure exists; requires DB setup
- [ ] 2.2 Create migration `add_duplicados_base_rule.py` — BLOCKED: same as 2.1
- [ ] 2.3 urgencias/detect_all.py: Wire sala_obs rules — BLOCKED: requires DB rules (2.1) to exist first
- [ ] 2.4 transversales/: Wire `detect_duplicados_base_generico` — BLOCKED: requires DB rules (2.2) to exist first

## Phase 3: Testing

- [x] 3.1 test_evaluators.py: Add `TestSetContainsAllEvaluator` — empty set, partial overlap, full contain, wrong types (7 tests)
- [x] 3.2 test_evaluators.py: Add `TestSetIntersectsEvaluator` — no intersect, partial intersect, empty ref, None row_value (7 tests)
- [x] 3.3 test_evaluators.py: Add `TestAllValuesMatchEvaluator` — all ≥ threshold, some below, empty list, None threshold (7 tests)
- [x] 3.4 test_group_evaluator.py: Add collect_set integration tests — single/multi groups, nulls, list output; collect_value_counts — pair counting, list-of-dicts format (7 tests)
- [x] 3.5 test_snapshot_legacy_vs_engine.py: Add snapshot parity tests — engine group-by with set_intersects/set_contains_all and collect_value_counts/all_values_match (2 tests)

## Phase 4: Integration

- [x] 4.1 Update `tasks.md` with completion marks after all tasks done
