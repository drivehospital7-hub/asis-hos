# Design: Condition Tree Editor Refactor

## Technical Approach

Extract `ConditionCondicionTree` from the 1705-line `page.tsx` into a standalone `ConditionTreeEditor` component with 5 sub-components. Replace `useState`+callback deep-clone pattern with `useReducer` for predictable state transitions. Expand operator set from 8→18 with categorized dropdowns and dynamic value input widgets per operator category.

## Architecture Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| `useReducer` vs `useState`+callbacks | `useState` uses `JSON.parse(JSON.stringify(dclone))` on every mutation — O(n) copy even for small changes. `useReducer` gives O(1) dispath with targeted updates, easier debugging via action logs, and no stale-closure risk. | **useReducer** — ADD_CHILD, UPDATE_NODE, REMOVE_NODE, TOGGLE_COLLAPSE, LOAD_TREE, REORDER_CHILDREN. |
| Recursive render vs flat list with indentation | Recursive matches existing code, handles arbitrary depth naturally, simpler JSX. Flat list needs manual depth tracking and parent references. | **Recursive** — CompositeNode renders children via `.condiciones` map; each child independently manages its subtree. |
| Static operator constants vs API-driven | API-driven ensures perfect sync but adds latency, caching complexity, and a new endpoint. Static constants keep the UI fast and simple; operator set changes infrequently. | **Static operators.ts** — all 18 operators with categories and value-type mapping (R7 — manual sync with evaluators.py). |
| JSON textarea vs structured form for `exists_in_db` | Structured form (table, field inputs) is better UX but adds complexity for a single operator. JSON textarea works and the value shape is simple: `{"table":"...", "field":"..."}`. | **JSON textarea** — MVP; structured form deferred until a 2nd operator needs it. |

### Additional Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| Collapse state in reducer vs separate useState | Reducer is cleaner — collapse is tree state, just not serialized. Separate state would need parallel tree traversal. | **Reducer with serialize step** — `TOGGLE_COLLAPSE` sets `_collapsed` on node; `serializeTree()` strips `_collapsed` before API call. |
| Module-level `_tempNodeId` vs UUID | Temp counter works but leaks across renders. UUID/crypto.randomUUID() is safer and avoids collisions. | **crypto.randomUUID()** — generates unique IDs; no shared mutable state. |

## Data Flow

```
page.tsx RuleDetailForm
  ├── form fields (nombre, dominio, severidad, etc.)
  ├── tree: CondicionTree[] ─────── useState
  └── ConditionTreeEditor
       ├── useReducer(treeState, action)
       ├── serializeTree(state) → CondicionTree[]  (on save, strips _collapsed)
       ├── CompositeNode (recursive)
       │   ├── type selector [AND|OR|NOT]
       │   ├── collapse toggle → dispatches TOGGLE_COLLAPSE
       │   ├── [+ Atomic] → dispatches ADD_CHILD(parentId, "atomic")
       │   ├── [+ Composite] → dispatches ADD_CHILD(parentId, "composite")
       │   ├── [×] Remove → dispatches REMOVE_NODE(nodeId)
       │   └── children.map(child =>
       │       child.tipo === "composite" ? CompositeNode : AtomicNode)
       └── AtomicNode
           ├── FUENTES_DATOS select
           ├── OperatorSelector (categorized dropdown)
           │   └── groups: Comparison | String | Set | DB | Complex
           └── ValueInput (dispatches by operator category)
               ├── operator in [eq,gt,gte,lt,lte]        → <input type="number">
               ├── operator in [contains,regex]           → <input type="text">
               ├── operator === "regex_extract"            → <textarea> (JSON)
               ├── operator in [in,set_contains_all,set_intersects,cat_in] → ArrayEditor
               ├── operator === "exists_in_db"             → <textarea> (JSON)
               └── operator in [ent_code_match,sala_obs_check,centro_costo_check,all_values_match,cups_contratado] → <span> (hidden/label)
```

### Reducer Actions

