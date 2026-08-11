## Exploration: Remaining Engine vs Legacy Gap

### Current Architecture Summary

After 4 rounds of optimization, the engine still uses a **rule-major iteration pattern**:

1. **exporter.py** builds RowStore (`list[dict]`) once → passes to `detect_all.py`
2. **detect_all.py** calls `RuleBasedDetector(rule_name).detect()` for each rule **sequentially** — 21-28 calls per domain
3. Each `evaluate_sheet()` does a **full row scan**:
   - 1× RowStore dict lookup per row
   - 2× EvaluationContext creations per row (one for exceptions, one for eval)
   - 1× full dict copy per row (`{**row_data, **params}`)
   - Condition tree evaluation per row: for each atomic node → `get_provider()` + `provider.resolve()` + `get_evaluator()` + `evaluator.evaluate()`
   - In production: full trace dict allocation per atomic node

**Key numbers at 50K rows / 21 rules / 3 atomic conditions avg:**
- 1,050,000 row iterations (21 × 50K)
- 2,100,000 EvaluationContext instances
- 1,050,000 full dict copies
- 3,150,000 provider lookups + 3,150,000 evaluator lookups
- 3,150,000 trace dicts in production mode

### What Previous Optimizations Already Addressed

| Optimization | What it fixed | Remaining |
|---|---|---|
| RowStore | O(1) dict access replaces openpyxl `cell()` | Still 21 passes |
| SessionManager | 1 DB session instead of 20-30 | — |
| Batch evidence | 1 flush instead of 20 | — |
| Composite indexes | Fast rule loading | — |
| Exception caching | O(1) exception check per rule (was O(N)) | — |
| Lazy date.edad | Only computed when needed | — |
| NO_MATCH skip | No evidence ORM for NO_MATCH | Trace dicts STILL allocated |
| `_evaluate_fast` | No trace dicts in fast path | Only used when `persist=False` (testing) |

---

### Remaining Bottlenecks

#### 1. **Rule-major iteration** — 21+ full row scans instead of 1

**Cost**: 21× row iteration overhead. Each rule re-reads all rows from the same RowStore, re-creates EvaluationContexts, re-evaluates condition trees.

**Why it still exists**: The engine was designed as one-rule-at-a-time (`evaluate_sheet(rule_name, ...)`). Each `detect_all.py` calls it sequentially for each rule. `evaluate_sheet_domain()` exists but is unused — and even it loops rules sequentially.

**Evidence**:
- Urgencias: **28** RuleBasedDetector calls → 28 full scans
- Odontología: **21** RuleBasedDetector calls → 21 full scans
- Hospitalización: **22** RuleBasedDetector calls → 22 full scans

**Legacy comparison**: Legacy also ran 21 passes, but each pass had **no abstraction overhead** — flat if/elif with direct cell() access. The engine's per-pass cost is 3-5× higher because of abstraction layers.

**Affects**: ALL environments (both `_PERSIST=True` and `_PERSIST=False`)

#### 2. **Two redundant EvaluationContext creations with full dict copy**

**Cost**: 2× dataclass instantiation + 1× dict copy per row per rule = 2,100,000 instances + 1,050,000 full dict copies at 50K rows × 21 rules.

**Why it still exists**: The first `ctx` (line 140 in engine.py) exists only for exception checking — `apply_exceptions()` needs `invoice_data`. The second `eval_ctx` (line 155) copies the entire `row_data` dict even when `params` is empty (the common case: `param_configs = [{}]`).

**Code trace**:
```python
# line 140 — ctx created ONLY for exception check
ctx = EvaluationContext(invoice_data=row_data, ...)
effect, overrides = exception_handler.apply_exceptions(rule, ctx, ...)

# line 155 — eval_ctx with FULL DICT COPY of row_data  
eval_ctx = EvaluationContext(
    invoice_data={**row_data, **(params if isinstance(params, dict) else {})},
    ...
)
```

The exception handler only uses `ctx.invoice_data` — it could accept `row_data` directly as a plain dict, eliminating the first EvaluationContext.

The `{**row_data}` copy is wasteful for the ~80% of rules with a single empty param config.

**Affects**: ALL environments

#### 3. **Provider/evaluator registry lookups per atomic condition**

**Cost**: 2 dict lookups + 2 method calls per atomic condition = 6,300,000 lookups at 50K × 21 × 3.

**Per atomic condition path**:
```python
provider = get_provider(fuente)        # dict lookup: PROVIDER_REGISTRY.get(prefix)
row_value = provider.resolve(fuente, ctx)  # method call → InvoiceProvider: context.invoice_data.get(field_name)
evaluator = get_evaluator(operador)    # dict lookup: EVALUATOR_REGISTRY.get(operator)
outcome = evaluator.evaluate(node, row_value, valor_esperado, context=ctx)  # method call
```

