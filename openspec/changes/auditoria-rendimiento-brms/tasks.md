# Tasks: Auditoría de Rendimiento BRMS

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~590 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Engine) → PR 3 (Wiring + DB) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | RowStore + SessionManager + tests | PR 1 | base=main; independent foundation |
| 2 | Engine refactor (engine.py, group_eval, rule_based_detector) + engine test | PR 2 | base=main; depends on PR 1 types but no code coupling |
| 3 | 3× detect_all.py + exporter.py wiring + DB indexes + migration | PR 3 | base=main; depends on PR 1 + PR 2 |

## Phase 1: Foundation — RowStore + SessionManager

- [x] 1.1 RED: Write `test_row_store.py` — `build_row_store()` from 2D list + indices, edge cases
- [x] 1.2 GREEN: Create `row_store.py` — `build_row_store()` + `row_from_dict()`
- [ ] 1.3 RED: Write `test_session_manager.py` — enter/exit, savepoint, rollback on error
- [ ] 1.4 GREEN: Create `session_manager.py` — `SessionManager` context manager + savepoint helper

## Phase 2: Core Engine Refactor

- [ ] 2.1 RED: Write `test_engine_rows_path.py` — same data, old vs new path → identical output
- [ ] 2.2 GREEN: Modify `engine.py` — `evaluate_sheet()` accepts `rows: list[dict] | None`, `evidence_collector: EvidenceCollector | None`
- [ ] 2.3 GREEN: Modify `group_evaluator.py` — `build_groups()` accepts `rows: list[dict]` overload
- [ ] 2.4 GREEN: Modify `rule_based_detector.py` — `detect()` passes `rows` to engine when available

## Phase 3: Integration Wiring

- [ ] 3.1 GREEN: Modify `evidence_collector.py` — add `domain` param to `__init__` for logging
- [ ] 3.2 GREEN: Modify 3× `detect_all.py` — wrap in `SessionManager()`, domain-level `EvidenceCollector`, flush once
- [ ] 3.3 GREEN: Modify `exporter.py` — build `RowStore` from Polars data, pass to downstream detectors

## Phase 4: Database Indexes

- [ ] 4.1 GREEN: Modify `models.py` — add `__table_args__` for 3 composite indexes
- [ ] 4.2 GREEN: Create `migrations/005_add_performance_indexes.sql` — `CREATE INDEX CONCURRENTLY`
- [ ] 4.3 Verify: Run integration + snapshot tests, check output identical before/after
