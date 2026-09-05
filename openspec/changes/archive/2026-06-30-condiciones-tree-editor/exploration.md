## Exploration: Condition Tree Editor Improvements

### Current State

The condition tree editor lives in `frontend/src/pages/admin-reglas/page.tsx` inside the `ConditionCondicionTree` component (lines 788-910). It renders a recursive tree of AND/OR/NOT composite nodes with atomic leaf nodes.

**Key limitations discovered:**

1. **No composite children** — `addChildToNode` (line 943) always creates `tipo: "atomic"` with `operador: "eq"`. Users CANNOT nest AND/OR/NOT children inside other composites to build deeper trees.

2. **Missing operators** — `OPERADORES_ATOMICOS` (line 73) lists only 8: `["eq", "gt", "gte", "lt", "lte", "in", "contains", "regex"]`. The engine has **18 evaluators** registered (see full list below).

3. **Hardcoded text input for valor_esperado** — line 870 always renders `<input type="text">`. But operators need different input types:
   - `exists_in_db` expects JSON object `{"table": "...", "field": "..."}`
   - `in`, `set_contains_all`, `set_intersects` expect arrays
   - `all_values_match` expects a number (threshold)
   - `centro_costo_check`, `sala_obs_check` don't need valor_esperado at all

4. **No collapsible tree** — All nodes render expanded. A rule with 15+ conditions becomes unmanageable.

5. **Incomplete FUENTES_DATOS** — Lists 31 `invoice.*` and `date.*` fields, but MISSES `catalog.*`, `contract.*`, and `group.*` provider paths.

6. **Conditions are NOT shared** — Each rule has its own `condiciones` table entries with `regla_id` FK. `_clone_conditions` creates deep copies on versioning. No shared condition library exists.

### All Engine Operators

Source: `app/services/engine/evaluators.py` lines 54-814 (registry built at line 840-843).

| # | Operator | Class | valor_esperado type | Requires context? | Category |
|---|----------|-------|---------------------|-------------------|----------|
| 1 | `eq` | `EqEvaluator` | string/number | No | Comparison |
| 2 | `gt` | `GtEvaluator` | number (coerced) | No | Comparison |
| 3 | `gte` | `GteEvaluator` | number (coerced) | No | Comparison |
| 4 | `lt` | `LtEvaluator` | number (coerced) | No | Comparison |
| 5 | `lte` | `LteEvaluator` | number (coerced) | No | Comparison |
| 6 | `in` | `InEvaluator` | array/list | No | Set |
| 7 | `contains` | `ContainsEvaluator` | string | No | String |
| 8 | `regex` | `RegexEvaluator` | string (pattern) | No | String |
| 9 | `regex_extract` | `RegexExtractEvaluator` | string (pattern) | No | String |
| 10 | `exists_in_db` | `ExistsInDBEvaluator` | JSON `{"table","field"}` | Yes (session) | DB |
| 11 | `ent_code_match` | `CodigoEntidadCoincideEvaluator` | string (regex pattern) | Yes (invoice) | Cross-field |
| 12 | `sala_obs_check` | `SalaObservacionEvaluator` | ignored | Yes (invoice) | Complex |
| 13 | `centro_costo_check` | `CentroCostoCheckEvaluator` | ignored | Yes (invoice) | Complex |
| 14 | `cat_in` | `CatalogInEvaluator` | string (catalog key) | Yes (session) | DB |
| 15 | `set_contains_all` | `SetContainsAllEvaluator` | array/list | No | Set |
| 16 | `set_intersects` | `SetIntersectsEvaluator` | array/list | No | Set |
| 17 | `all_values_match` | `AllValuesMatchEvaluator` | number (threshold) | No | Aggregation |
| 18 | `cups_contratado` | `CupsContratadoEvaluator` | ignored | Yes (session+invoice) | Complex |

**Frontend has only operators 1-8.** Operators 9-18 have zero UI support. Operators 11-13, 18 are context-aware evaluators that read from `context.invoice_data` directly — they don't need `fuente_datos` or `valor_esperado` in the traditional sense.

#### Input types needed per operator category:

| Category | Operators | Input widget | Notes |
|----------|-----------|-------------|-------|
| Comparison | eq, gt, gte, lt, lte | text or number | Simple value |
| String | contains, regex, regex_extract | text | Text pattern |
| Set | in, set_contains_all, set_intersects | array editor (tag input or JSON) | Comma-separated or JSON array |
| DB lookup | exists_in_db | JSON editor `{"table","field"}` | Autocomplete table/field names? |
| Catalog | cat_in | text | Catalog key name |
| Aggregation | all_values_match | number | Threshold value |
| Complex | ent_code_match, sala_obs_check, centro_costo_check, cups_contratado | no input / JSON config | Context-based, valor_esperado optional |

### Data Sources (FUENTES_DATOS vs providers)

Source: `app/services/engine/providers.py` — 5 registered providers.

| Provider prefix | Registered | In FUENTES_DATOS? | Sample paths |
|----------------|------------|-------------------|--------------|
| `invoice` | ✅ Yes | ✅ Yes (29 fields) | `invoice.vlr_subsidiado`, `invoice.convenio_facturado` |
| `date` | ✅ Yes | ✅ Yes (2 fields) | `date.edad`, `date.horas` |
| `catalog` | ✅ Yes | ❌ MISSING | `catalog.profesionales[CODE]`, `catalog.profesionales[CODE].tipo` |
| `contract` | ✅ Yes | ❌ MISSING | `contract.ide_contrato.expected[entidad][codigo]` |
| `group` | ✅ Yes | ❌ MISSING | `group.collect_set_codigo`, `group.collect_value_counts` |

