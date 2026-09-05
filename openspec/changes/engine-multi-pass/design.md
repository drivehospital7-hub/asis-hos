# Design: Engine Multi-Pass Aggregation

## Technical Approach

Extend `GroupEvaluator._build_group_data()` with 2 new aggregation functions (`collect_set`, `collect_value_counts`), add 3 atomic evaluators to the registry, and register a `GroupProvider` to resolve `group.*` data paths. All changes are additive — no existing aggregations, evaluators, or rules are modified.

## Architecture Decisions

### Decision: `group.` provider prefix

| Option | Tradeoff |
|--------|----------|
| Use `invoice.` for group data (existing pattern) | Inconsistent semantics: `invoice.*` implies row-level, but group aggregates are not row-level |
| **Add `GroupProvider` with prefix `group`** | Clear semantics; new rules use `group.aggregate_name`; old group rules keep `invoice.*` (backward compat) |

**Choice**: Register `GroupProvider` with prefix `group`. It resolves `group.{field}` by looking up `context.invoice_data[{field}]` — same dict, different prefix.

### Decision: Set→List conversion at source

| Option | Tradeoff |
|--------|----------|
| Convert at evidence record time | Affects all evidence snapshots, not just group data |
| **Convert in `_build_group_data()` output** | Localized; `collect_set` stores `list` instead of `set` in `group_data`; evaluators work with lists too |

**Choice**: `collect_set` stores `list` from the start. Evaluators `set_contains_all`/`set_intersects` accept `list` as `row_value` (converted to `set` internally). Evidence snapshot serialization unchanged.

### Decision: `collect_value_counts` output format

| Option | Tradeoff |
|--------|----------|
| Dict of tuple→int | Not JSONB-serializable |
| **List of dicts** | JSONB-friendly; `[{"codigo":"X","cantidad":1,"count":2},...]` |

**Choice**: List of dicts with explicit `count` key. `AllValuesMatchEvaluator` iterates and checks `count >= threshold`.

## Data Flow

```
    Rule Evaluation Flow (group-by path):
    
    engine._evaluate_sheet_group_by()
         │
         ├─ GroupEvaluator.build_groups()       pre-scan: factura → [row numbers]
         │
         ├─ GroupEvaluator._build_group_data()   aggregate: compute collect_set /
         │    │                                   collect_value_counts per group
         │    │
         │    ├─ collect_set:  iterate rows → collect values → list(unique)
         │    └─ collect_value_counts: iterate rows → count (f1,f2) pairs → [dict...]
         │
         ├─ EvaluationContext(invoice_data=group_data)   group values at invoice_data level
         │    │
         │    ├─ invoice.* provider (legacy group rules)
         │    └─ group.* provider (new rules)            ← NEW
         │
         ├─ ConditionEvaluator.evaluate(tree, ctx)       recursive AND/OR/NOT
         │    │
         │    └─ AtomicEvaluator.evaluate()
         │         ├─ set_contains_all(list, expected)   ← NEW
         │         ├─ set_intersects(list, expected)      ← NEW
         │         └─ all_values_match(list, min_count)   ← NEW
         │
         ├─ EvidenceCollector.record(snapshot=group_data) data already serializable
         └─ Return detection results
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/group_evaluator.py` | Modify | Add `_agg_collect_set()`, `_agg_collect_value_counts()` — ~50 lines |
| `app/services/engine/evaluators.py` | Modify | Add 3 evaluator classes + register — ~70 lines |
| `app/services/engine/providers.py` | Modify | Add `GroupProvider` + register — ~15 lines |
| `migrations/versions/*_add_sala_obs_rules.py` | Create | DB migration: 3 new rules with conditions |
| `migrations/versions/*_add_duplicados_base_rule.py` | Create | DB migration: 1 new rule with conditions |
| `app/services/urgencias/detect_all.py` | Modify | Wire `sala_observacion_codigos_obligatorios` and `sala_observacion_prohibido_soat` via engine |
| `app/services/transversales/detect_all.py` (or equiv) | Modify | Wire `detect_duplicados_base_generico` via engine |
| `tests/engine/test_group_evaluator.py` | Modify | +4 integration tests for new aggregations |
| `tests/engine/test_evaluators.py` | Create | +8 unit tests for new evaluators |
| `tests/engine/test_snapshot_legacy_vs_engine.py` | Modify | +2 snapshot tests (sala_obs + duplicados_base) |

## Interfaces / Contracts

### New Aggregation Configs

```python
# collect_set config
{"function": "collect_set", "field": "codigo", "target": "collect_set_codigo"}
# → group_data["collect_set_codigo"] = ["5DSB01", "890701", ...]

# collect_value_counts config  
{"function": "collect_value_counts", "fields": ["codigo", "cantidad"], "target": "collect_value_counts"}
# → group_data["collect_value_counts"] = [{"codigo": "X", "cantidad": 1, "count": 2}, ...]
```

### New Evaluator Signatures

```python
# set_contains_all
evaluator.evaluate(node, row_value: list, expected: list, context) → bool
# True iff set(row_value) ⊇ set(expected)

# set_intersects
evaluator.evaluate(node, row_value: list, expected: list, context) → bool
# True iff set(row_value) ∩ set(expected) ≠ ∅

# all_values_match
evaluator.evaluate(node, row_value: list, expected: int, context) → bool  
# True iff all(row_value[i]["count"] >= expected)
```

### Rule Seed: sala_observacion_codigos_obligatorios

- **type**: group-by
- **parametros**: `[{"group_by": "factura", "function": "collect_set", "field": "codigo"}]`
- **condition**: `AND(set_intersects(group.collect_set_codigo, ["5DSB01","05DSB01","129B02"]), NOT(set_contains_all(group.collect_set_codigo, ["890701","890601"])))`

### Rule Seed: sala_observacion_prohibido_soat

- **type**: group-by (similar — checks for prohibited SOAT codes 38114/38915 without mandatory 39145/39131)

### Rule Seed: detect_duplicados_base_generico

- **type**: group-by
- **parametros**: `[{"group_by": "factura", "function": "collect_value_counts", "fields": ["codigo", "cantidad"]}]`
- **condition**: `all_values_match(group.collect_value_counts, 2)`

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit — SetContainsAllEvaluator | Empty set, partial overlap, full contain, wrong types | 3 tests |
| Unit — SetIntersectsEvaluator | No intersect, partial intersect, empty ref, None row_value | 3 tests |
| Unit — AllValuesMatchEvaluator | All ≥ threshold, some below, empty list, None/threshold edge | 4 tests |
| Integration — collect_set | Single/multi groups, with nulls, verify list output (not set) | 2 tests |
| Integration — collect_value_counts | Two-field counting, verify list-of-dicts output | 2 tests |
| Snapshot — sala_obs | Legacy `detect_sala_observacion` vs engine rules (same Excel) | 1 test |
| Snapshot — duplicados | Legacy `detect_duplicados_generico` vs engine rule (same Excel) | 1 test |

## Migration / Rollout

1. **Deploy code** (aggregations + evaluators + GroupProvider) — no behavior change without DB rules
2. **Add DB rules** via migration — set `estado = draft` initially
3. **Run snapshot parity tests** — if green, switch rules to `estado = active`
4. **Wire into detect_all.py** — engine path behind `is_rule_engine_enabled()` gate
5. **Rollback**: set rules to `estado = draft` → legacy code resumes

## Open Questions

- None. All technical decisions resolved by existing patterns.
