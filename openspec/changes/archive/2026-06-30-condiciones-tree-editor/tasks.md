# Tasks: ConditionTreeEditor Refactor

## Phase 1: Foundation — operators.ts

| # | Task | Detail | Files |
|---|------|--------|-------|
| ✅ 1.1 | Create `operators.ts` — constants file | Define all 18 operators across 5 categories (Comparison, String, Set, DB, Complex) with per-operator value type mapping. Export `OPERADORES_ATOMICOS`, `CATEGORIAS`, `OPERADORES_COMPOSITE`, and `OPERADOR_VALUE_TYPE` map. | `frontend/src/components/admin-reglas/operators.ts` |
| ✅ 1.2 | Complete `FUENTES_DATOS` | Add `catalog.*`, `group.*`, `contract.*` prefixes to existing FUENTES_DATOS array. | `frontend/src/components/admin-reglas/operators.ts` |
| ⏭️ 1.3 | ~~Unit test: constants correctness~~ | Skipped — no frontend test framework configured for this project. | N/A |

## Phase 2: Reducer + Core State

| # | Task | Detail | Files |
|---|------|--------|-------|
| ✅ 2.1 | Create `ConditionTreeEditor.tsx` — orchestrator | `useReducer` with 6 actions: `LOAD_TREE`, `ADD_CHILD`, `UPDATE_NODE`, `REMOVE_NODE`, `TOGGLE_COLLAPSE`, `REORDER_CHILDREN`. Recursive tree walk for updates. Node IDs via `crypto.randomUUID()`. | `frontend/src/components/admin-reglas/ConditionTreeEditor.tsx` |
| ✅ 2.2 | Implement `serializeTree()` and `hydrateTree()` | `serializeTree(strip _collapsed)` → clean `CondicionTree[]` for API. `hydrateTree(add _collapsed: false)` on load (R8 default expanded). | `frontend/src/components/admin-reglas/ConditionTreeEditor.tsx` |
| ⏭️ 2.3 | ~~Unit test: reducer + serialization~~ | Skipped — no frontend test framework configured. | N/A |

## Phase 3: Sub-components

| # | Task | Detail | Files |
|---|------|--------|-------|
| ✅ 3.1 | Create `OperatorSelector.tsx` | Categorized dropdown: 5 option groups (Comparison, String, Set, DB, Complex) with group labels. Accepts `value` + `onChange`. Renders group label + disabled divider. | `frontend/src/components/admin-reglas/OperatorSelector.tsx` |
| ✅ 3.2 | Create `ValueInput.tsx` | Dynamic dispatcher: `<input type="number">` for comparison, `<input type="text">` for string, `<textarea>` for JSON (regex_extract, exists_in_db), `ArrayEditor` for set operators, `<span>`/hidden for context-based evaluators. | `frontend/src/components/admin-reglas/ValueInput.tsx` |
| ✅ 3.3 | Create `AtomicNode.tsx` | Leaf node row: FUENTES_DATOS `<select>` + `OperatorSelector` + `ValueInput` + [×] remove button. Dispatches `UPDATE_NODE` on field change. | `frontend/src/components/admin-reglas/AtomicNode.tsx` |
| ✅ 3.4 | Create `CompositeNode.tsx` | AND/OR/NOT type `<select>` + collapse toggle (R8) + [+ Atomic] / [+ Composite] buttons + [×] remove + recursive child render. Each child is either `CompositeNode` or `AtomicNode` per `tipo`. | `frontend/src/components/admin-reglas/CompositeNode.tsx` |

## Phase 4: Integration

| # | Task | Detail | Files |
|---|------|--------|-------|
| ✅ 4.1 | Modify `page.tsx` | Replace `ConditionCondicionTree` + helpers (`updateNodeInTree`, `removeNodeFromTree`, `addChildToNode`, `_tempNodeId`) with `<ConditionTreeEditor>`. Pass `tree` + `onChange` + `readOnly`. ~200 lines removed (actual: 346). | `frontend/src/pages/admin-reglas/page.tsx` |
| ⏭️ 4.2 | ~~Integration test: existing rule data~~ | Skipped — no frontend test framework configured. | N/A |
| ⏭️ 4.3 | ~~Integration test: save round-trip~~ | Skipped — no frontend test framework configured. | N/A |

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Estimated new code | ~350-400 lines across 6 new files |
| Estimated removed | ~200 lines from `page.tsx` |
| Net changed lines | ~150-200 |
| 400-line budget risk | **Low** |
| Chained PRs recommended | **No** — single PR fits well within budget |
| Decision needed before apply | **Yes** (ask-always delivery strategy) |

## Next Step

Implementation complete. Ready for verify.

## Status

**8/13 tasks done** (5 skipped due to no frontend test framework). ~892 lines added, ~346 removed from page.tsx. Net: ~546 lines.
