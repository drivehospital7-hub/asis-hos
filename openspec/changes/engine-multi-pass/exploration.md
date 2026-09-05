# Exploration: engine-multi-pass-aggregation

## Current State

The rule engine (`app/services/engine/`) evaluates conditions against Excel sheets in two modes:

1. **Row-by-row** — iterates rows, evaluates condition trees per row using `ConditionEvaluator` + `EvaluationContext`. Covers ~80% of detectors (decimales, tipo_documento_edad, centro_costo via `CentroCostoCheckEvaluator`, etc.).

2. **Group-by** — pre-scans rows into groups by factura via `GroupEvaluator.build_groups()`, computes scalar aggregates per group (`distinct_count`, `group_size`, `sum`), then evaluates a condition tree against the aggregated context. Currently covers `doble_tipo_procedimiento` and `revision_cantidad`.

The engine detects group-by rules by checking `parametros[0].get("group_by")` in `engine._evaluate_sheet_group_by()`.

Three legacy detectors remain outside the engine's expressive range:

| Detector | Lines | Domain | Pattern |
|----------|-------|--------|---------|
| `detect_duplicados_base.py` | 178 | Transversal | Pair-counting with ALL-pairs-threshold |
| `sala_observacion.py` | 366 | Urgencias | Pre-scan collection + cross-row set dependencies |
| `centro_costo_rules.py` | 146 | Transversal | Already covered by `CentroCostoCheckEvaluator` ✅ |

The wrappers `duplicados_farmacia.py` (Urgencias, 50 lines) and `duplicados_farmacia_farmacia.py` (Farmacia, 42 lines) are thin callers of `detect_duplicados_generico()` with domain-specific filters. `detect_all.py` line 288 already has an `is_rule_engine_enabled()` branch calling `RuleBasedDetector("duplicados_farmacia")`, suggesting a DB rule exists but may not replicate the full pair-counting logic.

## Affected Areas

- `app/services/engine/group_evaluator.py` — Must be extended with new aggregation functions (`collect_set`, `pair_counts`). Current aggregations are `distinct_count`, `group_size`, `sum` only.
- `app/services/engine/evaluators.py` — Needs new atomic evaluators (`set_contains_all`, `set_intersects`, `all_values_match`) to evaluate conditions against collected data.
- `app/services/engine/engine.py` — `_build_row_context()` may need awareness of group-level pre-scan cache if evaluators need cross-row context (minor change).
- `app/services/urgencias/sala_observacion.py` — Legacy code to retire after engine replicates its logic.
- `app/services/transversales/detect_duplicados_base.py` — Legacy code to retire after engine replicates pair-counting.
- `app/services/engine/providers.py` — May need a new provider prefix for group-collected data (e.g., `group.`).
- `app/models/` — May need new `Condicion` rows for the new evaluator operators and data sources.
- `tests/engine/test_snapshot_phase*.py` — Snapshot tests needed for legacy-vs-engine parity on both detectors.

## Patterns Identified

### Pattern 1: Pre-scan Collection + Cross-row Set Dependency

**Found in**: `sala_observacion.py` (lines 96–193 first pass, lines 194–361 second pass)

**Mechanics**:
1. First pass iterates all rows, collects per-factura state:
   - `codigos_sala` — set of sala observation codes found in any row
   - `codigos_urgencias_obligatorios` — set of mandatory codes (890701, 890601) found
   - `codigos_soat_obligatorios` — set of SOAT mandatory codes (39145, 39131) found
   - `tiene_890601h` — boolean flag
   - `tiene_soat_prohibido` — boolean flag
   - `entidad`, `estancia_horas`, `tarifario` — scalar context
2. Second pass validates cross-row rules:
   - **Set containment**: "If factura has ANY sala code AND is NOT SOAT, must have BOTH 890701 AND 890601" → `obligatorios_requeridos - codigos_urgencia_obligatorios` must be empty
   - **Set presence**: "If factura has SOAT sala codes AND SOAT tarifario, must have 39145 AND 39131" → `CODIGOS_SOAT_OBLIGATORIOS_SALA - codigos_soat_obligatorios` must be empty
   - **Entity-specific restrictions**: "ESS118/ESSC18 cannot have 129B02"
   - **Estancia thresholds**: "If estancia > 6h, require long-stay code; if ≤ 2h, no sala code needed"