**Why it still exists**: Providers and evaluators are resolved fresh on every call. The provider prefix (e.g., `"invoice"`) and operator (e.g., `"eq"`) are STATIC per condition node — they never change between rows. But the engine doesn't cache them on the node.

**Legacy comparison**: Legacy `isinstance(vlr, float) and vlr % 1 != 0` = 2 Python ops. Engine = 4 lookups + method calls. This is ~29 extra Python operations per atomic condition.

**Affects**: ALL environments

#### 4. **Trace dict allocation in production** (`persist=True`)

**Cost**: Full trace dicts built for EVERY atomic node, for EVERY row — even NO_MATCH rows (the ~95% majority). Only MATCH/ERROR rows actually use the trace for evidence.

**`_evaluate_atomic` trace allocation** (lines 362-371):
```python
return {
    "outcome": outcome,
    "trace": {
        "tipo": "atomic",
        "operador": operador,
        "fuente_datos": fuente,
        "valor_real": str(row_value) if row_value is not None else None,  # str() call
        "valor_esperado": str(valor_esperado) if valor_esperado is not None else None,  # str() call
        "outcome": outcome,
    },
}
```

**`_evaluate_composite` trace allocations** — builds nested dicts for AND/OR/NOT with intermediate lists.

**Why it still exists**: The engine decides ONCE at the top (`collect_trace=persist`) whether to build traces. It doesn't check per-node. The `_evaluate_fast` path avoids all this but is only taken when `persist=False`.

**Irony**: Optimization #7 (NO_MATCH evidence skip) already skips the ORM record for NO_MATCH, but the trace dicts are already allocated by then. The allocation happens in `ConditionEvaluator.evaluate()`, but the check happens in `engine.py` AFTER evaluation.

**Affects**: Production (`_PERSIST=True`). Not affected when `SKIP_EVIDENCE_AUDIT=true`.

#### 5. **Complex evaluator overhead per row**

**Cost**: Evaluators like `CupsContratadoEvaluator`, `CronogramaCheckEvaluator`, `CentroCostoIntramuralEvaluator` do heavy per-row work — multiple `str()` coercions, `inv.get()` calls, conditional branching, sometimes DB queries.

**Why it still exists**: These evaluators encapsulate legacy detector logic inside the `evaluate()` method. They're called once per row per rule through the full abstraction chain (registry → resolve → evaluate).

**Example**: `CronogramaCheckEvaluator.evaluate()` does ~40 operations: 4 `str()` casts, 6 `inv.get()` calls, date parsing, cache lookups, etc. — all behind the single `evaluator.evaluate()` call. Legacy did the same work but without the 4-wrapper overhead.

**Affects**: ALL environments, but only for rules that use complex evaluators (~30% of rules).

#### 6. **Results dict building with 20+ field checks**

**Cost**: Lines 200-222 check ~20 fields in BOTH `row_data` and `eval_ctx.invoice_data` per MATCH row — ~40 `dict.get()` calls per match.

