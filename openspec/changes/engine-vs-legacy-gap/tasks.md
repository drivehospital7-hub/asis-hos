# Tasks: Engine Micro-Optimizations

> Change: engine-vs-legacy-gap | TDD: Strict | Test runner: pytest

---

## Phase 1: Pre-resolve providers/evaluators at tree-build time

### 1.1 RED — Test `build_tree()` attaches `_provider`/`_evaluator`

- [x] Write `test_build_tree_attaches_provider_and_evaluator` — verifies atomic nodes get `_provider` and `_evaluator` keys after `build_tree()`
- [x] Write `test_cached_provider_evaluator_used_in_fast_eval` — mock provider/evaluator on node, verify `_evaluate_fast()` uses cached instead of calling `get_provider()` / `get_evaluator()`
- [x] Write `test_fallback_to_dynamic_lookup` — node without `_provider` still works via dynamic lookup fallback

### 1.2 GREEN — Implement caching in `build_tree()`

- [x] Walk tree in `build_tree()`: attach `_provider` and `_evaluator` to each atomic node
- [x] Update `_evaluate_fast()` to use `node.get("_provider")` / `node.get("_evaluator")` with fallback
- [x] Update `_evaluate_atomic()` similarly

### 1.3 REFACTOR — Clean up

- [x] Extract walk-tree logic to private helper `_pre_resolve_tree()`
- [x] Ensure composite nodes also get `_provider`/`_evaluator = None` (explicit is better)

---

## Phase 2: Eliminate redundant EvaluationContext + dict copy

### 2.1 RED — Test `apply_exceptions()` accepts dict directly

- [x] Write `test_apply_exceptions_accepts_row_data_dict` — call with `row_data=dict(...)`, verify scope matching and skip detection
- [x] Write `test_apply_exceptions_row_data_does_not_match` — verify no match when scope differs
- [x] Write `test_apply_exceptions_empty_scope_matches_all` — empty scope matches all rows

### 2.2 GREEN — Modify `apply_exceptions()` + engine.py

- [x] Modify `apply_exceptions()` to accept `row_data: dict` (in addition to `context: EvaluationContext`)
- [x] In engine.py line ~140: pass `row_data` directly to `apply_exceptions()` instead of creating `ctx`
- [x] In engine.py line ~155: when `params` is empty `{}`, reuse `row_data` directly (skip `{**row_data}`)

### 2.3 REFACTOR — Clean up

- [x] Backward compat: existing callers using `context=` still work via `isinstance(context, dict)` check
- [x] Simplified variable names: `merged_data` replaces inline dict copy expression

---

## Phase 3: Two-phase evaluation in production

### 3.1 RED — Test fast path first, trace on demand

- [x] Write `test_fast_path_first_trace_only_for_match` — verify `_evaluate_fast` returns compact result (no trace)
- [x] Write `test_fast_path_no_trace_for_no_match` — verify fast path for no-match produces compact result
- [x] Write `test_collect_trace_false_uses_fast_path` — verify `collect_trace=False` delegates to fast path

### 3.2 GREEN — Implement two-phase eval

- [x] In engine.py evaluation loop: call `self._evaluator.evaluate(tree, eval_ctx, collect_trace=False)` first
- [x] If outcome is MATCH/ERROR AND `persist=True`: re-evaluate with `collect_trace=True`
- [x] If outcome is NO_MATCH: use fast result directly (skip second eval)
- [x] Fix: propagate error info in `_evaluate_fast` for missing provider/evaluator/exceptions

### 3.3 REFACTOR — Clean up

- [x] `_evaluate_fast` now returns `{"outcome": False, "error": "..."}` for error cases (was silent False)
- [x] `persist=False` path unchanged (already uses fast path)

---

## Review Workload Forecast

| File | Est. changed lines | Risk |
|---|---|---|
| `app/services/engine/condition_evaluator.py` | ~30 | Low |
| `app/services/engine/engine.py` | ~40 | Medium |
| `app/services/engine/exception_handler.py` | ~15 | Low |
| `tests/engine/test_engine_perf_optimizations.py` | ~80 | Low |
| **Total** | **~165** | — |

- 400-line budget risk: **Low** (~165 lines)
- Chained PRs recommended: **No**
- Single PR: ✅ safe