**Engine gap**: `GroupEvaluator` can compute scalar aggregates but cannot collect sets of values per group. The `SalaObservacionEvaluator` (per-row) handles the estancia-vs-code check but cannot express cross-row set dependencies like "does this factura have code 890701 anywhere in its rows?"

### Pattern 2: Pair Counting with All-Pairs Threshold

**Found in**: `detect_duplicados_base.py` (lines 89–164)

**Mechanics**:
1. First pass: filter rows by tipo_factura + optional tarifario/codigo_tipo_proc; group by `(factura, [codigo_tipo_procedimiento])`; within each group, count occurrences of each `(codigo, cantidad)` pair.
2. Second pass: emit result if ALL pairs have count ≥ 2 (line 156: `len(pares_duplicados) == total_pares`).

**Key logic**:
```python
par_counts[par_key] = par_counts.get(par_key, 0) + 1  # first pass
if len(pares_duplicados) == total_pares:               # second pass: ALL threshold
```

**Engine gap**: `GroupEvaluator` has no pair-frequency aggregation. `distinct_count` counts distinct values of a single field but cannot count occurrences of compound keys `(field1, field2)` nor evaluate "all counts ≥ N".

### Pattern 3: Group-level Condition Evaluation

**Found in**: Both detectors, already partially supported by engine.

**Mechanics**: Conditions evaluated against group-level data rather than individual rows. The engine already does this via `GroupEvaluator.evaluate()` which builds an `EvaluationContext` with aggregated data.

**Engine status**: ✅ Already supported. The gap is only in WHAT data is available in the group context (currently only scalar aggregates).

### Pattern 4: Legacy Wrappers with Domain-Specific Filters

**Found in**: `duplicados_farmacia.py`, `duplicados_farmacia_farmacia.py`

**Mechanics**: Thin wrappers that call `detect_duplicados_generico()` with domain-specific `tipo_factura`, `tarifario_val`, and `codigos_tipo_proc` parameters.

**Engine status**: The engine already handles this via `parametros` overrides in the rule definition. The wrapper pattern maps cleanly to DB rule `parametros` configs. No engine change needed.

## Engine Changes Needed (Ranked by Complexity)

### Change 1: `collect_set` aggregation — LOW complexity

**What**: Add a new aggregation function to `GroupEvaluator._build_group_data()` that collects all non-None values of a field into a Python set stored in the group data dict.

**Config example**:
```json
{
  "function": "collect_set",
  "field": "codigo",
  "target": "codigos_sala_set"
}
```

**Implementation**: ~15 lines in `group_evaluator.py`. Iterates group rows, reads column, adds non-None values to a `set`, stores under target key.

**Enables**: All "does factura have code X?" checks from sala_observacion.

### Change 2: `set_contains_all` / `set_intersects` evaluators — LOW complexity

**What**: New atomic evaluators that compare collected sets against expected sets.

- `set_contains_all`: Returns True if `collected_set` ⊇ `expected_set` (all mandatory codes present)
- `set_intersects`: Returns True if `collected_set` ∩ `expected_set` ≠ ∅ (sala code exists)

**Config example** (condition node):
```json
{
  "tipo": "atomic",
  "operador": "set_contains_all",
  "fuente_datos": "invoice.codigos_urgencia_set",
  "valor_esperado": ["890701", "890601"]
}
```

**Implementation**: ~30 lines in `evaluators.py`. Resolves the collected set from context via provider, checks containment.

**Enables**: Mandatory code checks, SOAT code checks, prohibited code checks in sala_observacion.

### Change 3: `collect_value_counts` aggregation — MEDIUM complexity

**What**: New aggregation function that counts occurrences of compound keys `(field1, field2)` within a group, returning a list of dicts `[{field1: val1, field2: val2, count: n}, ...]`.

