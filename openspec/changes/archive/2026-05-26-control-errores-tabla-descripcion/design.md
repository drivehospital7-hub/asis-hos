# Design: Control-errores-table-description-dominance

## Technical Approach

Adjust CSS column widths and max-width constraints to let the Description column expand, then align the facturador editor sizing with the dynamic pattern already used by the global editor — pure frontend changes, no backend impact.

## Architecture Decisions

### Decision: Rect source for facturador editor sizing

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Use `btn.getBoundingClientRect()` (existing `rect`) | Editor would match the icon button's ~30×30px bounding box — too small for text input | ❌ Rejected |
| Use `btn.closest('td').getBoundingClientRect()` | Matches the actions `<td>` dimensions (~row-height × column-width), giving a sensible base size | ✅ **Chosen** |
| Keep hardcoded 300×120px | Simple but ignores the dynamic-sizing pattern established by `openEditor()` | ❌ Rejected |

**Rationale**: The proposal's risk register already flags this ("Use rect from `<td>` parent, not the icon button itself"). The `openEditor()` function uses the cell's rect for sizing; the facturador should use its closest semantic container (the actions `<td>`).

### Decision: Column width strategy

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Percentage widths | Simple, proportional. At narrow viewports the table already clips (wrapper has no `overflow-x`). | ✅ **Chosen** — matches existing pattern |
| `minmax(25%, 1fr)` grid | More flexible but introduces a different layout model mid-page for a single table | ❌ Rejected |

**Rationale**: Percentages are the existing convention. Changing to grid for one table would be inconsistent with the rest of the page.

## Data Flow

```
User loads /control-errores
  → Browser renders <table> with 8 `<th>` columns
  → CSS `th:nth-child(n)` rules assign widths
  → Cell content in Description column (data-field="observacion") now has ~35% width
     and no max-width cap → long text wraps naturally

User clicks facturador note button
  → openFacturadorEditorImpl(errorId, btn)
  → rect = btn.closest('td').getBoundingClientRect()
  → Editor positioned right of button, sized to rect dimensions
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/static/css/legacy/control_errores.css` | Modify | Column widths (L245-250), max-width on text cells (L738-745), add Factura-specific rule |
| `app/templates/control_errores.html` | Modify | `openFacturadorEditorImpl()` width/height (L500-502) |

### CSS Changes

**1. Column widths (L245-250)**

Before:
```css
.table thead th:nth-child(1) { width: 10%; }
.table thead th:nth-child(2) { width: 10%; }
.table thead th:nth-child(3) { width: 11%; }
.table thead th:nth-child(5) { width: 13%; }
.table thead th:nth-child(6) { width: 8%; }
.table thead th:nth-child(7) { width: 8%; }
```

After:
```css
.table thead th:nth-child(1) { width: 6%; }   /* Validador: 10% → 6% */
.table thead th:nth-child(2) { width: 8%; }   /* Factura: 10% → 8% */
.table thead th:nth-child(3) { width: 8%; }   /* Creado: 11% → 8% */
.table thead th:nth-child(4) { width: 11%; }  /* Categoría: auto → 11% */
.table thead th:nth-child(5) { width: 36%; }  /* Descripción: 13% → 36% */
.table thead th:nth-child(6) { width: 15%; }  /* Responsable: 8% → 15% */
.table thead th:nth-child(7) { width: 6%; }   /* Pendiente: 8% → 6% */
.table thead th:nth-child(8) { width: 10%; }  /* Acciones: auto → 10% */
```

Column mapping:
| nth-child | Column | Original | Implementado |
|-----------|--------|----------|-------------|
| 1 | Validador | 10% | 6% |
| 2 | Factura | 10% | 8% |
| 3 | Creado | 11% | 8% |
| 4 | Categoría | auto | 11% |
| 5 | Descripción | 13% | 36% |
| 6 | Responsable | 8% | 15% |
| 7 | Pendiente | 8% | 6% |
| 8 | Acciones | auto | 10% |

**2. max-width on `.editable-cell[data-type="text"]` (L738-745)**

