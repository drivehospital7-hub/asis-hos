# Design: Añadir columna Rol a control-errores y ensanchar la tabla

## Technical Approach

Service-layer enrichment following the existing `imagenes_count` pattern: `get_errores()` builds a `nombre_completo → rol` map from `get_facturadores()` and injects `responsable_rol` into each error dict at list time. No JSON schema change. The frontend reads `e.responsable_rol` in `renderTable()`, `renderFilteredTable()`, and `addNewRow()`, with `"-"` fallback. 4 `colspan="8"` → `colspan="9"`. CSS frees 11% width from Descripción (36%→30%) and Responsable (15%→10%), allocates 8% to new Rol column at nth-child(7).

## Architecture Decisions

### Decision: Dynamic enrichment at service layer

| Option | Tradeoff | Decision |
|--------|----------|----------|
| **Computed at list time** (chosen) | No migration, no stale data, same pattern as `imagenes_count` | ✅ |
| Stored in JSON per error | Requires migration, becomes stale when user roles change, defeats purpose | ❌ |

**Rationale**: `get_facturadores()` already returns each user with a `"rol"` key. Enriching at the service layer is zero-migration, zero-staleness, and consistent with how `imagenes_count` is injected in `errores_storage.listar_errores()`.

### Decision: Column insertion between Responsable and Pendiente

**Choice**: New Rol column at position 7 (after Responsable, before Pendiente/Estado).
**Rationale**: Logical grouping — who is assigned + their role → then status. Avoids breaking existing responsive or nth-child assumptions for columns 1-6 and 8-9. The `width: 6%;` (Estato) and `width: 10%;` (Acciones) already in the CSS remain unchanged.

### Decision: Width reallocation

| Column | Before | After | Delta |
|--------|--------|-------|-------|
| Descripción | 36% | 30% | −6% |
| Responsable | 15% | 10% | −5% |
| Rol (new) | — | 8% | +8% |
| Others | unchanged | unchanged | 0% |

**Rationale**: Descripción had the most slack (36%) and can afford 6% loss without wrapping. Responsable has enough from 10%. 8% for the new Rol column is enough for short labels ("facturador", "medico", "admin").

### Decision: Empty fallback is `"-"`

**Choice**: When `get_facturadores()` is empty or the responsible's name has no match in the map, display `"-"`.
**Rationale**: Consistent with existing fallback pattern (e.g., `escapeHtml(e.observacion||'-')` in template line 420). Also covers the edge case where the user was deleted but errors reference them.

### Decision: CSV column order mirrors table

**Choice**: New Rol column inserted at position 7 in CSV headers and row builder, between "Responsable" and "Observación del Facturador".
**Rationale**: Maintaining the same visual order between table and CSV prevents operator confusion when cross-referencing.

## Data Flow

```
User loads /control-errores
    │
    ▼
get_errores()                          ← app/services/control_errores_service.py
    │
    ├── listar_errores()               ← app/utils/errores_storage.py (raw JSON)
    │   └── injects imagenes_count
    │
    ├── get_facturadores()             ← app/utils/users_store.py
    │   └── returns [{nombre_completo, rol, ...}]
    │
    ├── Build map: nombre_completo → rol
    │
    └── For each error:
        error["responsable_rol"] = map.get(error["responsable"], "-")
    │
    ▼
JSON response to frontend:
    { status: "success", data: { errores: [{..., responsable_rol: "facturador"}, ...] } }
    │
    ▼
renderTable() / renderFilteredTable() / addNewRow()
    │
    ├── <th>Rol</th> at column 7
    ├── <td>${escapeHtml(e.responsable_rol || '-')}</td>
    ├── colspan="8" → colspan="9" (4 occurrences)
    └── exportToCSV() headers + rows include Rol at position 7
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/control_errores_service.py` | Modify | `get_errores()` builds rol map from `get_facturadores()`, enriches each error with `responsable_rol` |
| `app/templates/control_errores.html` | Modify | Add `<th>Rol</th>`, `<td>` in 3 render funcs, 4× `colspan="8"`→`colspan="9"`, CSV export sync |
| `app/static/css/legacy/control_errores.css` | Modify | nth-child(7) → ROL 8%; nth-child(5)=30%, nth-child(6)=10%; shift 7→8, 8→9 |
| `tests/services/test_control_errores_service.py` | Modify | Add unit test for rol enrichment in `get_errores()` |
| `tests/services/test_control_errores_integration.py` | Modify | Add integration test for rol in GET response |

## Interfaces / Contracts

### Enriched error dict (at rest vs over the wire)

```python
# JSON-stored keys (unchanged)
{
    "id": "uuid",
    "responsable": "JUAN PEREZ",       # nombre_completo from facturadores
    "rol": "facturador",                # ← already in get_facturadores() response
}

# Over-the-wire (enriched at list time, NOT stored)
{
    ...existing keys...,
    "responsable_rol": "facturador",    # ← NEW, computed
    "imagenes_count": 2,                # ← existing computed field
}
```

### Map construction

```python
# In get_errores(), after listar_errores():
facturadores = get_facturadores()
rol_map = {f["nombre_completo"]: f["rol"] for f in facturadores}
for error in errores:
    error["responsable_rol"] = rol_map.get(error.get("responsable", ""), "-")
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `get_errores()` enriches each error with `responsable_rol` from `get_facturadores()` map | Patch `listar_errores` + `get_facturadores`, assert `responsable_rol` in response data |
| Unit | Fallback to `"-"` when facturadores list is empty or responsable not in map | Patch `get_facturadores` → return `[]`, assert `"-"` for all |
| Unit | `get_errores()` still works when `get_facturadores()` returns users with no `"rol"` key | Include a facturador dict without `"rol"`, use `.get("rol", "-")` defensive fallback |
| Integration | GET `/api/control-errores` returns `responsable_rol` in every error dict | Use `app_client` fixture, mock JSON storage, assert response JSON shape |
| Integration | CSV export includes Rol column with correct data | (Covered by template rendering, not backend — manual review of generated CSV) |

## Migration / Rollout

No migration required — rol is computed dynamically. Rollback: revert the 5 files listed above. No data loss or schema drift.

## Open Questions

- [ ] None — architecture is well-defined by the proposal and existing patterns.
