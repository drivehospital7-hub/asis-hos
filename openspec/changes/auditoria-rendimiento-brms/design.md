# Design: Auditoría de Rendimiento BRMS

## Technical Approach

Eliminate the O(R×N) openpyxl `cell()` bottleneck and O(R) DB session overhead by introducing a **facts-first RowStore**, **single session per domain**, and **deferred batch evidence**. Zero behavioral change — the engine's interface gets an optional `rows: list[dict]` parameter alongside the existing `Worksheet` path for backward compat.

---

## Architecture Decisions

### Decision 1: RowStore — `list[dict]` built from Polars

| Option | Tradeoff |
|--------|----------|
| **Chosen**: `list[dict]` built in `exporter.py` after Polars read | Matches `EvaluationContext.invoice_data` shape already expected by providers/evaluators. No new type. |
| Typed dataclass (`Row`) | Adds translation layer for no behavioral gain. Providers already use dict `.get()`. |
| `list[list]` (current `_SimpleSheet`) | Requires column index indirection everywhere. dict key access is O(1) and self-documenting. |

**Rationale**: The `InvoiceProvider` already resolves `invoice.{field}` via `context.invoice_data.get(field)`. A `list[dict]` row store means each row becomes `EvaluationContext.invoice_data` directly — no translation needed. Keys use existing `indices` dict keys (snake_case).

### Decision 2: Engine interface — new overload, not replacement

| Option | Tradeoff |
|--------|----------|
| **Chosen**: `evaluate_sheet()` accepts optional `rows: list[dict] \| None = None` | Backward compatible. Old callers pass nothing = old path. |
| New method `evaluate_rows()` | More explicit but duplicates logic. |
| Breaking signature change | Breaks `RuleBasedDetector.detect()` contract. |

**Rationale**: `RuleBasedDetector.detect()` is the integration point. Adding `rows` param means the detector can pass facts when available, else fall back. Internal refactor: `_build_row_context()` vs new `_get_row_from_dict()` — both produce the same `dict[str, Any]`.

### Decision 3: SessionManager — context manager + savepoints

**Choice**: `SessionManager` wraps `get_session()`, yields session to its block. Within the block, each rule evaluation gets a savepoint via `session.begin_nested()`. The outer commit is deferred to the very end.

**Rationale**: Preserves per-rule rollback (savepoints) while using a single DB connection. Matches current `detect_all.py` pattern but eliminates the open/close overhead.

```python
class SessionManager:
    def __enter__(self) -> Session: ...
    def __exit__(self, exc_type, ...) -> None:
        if exc_type: session.rollback()
        else: session.commit()
        session.close()
    def savepoint(self) -> contextmanager: ...
```

### Decision 4: Evidence batch — `EvidenceCollector` at domain scope

**Choice**: Lift `EvidenceCollector` instantiation to the domain `detect_all.py` level. One collector per domain receives all rules' evidence. `flush_batch(session)` called once at the end.

**Rationale**: Already designed for this — `EvidenceCollector` buffers in memory. The problem today is each `RuleBasedDetector` creates its own engine, which creates its own collector. Moving the collector to domain scope eliminates per-rule flushing.

### Decision 5: GroupEvaluator gets a `row_dict` overload

**Choice**: `GroupEvaluator.build_groups()` and `_build_group_data()` accept optional `rows: list[dict]`. When provided, all `data_sheet.cell()` calls are replaced with `rows[row-2][col_name]` dict lookups.

**Rationale**: Group-by rules (e.g., `ruta_duplicada`, `sala_obs_*`) are the most expensive per row. The conversion is mechanical: `data_sheet.cell(row, col_idx+1).value` → `rows[row-2][indices_reverse[col_name]]`.

---

## Data Flow

