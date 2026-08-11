# Tasks: DB Engine Intra-Row Optimizations

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~170 (145–185) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Foundation (enable optimizations)

- [x] 1.1 Create `tests/engine/test_engine_perf_optimizations.py` with three TDD (RED) test classes: exception caching, lazy date.edad, NO_MATCH skip. Use mock SQLAlchemy sessions/collectors.
- [x] 1.2 Refactor `app/services/engine/exception_handler.py` — extract `query_exceptions(rule, session)` returning `list[Excepcion]`. Update `apply_exceptions()` to accept the cached list via new param `cached_exc`.
- [x] 1.3 Add `tree_uses_field(tree: dict, field_name: str) -> bool` to `app/services/engine/condition_evaluator.py`. Recursively walk `_children`, check `fuente_datos` on atomic nodes.

## Phase 2: Core Optimizations (GREEN — make RED tests pass)

- [x] 2.1 Implement exception caching in `engine.py` `evaluate_sheet()` — call `query_exceptions()` once before the row loop, pass cached list to `apply_exceptions()`. Skip per-row query.
- [x] 2.2 Implement lazy date.edad in `engine.py` — after `build_tree()`, call `tree_uses_field()` for `date.edad` and `date.edad_meses`. Set booleans. Guard `_resolve_computed()` inside row loop with those flags.
- [x] 2.3 Implement NO_MATCH evidence skip in `engine.py` — wrap `collector.record()` call with `if final_outcome != "NO_MATCH"`.

## Phase 3: Verification

- [x] 3.1 Run `python -m pytest tests/engine/test_engine_perf_optimizations.py -v` — all 8 TDD tests GREEN.
- [x] 3.2 Run `python -m pytest tests/engine/ -v` — full test suite, confirm zero regressions (597 passed).
- [x] 3.3 Run snapshot tests: `python -m pytest tests/engine/test_snapshot_legacy_vs_engine.py -v` — identical output before/after (4 passed, included in 3.2).
- [x] 3.4 Feature flags noted: optimizations are always-on (no toggles). Snapshots confirmed identical without flags.