**Config example**:
```json
{
  "function": "collect_value_counts",
  "fields": ["codigo", "cantidad"],
  "target": "pair_counts"
}
```

**Implementation**: ~30 lines in `group_evaluator.py`. Iterates group rows, builds dict of tuple→count, converts to list of dicts.

**Enables**: The pair-counting first pass from detect_duplicados_base.

### Change 4: `all_values_match` evaluator — MEDIUM complexity

**What**: General-purpose evaluator that checks if ALL items in a collected list satisfy a condition. For duplicados: "all items in `pair_counts` have `count ≥ 2`". Could be parameterized with a sub-condition.

**Config example**:
```json
{
  "tipo": "atomic",
  "operador": "all_values_match",
  "fuente_datos": "invoice.pair_counts",
  "valor_esperado": {"field": "count", "operator": "gte", "value": 2}
}
```

**Alternative**: A specialized `pares_duplicados` evaluator that hardcodes the "all pairs ≥ 2" logic. Simpler but less reusable.

**Implementation**: ~40 lines in `evaluators.py` for generic version; ~20 lines for specialized version.

**Enables**: The second pass of detect_duplicados_base — "all pairs duplicated".

### Change 5: Group-level `collect_boolean` aggregation — LOW complexity

**What**: New aggregation `any_match` / `all_match` that evaluates a per-row condition across all rows in a group and returns a boolean. For example: "any row has codigo == '890601H'".

**Config example**:
```json
{
  "function": "any_match",
  "field": "codigo",
  "operator": "eq",
  "value": "890601H",
  "target": "tiene_890601h"
}
```

**Implementation**: ~25 lines in `group_evaluator.py`. During pre-scan, evaluates the per-row condition and OR-aggregates.

**Enables**: Boolean flags like `tiene_890601h`, `tiene_soat_prohibido` from sala_observacion first pass.

**Alternative**: These can also be expressed as `set_contains` checks on collected sets, so this aggregator may be redundant. The `collect_set` + `set_contains` approach is cleaner.

## Approaches

### Approach A: Extend GroupEvaluator with Richer Aggregations + Evaluators (Recommended)

**Description**: Keep the existing `pre-scan → aggregate → evaluate` lifecycle. Add three aggregation functions (`collect_set`, `collect_value_counts`, `any_match`) and three evaluators (`set_contains_all`, `set_intersects`, `all_values_match`). Engine plumbing unchanged.

**Pros**:
- Minimal architectural change — extends existing pipeline, no new phases
- Each aggregation function is ~15-30 lines, each evaluator ~20-40 lines
- All changes are additive to registry-based systems
- Reuses existing condition tree, evidence collection, and audit trail
- Can be implemented incrementally (change 1→2 first, then 3→4)

**Cons**:
- `collect_set` stores Python sets in `EvaluationContext.invoice_data`, which must be serializable for evidence snapshots (solvable: convert to list at evidence record time)
- `collect_value_counts` stores lists of dicts, same serialization concern
- Condition trees for multi-step rules (sala_observacion) become complex AND/OR trees with many atomic nodes

**Effort**: Medium (~150-200 lines of new code across 3 files)

### Approach B: Two-Phase Evaluation with Global Pre-scan Cache

**Description**: Add a `PreScanCollector` that runs before `evaluate_sheet()`, collects all group-level data into a shared cache keyed by factura. Row-by-row evaluators can then reference the cache (e.g., `group_cache[factura]["has_890701"]`). Eliminates the group-by mode split.

**Pros**:
- Row-by-row evaluators gain access to cross-row context
- Could unify sala_observacion into a single evaluator (no group-by needed)
- More powerful for future cross-row detectors

**Cons**:
- Changes engine lifecycle significantly — every `evaluate_sheet()` call must run a pre-scan first
- Pre-scan must happen even for pure row-by-row rules (wasteful) unless opt-in
- Cache invalidation complexity (must clear between sheets)
- Requires coordination between pre-scan and row iteration phases
- Higher implementation risk

**Effort**: High (~400+ lines across 4+ files)

### Approach C: Standalone Compound Evaluators