```
exporter.py                         detect_all.py                    engine/
    │                                    │                             │
    ├─ Polars.read_excel()               │                             │
    ├─ build RowStore (list[dict]) ──────┤                             │
    │                               │    │                             │
    │                    with SessionManager() as session:             │
    │                        │                                        │
    │                        ├─ collector = EvidenceCollector()        │
    │                        │    (domain-level)                       │
    │                        │                                        │
    │                        ├─ for each rule:                        │
    │                        │   ├─ savepoint()                       │
    │                        │   ├─ engine.evaluate_sheet(            │
    │                        │   │     rows=rowstore,                 │
    │                        │   │     evidence_collector=collector)   │
    │                        │   └─ savepoint rollback/commit         │
    │                        │                                        │
    │                        └─ collector.flush_batch(session)        │
    │                        └─ session.commit()                      │
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/row_store.py` | Create | Build `list[dict]` from 2D rows + indices; mapping utils |
| `app/services/engine/session_manager.py` | Create | `SessionManager` context manager + savepoint helper |
| `app/services/engine/engine.py` | Modify | `evaluate_sheet()` accepts `rows` + `evidence_collector` params |
| `app/services/engine/group_evaluator.py` | Modify | `build_groups()` / `_build_group_data()` accept `rows: list[dict]` |
| `app/services/engine/exception_handler.py` | Modify | `apply_exceptions()` no-op change (already session-based) |
| `app/services/engine/evidence_collector.py` | Modify | Add `domain` param to `__init__` for logging; no structural change |
| `app/services/engine/rule_based_detector.py` | Modify | `detect()` accepts `rows: list[dict] \| None`; passes to engine |
| `app/services/*/detect_all.py` | Modify | 3 domains: wrap in `SessionManager()`, pass RowStore, domain-level collector |
| `app/services/exporter.py` | Modify | Build RowStore after Polars read; pass to downstream detectors |
| `app/models.py` | Modify | Add `__table_args__` for 3 composite indexes |
| `migrations/005_add_performance_indexes.sql` | Create | 3 `CREATE INDEX CONCURRENTLY` |
| `tests/engine/test_row_store.py` | Create | TDD: RowStore construction, dict access, edge cases |
| `tests/engine/test_session_manager.py` | Create | TDD: context manager, savepoint flow |
| `tests/engine/test_engine_rows_path.py` | Create | TDD: engine with `rows=` produces identical output to `Worksheet` path |

---

## Interfaces / Contracts

```python
# row_store.py
def build_row_store(rows_2d: list[list[Any]], indices: dict[str, int | None]) -> list[dict[str, Any]]:
    """Convert 1-based 2D list (from _SimpleSheet/Polars) to list[dict] using column index map."""

def row_from_dict(row: dict[str, Any], indices: dict[str, int | None]) -> dict[str, Any]:
    """Alias — identity for dict rows; kept for interface consistency."""

# session_manager.py
class SessionManager:
    def __init__(self, domain: str) -> None: ...
    def __enter__(self) -> Session: ...
    def __exit__(self, ...) -> None: ...
    @contextmanager
    def savepoint(self) -> Generator[None, None, None]: ...

# engine.py — modified signature
def evaluate_sheet(
    self,
    rule_name: str,
    data_sheet: Worksheet | None = None,     # kept for backward compat
    indices: dict[str, int | None],
    rows: list[dict[str, Any]] | None = None, # NEW: facts-first path
    evidence_collector: EvidenceCollector | None = None, # NEW: domain-level
    persist: bool = True,
) -> list[dict[str, Any]]: ...

# group_evaluator.py — modified
@staticmethod
def build_groups(
    data_sheet: Worksheet | None = None,
    indices: dict[str, int | None] = None,
    rows: list[dict[str, Any]] | None = None,
    ...
) -> dict[str, list[int]]: ...
```

---

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | RowStore generation | Build from known 2D list, verify dict keys/values match indices |
| Unit | SessionManager enter/exit | Mock `get_session()`, verify commit on success, rollback on error |
| Unit | Engine rows path vs old path | Same rule, same data, both paths → identical result list |
| Integration | Domain detect_all with single session | Compare output of `detect_all_*` before/after refactor |
| Snapshot | Full legacy parity | Existing `test_snapshot_legacy_vs_engine.py` must pass unchanged |
| Index | Migration SQL | Verify `\d reglas` shows composite index; `EXPLAIN` shows index scan |

**Strict TDD**: Each file created with RED (failing test) → GREEN (implementation) cycle. The row store and session manager are pure functions / simple context managers — easy to test in isolation.

---

## Migration / Rollout

1. **Phase 1** (tests): Write `test_row_store.py`, `test_session_manager.py`, `test_engine_rows_path.py` — all RED
2. **Phase 2** (row_store + session_manager): Pure implementations, GREEN
3. **Phase 3** (engine + group_evaluator refactor): Add optional params, existing tests stay GREEN
4. **Phase 4** (detect_all.py refactor): Wrap in SessionManager, pass RowStore, domain-level collector
5. **Phase 5** (migration): `005_add_performance_indexes.sql` — `CONCURRENTLY` so no downtime
6. **Verification**: Snapshot tests + integration tests must match identically

**Rollback**: `RUN_MODE=legacy` env var bypasses engine entirely (already exists as `is_rule_engine_enabled()`). Indexes can be dropped via `005_rollback_performance_indexes.sql`. Evidence persistence toggled via `SKIP_EVIDENCE_AUDIT=true`.

---

## Open Questions

- [ ] **GroupEvaluator pre-filter**: The proposal mentions O(1) pre-filter for `eq`/`in` conditions. Does this add meaningful gain vs the dict-based row iteration (~50ns per lookup)? I'd skip it unless benchmarks show it's a bottleneck after RowStore.
- [ ] **Evidence batch size**: 50K rows × 20 rules = 1M evidence rows. `bulk_insert_mappings` with 1M items may OOM. Should we batch in chunks of 10K?