| Action | Payload | Effect |
|--------|---------|--------|
| `LOAD_TREE` | `treeData: CondicionTree[]` | Replace entire state |
| `ADD_CHILD` | `parentId, tipo` | Push new atomic/composite child to `condiciones[]` |
| `UPDATE_NODE` | `nodeId, field, value` | Set field on node (recursive walk) |
| `REMOVE_NODE` | `nodeId` | Remove node from parent's `condiciones[]` |
| `TOGGLE_COLLAPSE` | `nodeId` | Toggle boolean `_collapsed` |
| `REORDER_CHILDREN` | `parentId, sourceIndex, destIndex` | Reorder `condiciones[]` (nice-to-have) |

### Serialization Contract

```
page.tsx tree state (CondicionTree[] includes _collapsed)
  → ConditionTreeEditor.serializeTree() strips _collapsed
  → PUT /api/reglas/<id> { ..., condiciones: cleanTree }
```

Deserialization (hydration):
```
GET /api/reglas/<id> → rule.condiciones (no _collapsed)
  → ConditionTreeEditor hydrates, adds _collapsed: false to composites
  → rendered with all composites expanded (R8 default)
```

## Operator → Value Type Mapping (from evaluators.py)

| Category | Operators | Value Widget | Value Type |
|----------|-----------|-------------|------------|
| Comparison | eq, gt, gte, lt, lte | NumberInput | number |
| String | contains, regex | TextInput | string |
| String | regex_extract | JSON textarea | pattern string |
| Set | in, set_contains_all, set_intersects | ArrayEditor | string[] |
| Set | cat_in | TextInput | catalog key string |
| DB | exists_in_db | JSON textarea | `{table, field}` |
| DB | ent_code_match, sala_obs_check, centro_costo_check | Hidden/label | context-derived |
| Complex | all_values_match | NumberInput | threshold int |
| Complex | cups_contratado | Hidden/label | context-derived |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/admin-reglas/page.tsx` | Modify | Replace tree section + helpers with `<ConditionTreeEditor>`; remove `ConditionCondicionTree`, `updateNodeInTree`, `removeNodeFromTree`, `addChildToNode`, `_tempNodeId` (~200 lines removed) |
| `frontend/src/components/admin-reglas/ConditionTreeEditor.tsx` | **Create** | Orchestrator: useReducer, tree state, load/serialize helpers |
| `frontend/src/components/admin-reglas/CompositeNode.tsx` | **Create** | Composite node: type select, collapse, add-child buttons, recursive children |
| `frontend/src/components/admin-reglas/AtomicNode.tsx` | **Create** | Leaf node: fuente_datos select + OperatorSelector + ValueInput + remove |
| `frontend/src/components/admin-reglas/OperatorSelector.tsx` | **Create** | Categorized dropdown with 18 operators, grouped by category |
| `frontend/src/components/admin-reglas/ValueInput.tsx` | **Create** | Dynamic widget dispatcher: number/text/json/array/hidden |
| `frontend/src/components/admin-reglas/operators.ts` | **Create** | Shared constants: all 18 operators, categories, categories list, FUENTES_DATOS (with catalog.*, group.*, contract.*), OPERADORES_COMPOSITE |
| `frontend/src/lib/api-reglas.ts` | Modify | Minor: export `FUENTES_DATOS` type if needed (existing `CondicionTree` interface is adequate) |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `operators.ts` constants | All 18 operators present, correct categories, FUENTES_DATOS includes new prefixes |
| Unit | `useReducer` reducer | Each action type produces correct state transition; serialize strips `_collapsed`; hydrate adds `_collapsed: false` |
| Unit | `OperatorSelector` | Renders all categories, selecting operator calls onChange |
| Unit | `ValueInput` | Correct widget per operator category; hidden for context-based evaluators |
| Unit | `CompositeNode` | Renders children recursively, collapse toggle works, add-child dispatches correct action |
| Integration | Tree rendering | Existing rule data renders with same tree shape after refactor (compare snapshot) |
| Integration | Save round-trip | serializeTree output matches API expected JSON format |

## Open Questions

- None — all decisions are documented and scoped. R7 manual sync is acceptable because evaluators.py changes infrequently.

## Migration / Rollout

No migration required — frontend-only change. Existing rules load from DB and hydrate via `LOAD_TREE` action; the JSON shape is identical. Rollback: revert page.tsx, delete 6 new files.