**Description**: Create `SalaObservacionGrupoEvaluator` and `DuplicadosPairsEvaluator` as compound evaluators that internally perform their own pre-scan in `evaluate()`. No engine changes.

**Pros**:
- Zero engine plumbing changes
- Quick to implement (wrap legacy code in evaluator interface)
- Isolated — changes to one don't affect the other

**Cons**:
- Each evaluator duplicates pre-scan logic (iterate rows, build groups)
- Not reusable — next cross-row detector needs another compound evaluator
- Violates the compositional design of the engine (evaluators should be simple comparisons)
- Sala_observacion has 6+ distinct checks; a compound evaluator would be a monolith
- Harder to express in DB conditions — the entire logic is opaque in one evaluator

**Effort**: Low initially (~100 lines per compound evaluator), but high long-term maintenance cost

## Recommendation

**Approach A** is the right choice. It extends the existing compositional architecture with minimal, reusable primitives:

1. **Implement Changes 1+2 first** (collect_set + set evaluators) — enables sala_observacion's set-based checks. These are the highest-value, lowest-risk changes.

2. **Implement Changes 3+4 next** (pair_counts + all_values_match) — enables detect_duplicados_base pair counting.

3. **Skip Change 5** (boolean aggregator) — `collect_set` + `set_contains` covers the same use case more cleanly.

### Migration Path

| Step | Action | Legacy retired |
|------|--------|---------------|
| 1 | Add `collect_set` to GroupEvaluator | — |
| 2 | Add `set_contains_all`, `set_intersects` evaluators | — |
| 3 | Create DB rules for sala_observacion cross-row checks | — |
| 4 | Snapshot tests: engine vs legacy parity | — |
| 5 | Wire engine into `detect_all.py` via `is_rule_engine_enabled()` | `sala_observacion.py` (cross-row portion) |
| 6 | Add `collect_value_counts` to GroupEvaluator | — |
| 7 | Add `all_values_match` evaluator | — |
| 8 | Create DB rules for duplicados_farmacia with pair-counting | — |
| 9 | Snapshot tests: engine vs legacy parity for duplicados | — |
| 10 | Wire engine duplicados into `detect_all.py` | `detect_duplicados_base.py` (called via wrappers) |

### Risks

- **Serialization**: `collect_set` stores Python `set` objects in `invoice_data`. Evidence snapshots serialize row data — sets must be converted to lists before storage. Mitigation: convert in `_build_group_data()` or at evidence record time.
- **Condition tree complexity**: Sala_observacion rules expressed as condition trees will have 15+ atomic nodes in AND/OR relationships. DB maintainability may suffer. Mitigation: document each rule's condition tree with comments in migration scripts.
- **Performance**: `collect_value_counts` requires iterating all rows per group. If there are 50K rows in 500 groups, each row is visited once — same as legacy. No regression expected.
- **Rule engine fallback**: `detect_all.py` already has `is_rule_engine_enabled()` gates. If engine rules produce incorrect results, systems fall back to legacy detectors. Safe to deploy incrementally.

### Ready for Proposal

Yes. Exploration is complete — all patterns are categorized, engine changes are scoped, and the recommended approach is defined. Proceed to `sdd-propose` for the formal proposal.

## Key Learnings

- The engine already has 80% of what's needed. The `GroupEvaluator` lifecycle (`pre-scan → aggregate → evaluate`) is well-designed and the gap is only in the aggregation functions and evaluator primitives available, not in the architecture itself.
- `centro_costo_rules.py` is fully covered by `CentroCostoCheckEvaluator` and requires no engine changes — it was incorrectly listed as needing multi-pass in the original change description.
- The existing `SalaObservacionEvaluator` (per-row) handles estancia-vs-code checks but cannot express cross-row set dependencies. Both per-row AND group-level evaluation are needed for full sala_observacion coverage.
- The `duplicados_farmacia` DB rule apparently exists (called in `detect_all.py` line 288), but may be using a simplified group_by that doesn't match the legacy pair-counting logic. This needs verification during implementation.
- `collect_set` + set evaluators are the highest-value primitives — they enable not just sala_observacion but any future cross-row "if code A then code B" rules.
