# Proposal: Close Engine vs Legacy Performance Gap

## Intent

After 8 rounds of optimization, the engine remains slower than legacy detectors. Three low-risk bottlenecks account for the remaining gap: (1) provider/evaluator registry lookups per atomic condition per row (~6.3M at 50K×21×3), (2) redundant EvaluationContext + dict copy per row (~2.1M instances), (3) trace dicts built for 95% of rows (NO_MATCH) then discarded.

## Scope

### In Scope
- Pre-resolve providers/evaluators at `build_tree()` — store in node dict
- Eliminate redundant EvaluationContext; skip `{**row_data}` copy when params empty
- Two-phase eval: fast path first, full trace only for MATCH/ERROR

### Out of Scope
- Row-major evaluation (21→1 row scans) — separate architectural change
- Consolidating `detect_all.py` to `evaluate_sheet_domain()` — enabler for future work
- Results dict template optimization — marginal gain for MATCH rows (~5%)
- Complex evaluator refactoring — separate per-evaluator effort

## Capabilities

### New Capabilities
None — pure performance optimization, no behavioral change.

### Modified Capabilities
None — no spec-level requirement changes.

## Approach

Three targeted, low-risk optimizations on the hot path:

1. **Pre-resolve in `build_tree()`**: Store `node["_provider"]` and `node["_evaluator"]` during tree construction. Providers/evaluators are stateless singletons — caching is safe. Eliminates 2 dict lookups + 2 function calls per atomic condition.

2. **Single EvaluationContext with conditional copy**: Pass `row_data` dict directly to `apply_exceptions()` (it only reads `invoice_data`). Create `EvaluationContext` once per row, only doing `{**row_data, **params}` when params are non-empty (most rules use `[{}]`). Cuts ~2.1M dataclass instantiations per run.

3. **Two-phase eval for production**: When `persist=True`, evaluate with `_evaluate_fast()` (no traces) first. Only re-evaluate with full traces for MATCH/ERROR rows (~5%). Eliminates ~3M trace dict allocations per run without changing evidence quality — same trace content, same code path, just deferred.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/condition_evaluator.py` | Modified | `build_tree()` stores `_provider`/`_evaluator` in node; atomic eval uses them |
| `app/services/engine/engine.py` | Modified | Single `EvaluationContext`, conditional copy, two-phase eval loop |
| `app/services/engine/exception_handler.py` | Modified | `apply_exceptions()` accepts `row_data: dict` instead of `EvaluationContext` |
| `tests/engine/test_engine_perf_optimizations.py` | Modified | Extend with tests for pre-resolved nodes, single ctx, two-phase eval |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cached provider/evaluator stale across runs | Low | Providers/evaluators are stateless singletons; registries don't change during a sheet evaluation |
| Double eval for MATCH rows produces different result | Low | Same `_evaluate_atomic` code path; pure functions, no side effects |
| Dict passed to `apply_exceptions()` mutated | Low | `row_data` is already never mutated in the loop; `_matches_scope` only reads |

## Rollback Plan

Revert to current state: (a) remove `_provider`/`_evaluator` from nodes in `build_tree()`, (b) restore second `EvaluationContext` instantiation in engine.py, (c) remove fast-first eval gate. All three are additive changes with no schema or data migrations.

## Dependencies

None. No DB schema changes, no config changes, no new dependencies.

## Success Criteria

- [ ] All existing engine tests pass (`pytest tests/engine/ -v`)
- [ ] `evaluate_sheet()` output identical for `persist=True` and `persist=False` (snapshot regression)
- [ ] New tests verify: pre-resolved nodes in `build_tree()` output, single context when params empty, two-phase eval only re-evaluates MATCH/ERROR
- [ ] Production mode wall-clock improvement measurable (expected: 1.5–2×)