**`catalog.*` paths** — used by the `CatalogProvider` which resolves `catalog.profesionales[CODE]` and `catalog.profesionales[CODE].tipo`. This is an in-memory cache loaded via `load_profesionales(domain, dict)`.

**`contract.*` paths** — `ContractProvider` is a placeholder returning None. Not yet used.

**`group.*` paths** — `GroupProvider` resolves from `context.invoice_data`. Used by group-by rules with `collect_set_*` and `collect_value_counts` aggregations.

### Tree Structure: API ↔ Frontend

**Backend** (`rule_service.py`):
- DB stores conditions as flat rows in `condiciones` table with `padre_id` self-reference
- `_build_condition_tree()` (line 24-49) assembles flat rows into a nested dict tree
- `_store_condition_tree()` (line 165-186) recursively flattens a nested tree back into `padre_id` rows
- `_clone_conditions()` (line 70-106) handles deep copy with ID remapping
- `valor_esperado` is stored as `JSONB` column — native PostgreSQL JSON support

**Frontend** (`api-reglas.ts`):
- `CondicionTree` interface (lines 31-42) has `condiciones?: CondicionTree[]` for nested children, plus `[key: string]: unknown` for dynamic field access
- `Regla.condiciones` is `CondicionTree[] | null | undefined`
- Tree is sent/received as nested JSON — works because `JSONB` stores/returns it transparently

**Engine** (`condition_evaluator.py`):
- `build_tree()` uses `_children` key internally (not `condiciones`)
- This is a naming mismatch: frontend uses `condiciones`, engine uses `_children`
- The frontend tree is sent directly to the API and stored via `_store_condition_tree()` which reads `node.get("condiciones", [])`

### Affected Areas

- `frontend/src/pages/admin-reglas/page.tsx` — MAIN: `ConditionCondicionTree` component (lines 797-910), tree helpers (lines 919-962), constants (lines 69-106), state management (lines 525-547)
- `frontend/src/lib/api-reglas.ts` — `CondicionTree` type updates if needed, but current interface is flexible enough
- `app/services/reglas/rule_service.py` — Backend changes only if shared conditions are added; current recursive tree handling works correctly
- `app/services/engine/evaluators.py` — Read-only reference for the complete operator list
- `app/services/engine/providers.py` — Read-only reference for data source completeness

### Approaches

1. **Minimal Patch — Extend existing UI**
   - Add missing operators to `OPERADORES_ATOMICOS`
   - Add `addCompositeChildToNode` beside `addChildToNode`
   - Add operator-based input switching (text vs JSON textarea vs number vs hidden)
   - Complete `FUENTES_DATOS` with `catalog.*`, `group.*`, `contract.*`
   - Pros: Low risk, fast to implement, fixes the most painful gaps
   - Cons: Still no collapsible tree (UX degrades with 20+ conditions), no visual categorization, the component keeps growing in complexity
   - Effort: Low-Medium

2. **Full Refactor — Extract Tree Editor Component**
   - Build a standalone `ConditionTreeEditor` component with:
     - Dedicated sub-components: `CompositeNode`, `AtomicNode`, `OperatorSelector`, `ValueInput`
     - Dynamic input dispatching per operator category
     - Collapsible/expandable nodes with visual indentation
     - "Add composite child" + "Add atomic child" buttons on composites
     - Operator categorization (comparison, string, set, DB, complex)
     - Complete FUENTES_DATOS including all provider paths
   - Pros: Clean architecture, excellent UX, easily maintainable component
   - Cons: More code, requires careful testing of all operator × input combinations
   - Effort: Medium

3. **Full Refactor + Shared Conditions**
   - Everything in Approach 2 PLUS:
     - New backend endpoint: `POST /api/condiciones` (shared condition templates)
     - Rules reference shared conditions via `condicion_ref_id`
     - Editing a shared condition propagates to all referencing rules
     - UI shows "shared" badge and links to source
   - Pros: Eliminates rule drift, single source of truth for common patterns
   - Cons: Backend changes needed (new table/model/API), versioning complexity for shared references, migration of existing conditions
   - Effort: High

### Recommendation

**Approach 2** — Full refactor of the tree editor.

Reasoning:
- Approach 1 leaves the component with the same structural problems (no collapsible tree, no input specialization) — it's tech debt that will need revisiting
- Approach 3 (shared conditions) is a separate concern with significant backend implications. It should be a different change
- The condition tree is the CORE of the rule editor UX. Making it robust pays off every time someone edits a rule
- The current 1705-line page.tsx is already too large — extracting the tree editor is an architectural improvement that aligns with SRP

**For a separate follow-up**: shared conditions. The current codebase has no infrastructure for it, and the use case (common condition patterns reused across rules) is valuable but needs its own exploration.

### Risks

- **Backward compatibility**: Existing rules with conditions stored in the DB must render correctly in the new editor. The tree structure format should not change.
- **Engine divergence**: If the operator list in the frontend doesn't match the engine's registry, users could create rules with operators the engine doesn't understand. The registry in `evaluators.py` is the single source of truth.
- **Complex evaluators**: Operators like `sala_obs_check`, `centro_costo_check`, and `cups_contratado` are complex evaluators that don't fit the traditional "field + operator + value" pattern. The UI needs to handle them gracefully — show them as atomic nodes with a descriptive label and no value input.
- **JSON input validation**: `exists_in_db` with its `{"table", "field"}` JSONB structure needs validation to prevent typos in table/field names. A dropdown selector backed by DB schema introspection would be ideal but is a significant addition.

### Ready for Proposal

Yes