Before:
```css
.editable-cell[data-type="text"], .new-row-cell[data-type="text"] {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;               /* ← remove this */
  height: 20px;
  line-height: 20px;
}
```

After:
```css
.editable-cell[data-type="text"], .new-row-cell[data-type="text"] {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* max-width removed — let column width govern */
  height: 20px;
  line-height: 20px;
}
```

**3. Add Factura-specific max-width** (insert after the block above, before L746):

```css
.editable-cell[data-field="factura"], .new-row-cell[data-field="factura"] {
  max-width: 120px;
}
```

**Affected cells impact**: Only two `data-type="text"` fields exist — `factura` (4 occurrences across full table + new-row template) and `observacion` (4 occurrences). Removing the global cap frees `observacion` while the new rule keeps `factura` narrow at 120px. The existing `.editable-cell[data-field="observacion_facturador"]` rule (L746, max-width: 300px) is NOT `data-type="text"` and is unaffected.

### JS Changes

**File**: `app/templates/control_errores.html`
**Function**: `openFacturadorEditorImpl` (L489)

Current (L490-502):
```js
const rect = btn.getBoundingClientRect();
// ...
editor.style.width = '300px';
editor.style.height = '120px';
editor.style.minHeight = '120px';
```

After:
```js
const btnRect = btn.getBoundingClientRect();
const rect = btn.closest('td').getBoundingClientRect();
// ...
editor.style.width = rect.width + 'px';
editor.style.height = rect.height + 'px';
editor.style.minHeight = '';
```

**Why two rects**: `btnRect` is used for positioning (top, left offset — already at L498-499, kept as-is). `rect` from the parent `<td>` provides sensible dimensions matching the row height and actions-column width. This follows `openEditor()`'s pattern at L720-725 where `rect` comes from the cell element.

## Edge Cases

| Case | Behavior | Notes |
|------|----------|-------|
| Empty description (`observacion: ''`) | Cell shows `-` (template fallback at L420). Max-width removed but column still gets 35% allocation — empty cell renders as blank space, proportional to table. | Acceptable — table layout distributes width regardless of content. |
| Long factura code (>15 chars) | Capped at 120px with `overflow: hidden; text-overflow: ellipsis`. Content visible on hover/cell click. | Same behavior as before, tighter cap from 150→120px. |
| Facturador button in narrow viewport | Editor opens to the right of the button. If viewport is too narrow, editor may clip. | Pre-existing issue (not in scope). Same behavior as current code. |
| Facturador editor with long text | Editor height matches `<td>` row height. Textarea inside has `min-height:100%` and `resize:none`. Long content scrolls. | Same as current `openEditor()` behavior for text cells. |
| `btn.closest('td')` returns `null` | Button must be inside a `<td>` per HTML structure (L434-441, L1291-1298). Cannot happen unless template changes. | Defensive: use `btn.parentElement` as fallback. |

## Verification

### Manual Testing Checklist

1. **Column widths**: Open `/control-errores` with real data. Inspect `<th>` elements in DevTools. Verify:
   - nth-child(1): 6%, nth-child(2): 8%, nth-child(3): 8%
   - nth-child(4): 11%, nth-child(5): 36%, nth-child(6): 15%
   - nth-child(7): 6%, nth-child(8): 10%
   - Description column is visibly ~4× wider than Factura

2. **Max-width removed**: Create or find a row with long description text (>30 chars). Verify the text is NOT clipped at 150px (previously it was). Cell should display full width governed by the 35% column.

3. **Factura stays capped**: Find a row with long factura code. Verify it truncates with ellipsis at ~120px. Hover → cell click opens editor with full value.

4. **Facturador editor sizing**: Click a facturador note icon. Verify editor dimensions match the actions `<td>` rect (not the icon button rect). Editor should not be 300×120px hardcoded.

5. **Regression — global editor**: Click a Factura cell or Description cell. Verify `openEditor()` still opens with correct cell-covering dimensions (unaffected code path).

6. **New-row template**: Click "Agregar" to create a new row. Verify the new factura cell still opens its editor correctly.

### Rollback

```bash
git revert HEAD --no-edit
```

Single commit reverts all 5 CSS lines + 3 JS lines.
