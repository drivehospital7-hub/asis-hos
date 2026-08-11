# Delta for admin-reglas-ui

## MODIFIED Requirements

### R2: Rule Detail / Edit Form

The rule detail view MUST show an editable form with fields: `nombre` (text), `descripcion` (textarea), `dominio` (select from allowed values), `severidad` (select: baja/media/alta/critica), `prioridad` (number). Below the basic fields, a **condition tree builder** SHALL allow editing the rule's condition tree.

Each tree node SHALL be:
- **Composite**: type AND/OR/NOT with a list of child nodes, each child removable via [×] button and new children addable via [+]. Composite nodes SHALL accept BOTH atomic AND composite children, enabling unlimited nesting depth. Composite nodes SHALL be collapsible/expandable via a toggle.
- **Atomic**: operator select + field selector (`FUENTES_DATOS`) + value input

The operator select SHALL support all 18 operators, categorized:
- **Comparison**: eq, gt, gte, lt, lte
- **String**: contains, regex, regex_extract
- **Set**: in, cat_in, set_contains_all, set_intersects
- **DB**: exists_in_db, ent_code_match, sala_obs_check, centro_costo_check
- **Complex**: all_values_match, cups_contratado

Value input SHALL change dynamically per operator category: **text** for string operators, **number** for comparison, **JSON editor** for regex_extract, **array editor** for set operators, or **hidden/label** for DB/complex operators (value derived from context).

`FUENTES_DATOS` SHALL include `catalog.*`, `group.*`, `contract.*` prefixes in addition to existing field selectors.

The tree SHALL render with visual indentation and collapsible composite nodes. Save SHALL serialize the tree as JSON and `PUT /api/reglas/<id>`. Collapse state SHALL be preserved in local component state during editing but NOT serialized to the API.

(Previously: 8 operators with single text input, atomic-only children, no collapsible tree, limited FUENTES_DATOS)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Load for edit | user clicks "Editar" on a rule | `GET /api/reglas/<id>` returns rule with nested conditions | form populated, condition tree rendered with collapsible composite nodes |
| Add composite node at depth | user clicks [+] on a composite child, selects AND | new AND node appears as nested child | tree updated at arbitrary depth, Save sends correct JSON |
| Add atomic leaf with categorized operator | user clicks [+] on AND node, selects comparison→eq with number value | new atomic leaf appears with number input | categorized dropdown shows operators by group |
| Remove node | user clicks [×] on a child node | node removed from tree | Save sends tree without that node |
| Collapse/expand composite | user clicks collapse toggle on AND node | children hidden/shown | toggle reflects expanded state |
| Dynamic value input | user selects operator `in` | value input switches to array editor | array editor allows adding/removing values |
| Save changes | user edits nombre + adds conditions | clicks "Guardar" | `PUT /api/reglas/<id>` called, success toast shown, returns to list |
| Validation error | user submits with empty nombre | clicks "Guardar" | inline error on nombre field, no API call made |

## ADDED Requirements

### R7: Operator Registry Sync

The UI operator list MUST match the engine's evaluators.py operator registry. A shared constant file SHALL define `OPERADORES_ATOMICOS` as the single source of truth for both the categorized dropdown options and operator→value-type mapping. When the engine registry is updated, the UI constant SHALL be updated in the same change.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Operadores match registry | engine evaluators.py defines 18 operators | UI loads rule editor | all 18 operators selectable in categorized dropdown |
| New operator added | engine adds operator to registry | shared constant updated | new operator appears in correct category |

### R8: Tree State Persistence

The tree collapse state SHALL be preserved during editing via local component state. Collapse state MUST NOT be serialized to API JSON — only condition tree structure and values are sent on save. On component remount (e.g., navigating away and back), all composite nodes SHALL default to expanded.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Collapse survives re-render | user collapses a composite node | local state update triggers re-render | composite node remains collapsed |
| State not sent to API | user collapses AND node, then clicks Guardar | `PUT /api/reglas/<id>` called | request body contains condition tree only, no collapse state |
| Remount resets collapse | user navigates away and back to rule edit | component remounts | all composite nodes default to expanded |
