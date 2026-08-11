# Proposal: Condition Tree Editor Refactor

## Intent

The `ConditionCondicionTree` component (120+ lines inside a 1705-line page.tsx) supports only 8 of 18 engine operators, lacks composite-child nesting, uses a hardcoded text input for all value types, and has no collapsible tree. This makes complex rules with 15+ conditions unmanageable. We need a standalone, maintainable editor that matches the engine's full capability.

## Scope

### In Scope
- Extract `ConditionTreeEditor` as a standalone component with 5 sub-components
- Support all 18 engine operators with per-category input widgets (text, number, JSON editor, array editor, hidden for context-based evaluators)
- Composite-child support: AND/OR/NOT nodes can have children of any type
- Complete `FUENTES_DATOS` — add `catalog.*`, `group.*`, `contract.*` paths
- Collapsible/expandable tree nodes with indentation
- Operator categorization UI (comparison, string, set, DB, complex)

### Out of Scope
- Shared conditions between rules (deferred to separate change)
- Backend changes — `rule_service.py` handles the tree format correctly as-is
- DB schema changes — `JSONB`/`padre_id` structure stays unchanged

## Capabilities

### New Capabilities
None — this is a pure refactor of existing UI capability.

### Modified Capabilities
- `admin-reglas-ui`: R2 (condition tree builder) expands from 8 → 18 operators, adds dynamic value input types, composite nesting at any depth, and collapsible tree nodes.

## Approach

Full refactor: extract the tree editor from `page.tsx` into `ConditionTreeEditor` (orchestrator) with 4 sub-components:

| Sub-component | Responsibility |
|--------------|----------------|
| `CompositeNode` | Renders AND/OR/NOT, manages children, collapse toggle, add-child buttons |
| `AtomicNode` | Renders operator + value input row for leaves |
| `OperatorSelector` | Dropdown categorized by operator category, icons per group |
| `ValueInput` | Dispatches to correct widget per operator (text/number/JSON/array/hidden) |

Recursive tree walks for serialization (→ API JSON) and hydration (← API JSON) stay in the editor. State uses `useReducer` for predictable composite→atomic mutations.

## Affected Areas

| Area | Change | Description |
|------|--------|-------------|
| `frontend/src/pages/admin-reglas/page.tsx` | Modified | Extract tree logic, reduce ~1705→~800 lines |
| `frontend/src/components/admin-reglas/ConditionTreeEditor.tsx` | **New** | Orchestrator with useReducer state, tree walk helpers |
| `frontend/src/components/admin-reglas/CompositeNode.tsx` | **New** | AND/OR/NOT node, collapse, add-child buttons |
| `frontend/src/components/admin-reglas/AtomicNode.tsx` | **New** | Leaf node: fuente_datos + OperatorSelector + ValueInput |
| `frontend/src/components/admin-reglas/OperatorSelector.tsx` | **New** | Categorized dropdown with all 18 operators |
| `frontend/src/components/admin-reglas/ValueInput.tsx` | **New** | Dynamic widget dispatcher per operator category |
| `frontend/src/lib/api-reglas.ts` | Modified | Minor `CondicionTree` type updates if needed |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing rules fail to render after refactor | Low | Snapshot one existing rule's JSON, compare tree hydration output |
| Operator list drifts from engine | Low | Generate `OPERADORES_ATOMICOS` from engine's registry comment block |
| Complex evaluators (sala_obs_check, etc.) have no value input | Low | Handle per operator category — hidden input, label-only display |

## Rollback Plan

1. Revert `page.tsx` to its pre-refactor state via `git checkout`
2. Delete the 5 new component files
3. Restore `api-reglas.ts` types via `git checkout`
4. No DB changes to roll back

## Dependencies

None — all changes are frontend-only. Engine backend is read-only reference.

## Success Criteria

- [ ] All 18 engine operators selectable in the UI with correct input widgets
- [ ] AND/OR/NOT nodes accept composite children (nested trees of arbitrary depth)
- [ ] Existing rules with conditions render identically (tree shape unchanged)
- [ ] Save produces JSON that `rule_service.py` stores correctly
- [ ] Collapse/expand works on composite nodes without data loss
- [ ] `FUENTES_DATOS` includes `catalog.*`, `group.*`, `contract.*` paths