**Why it still exists**: The problem dict needs to include display fields for the frontend. But the double-check (`if field in row_data: ... elif field in eval_ctx.invoice_data: ...`) is redundant since `eval_ctx.invoice_data` is a superset of `row_data` (it's a copy with merged params).

**Affects**: ALL environments for MATCH rows (~5% of rows)

---

### Approaches

#### 1. **Row-major evaluation** — evaluate ALL rules against one row, then move to next

**Description**: Instead of `for rule in rules: for row in rows:`, do `for row in rows: for rule in rules:`. Build ALL condition trees once, then iterate rows once. For each row, try all rules with short-circuit.

This requires consolidating all RuleBasedDetector calls in detect_all.py into a single engine call that accepts multiple rules.

**Key insight**: The RowStore is already read-only. No row mutation between rules. Perfect for row-major access.

**Sub-approach 1a**: **Batch `evaluate_sheet_domain()`** — use the existing method that loads all rules and evaluates them sequentially. Same 21 passes but eliminates detect_all.py boilerplate. Low impact.

**Sub-approach 1b**: **True row-major** — restructure the inner loop: fetch row_data once, evaluate all condition trees against it, collect outcomes. Requires refactoring engine.py or creating a new `evaluate_rows()` method.

- Effort: **High** (for 1b), **Low** (for 1a)
- Impact: **Very High** (1b: 21× → 1× row scans), **Low** (1a: no structural change)
- Risk: **Medium** — exception handling, evidence per-rule, and param configs must remain per-rule. Savepoints required per rule for transaction safety.

#### 2. **Pre-resolve providers and evaluators at tree-build time**

**Description**: During `build_tree()`, store the resolved provider and evaluator objects directly on condition nodes:
```python
node["_provider"] = get_provider(fuente_datos)
node["_evaluator"] = get_evaluator(operador)
```
Then in `_evaluate_fast()` and `_evaluate_atomic()`, use `node["_provider"]` and `node["_evaluator"]` instead of dict lookups. Eliminates 2 dict lookups + 2 function calls per atomic node per row.

- Effort: **Low** (~20 lines across condition_evaluator.py)
- Impact: **Medium** — saves 2 lookups + 2 calls per atomic condition. At 3M+ atomic evals per run, measurable.
- Risk: **Very Low** — providers and evaluators are stateless singletons (except __init__). Caching them doesn't introduce state issues.

#### 3. **Eliminate redundant EvaluationContext creation**

**Description**: Two changes:

3a. Accept `invoice_data: dict` directly in `apply_exceptions()` instead of requiring an `EvaluationContext`. The method only uses `context.invoice_data` anyway. Cuts 1 instance per row per rule.

3b. Avoid `{**row_data}` copy when params are empty. Either pass `row_data` directly (not a copy) since it's not mutated, or use a lightweight proxy.

- Effort: **Low** (~15 lines in engine.py + exception_handler.py)
- Impact: **Medium** — saves 1,050,000 dataclass instances + 1,050,000 dict copies at 50K × 21 rules
- Risk: **Low** — `row_data` is never mutated after creation; existing code already doesn't write to it

#### 4. **Two-phase evaluation in production: fast pass + trace on demand**

**Description**: Change the production path to:
1. Evaluate with `_evaluate_fast()` — no traces, fast
2. If outcome is MATCH or ERROR, RE-EVALUATE with trace collection for evidence
3. If NO_MATCH, skip — no traces allocated

**Trade-off**: Double evaluation for MATCH/ERROR rows (~5% of rows). But saves trace allocation for 95% of rows. Net win if trace allocation cost > fast evaluation cost.

- Effort: **Medium** (~40 lines in engine.py + condition_evaluator.py)
- Impact: **High** — eliminates ~3M trace dict allocations in production (95% of rows are NO_MATCH)
- Risk: **Low** — double evaluation for MATCH rows is safe (pure functions, no side effects). Risk of discrepancy: none, same code path.

#### 5. **Pre-built problem dict template**

**Description**: Build a template of field key lookups once per rule (not per row), then `.copy()` it per MATCH row. Avoids 20 `dict.get()` calls per MATCH row.

```python
# Before rule loop:
_display_fields = ["codigo", "codigo_equiv", "procedimiento", ...]

# Per MATCH row:
problem = template.copy()
for field in _display_fields:
    if field in row_data:
        problem[field] = row_data[field]
```

- Effort: **Low** (~10 lines in engine.py)
- Impact: **Low** — MATCH rows are only ~5%, so this saves 40 get() calls on 5% of rows ~ 2% total improvement
- Risk: **None**

#### 6. **Consolidate `evaluate_sheet_domain()` usage**

**Description**: Replace the 21-28 individual `RuleBasedDetector` calls in each `detect_all.py` with a single `engine.evaluate_sheet_domain(domain, ...)` call. This would:
- Load all rules once (single query)
- Group evidence collection at domain level
- Eliminate detect_all.py boilerplate (and the risk of session-per-rule in some domains like extramural)

**Caution**: This does NOT change the rule-major iteration pattern — `evaluate_sheet_domain()` loops rules internally. But it would enable future row-major refactoring by centralizing the entry point.

- Effort: **Medium** (~50-80 lines across detect_all.py files)
- Impact: **Low** on its own, **High** as enabler for Approach 1
- Risk: **Low** — `evaluate_sheet_domain()` already exists and is tested; just needs to be wired

---

### Recommendation

**Immediate (next sprint): Approach 2 + Approach 3 + Approach 4**

These three together address ALL remaining bottlenecks with LOW risk and LOW effort:

| Bottleneck | Approach | Effort | Impact |
|---|---|---|---|
| Provider/evaluator lookups (3M+ per run) | #2 — Pre-resolve at tree-build | Low | Medium |
| 2× EvaluationContext + dict copy (2.1M per run) | #3 — Eliminate redundant ctx | Low | Medium |
| Trace dicts for NO_MATCH rows (95% of rows) | #4 — Two-phase eval | Medium | High |

Combined, these could yield **2-3× speedup** in production mode and **1.5-2×** in test mode (SKIP_EVIDENCE_AUDIT=true).

**Future: Approach 1 (Row-major) + Approach 6 (consolidation)**

Row-major evaluation is the highest-impact change but requires significant refactoring. It should be designed carefully, NOT as a quick optimization. The consolidation (#6) should be done first to centralize the entry point, making row-major a simpler internal refactor later.

| Bottleneck | Approach | Effort | Impact |
|---|---|---|---|
| 21 full row scans | #6 + #1b — Consolidate + row-major | High | Very High |

### Ready for Proposal

Yes. For the immediate optimizations (#2, #3, #4). The row-major refactor needs separate exploration (it's a larger change with architectural implications).
