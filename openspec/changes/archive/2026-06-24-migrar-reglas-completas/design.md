# Design: Migración Completa de Reglas Legacy al Motor de Reglas

## Technical Approach

Incremental engine extension across 7 phases, each producing DB-backed rule seeds (`insert_rule_*.sql`), wiring them via `RuleBasedDetector` in their domain's `detect_all.py` under `USE_RULE_ENGINE` flag, and snapshot-testing legacy-vs-engine output identity. The existing `ConditionEvaluator` + `AtomicEvaluator` + `ContextProvider` registries are extended, not rewritten. Group-by and multi-rule cascade are built as parallel evaluation paths — zero changes to existing row-by-row logic. Context grows a `group_data` slot and `session` reference. Evidence flushes once per domain evaluation (single batch insert).

## Architecture Decisions

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| Group-by engine | Extend `ConditionEvaluator` | New `GroupEvaluator` class | Option B | Keeps row-by-row path untouched; group evaluation has different lifecycle (pre-scan → partition → evaluate → merge). Risk per exploration: zero `RowEvaluator` changes. |
| Catalog cache | Per-lookup DB query | Session-level in-memory dict | Option B | 1000-row sheet × repeated professionals = N queries vs 1. Memoization dict keyed by `(table, field, value)` matches legacy approach. |
| Multi-rule cascade | Loop in `engine.py` | Domain orchestrator in `detect_all.py` | Loop in `engine.py` | `evaluate_sheet_domain(domain)` keeps orchestration inside engine, single session, single evidence flush. `detect_all.py` becomes thin delegator. |
| Seed format | Raw SQL files | Alembic migrations | Raw SQL files | Rules are data, not schema. Insert-only. Idempotent via `ON CONFLICT DO NOTHING`. Existing project has no Alembic — follow the convention. |
| Date evaluators | New evaluator type | Extend `AtomicEvaluator` | Extend `AtomicEvaluator` | `age_from_dates` and `hours_diff` take two fields + return scalar — fits the `(condition, row_value, expected) → bool` contract with value resolution in provider layer. |

## Data Flow

### Phase 1-3 (Row-by-Row + Providers)
```
detect_all.py ──(flag)──→ RuleBasedDetector("rule_name", session)
                               │
                    RuleEvaluationEngine.evaluate_sheet()
                               │
               ┌───────────────┼───────────────┐
          RuleResolver   ConditionEvaluator   Providers
          (load rule+    (recursive tree)    (Invoice/Catalog/
           conditions)                       Contract resolvers)
               │               │
          EvidenceCollector ────┘
               │
          flush_batch(session) → ResultadoAuditoria
```

### Phase 4 (Multi-Rule Cascade)
```
detect_all.py ──(flag)──→ engine.evaluate_sheet_domain("urgencias", ws, indices)
                               │
                    RuleResolver.resolve("urgencias", session)
                    → [R1(prio=1), R2(prio=2), ...]
                               │
                    for rule in rules (priority order):
                        evaluate_sheet(rule.name, ws, indices)
                        collect results
                               │
                    EvidenceCollector.flush_batch(session)  ← ONCE
```

### Phase 6 (Group-By)
```
GroupEvaluator.evaluate(rule, ws, indices)
    │
    ├─ Pre-scan: iterate all rows → build groups dict[factura] = [rows]
    │
    ├─ For each group:
    │      ctx = EvaluationContext(group_data=group_rows, invoice_data=first_row)
    │      result = ConditionEvaluator.evaluate(tree, ctx)
    │      if MATCH → mark all rows in group
    │
    └─ flush_batch
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/providers.py` | Modify | Add `CatalogProvider`, `ContractProvider`, `CodeMappingProvider`, `DateProvider` classes + register |
| `app/services/engine/evaluators.py` | Modify | Add `StartsWithEvaluator`, `RegexExtractEvaluator`, `AgeFromDatesEvaluator`, `HoursDiffEvaluator`, `ExistsInDBEvaluator` |
| `app/services/engine/context.py` | Modify | Add `group_data: list[dict] | None` and `session: Any` fields |
| `app/services/engine/group_evaluator.py` | Create | `GroupEvaluator` — pre-scan, group-by key, aggregate functions |
| `app/services/engine/engine.py` | Modify | Add `evaluate_sheet_domain(domain, ws, indices)` method |
| `app/models.py` | Modify | Add `Profesional`, `CatalogoCodigo`, `ConstanteSistema` ORM classes |
| `seed/phase1/*.sql` | Create | 5 seed files: cups_equivalentes, revision_entidad_86, cantidades_urgencias, cantidades_soat, mal_capitado |
| `seed/phase2/profesionales.sql` | Create | Professional catalog seed data |
| `seed/phase3/contratos.sql` | Create | Contract reference seed data |
| `app/services/{domain}/detect_all.py` | Modify | Add `USE_RULE_ENGINE` branches for each migrated rule (5 per phase) |

## Interfaces / Contracts

### CatalogProvider path syntax
```
catalog.profesionales[codigo].tipo        → "ODONTOLOGO" | null
catalog.profesionales[codigo].nombre      → "Juan Pérez" | null
catalog.find_by_field("profesionales", "codigo", "OD001")
```

### ContractProvider path syntax
```
contract.nota_tecnica[entidad].tarifa     → 5000 | null
contract.ide_valido[entidad][codigo]      → [100, 200] | []
```

### GroupEvaluator signature (non-obvious pattern)
```python
class GroupEvaluator:
    def evaluate(self, rule: Regla, ws: Worksheet, indices: dict,
                 group_by_field: str = "numero_factura",
                 aggregate_function: str = "distinct_count",
                 aggregate_field: str = "tipo_procedimiento",
                 threshold_op: str = "gt", threshold_val: Any = 1,
                 session: Session) -> list[dict]:
```

### EvaluationContext extension
```python
@dataclass
class EvaluationContext:
    invoice_data: dict | None = None
    group_data: list[dict] | None = None     # NEW: Phase 6
    session: Any = None                       # NEW: Phase 7 DB queries
    # ... existing fields unchanged
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Each new evaluator/provider | pytest, ≥3 cases per evaluator (match, no-match, edge) |
| Integration | `RuleBasedDetector` round-trip | Mock session + real openpyxl sheet, assert output keys match legacy |
| Snapshot | Legacy vs engine output identity | `test_snapshot_legacy_vs_engine.py` per rule: run both, diff results dicts |
| Regression | All 200+ existing tests | `python -m pytest -v` must pass after every phase |

## Migration / Rollout

Each phase ships independently under `USE_RULE_ENGINE=true`. `USE_RULE_ENGINE=false` restores 100% legacy path instantly. No data migration needed — seed SQL is insert-only, idempotent. Legacy code preserved untouched across all phases.

## Open Questions

- [ ] Phase 6 `detect_duplicados_base` multi-pass counting — can pair-count aggregation be expressed in condition tree JSONB, or does it need custom evaluator?
- [ ] Phase 3 `ide_contrato_urgencias` pre-scan for 861801/890405 — implement as `PreScanHook` on engine or within `GroupEvaluator` pre-scan phase?
- [ ] `REVERSE` rules in `centro_costo_rules` — model as separate rules with inverted conditions or single rule with `reverse` flag?
