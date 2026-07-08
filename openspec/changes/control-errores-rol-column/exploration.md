## Exploration: control-errores-rol-column

### Current State

**What is control-errores?**
A Flask blueprint (`app/routes/control_errores.py`) serving a Jinja2 dashboard at `/control-errores` for tracking billing errors ("novedades") in the Urgencias service. Data persists via JSON file (`app/utils/errores_storage.py` → `data/control_errores.json`).

**Error record shape** (from `crear_error()`):
```python
{
    "id": "uuid",
    "tipo_error": str,          # From ERROR_TIPO_URGENCIAS list
    "factura": str,             # Upper case factura ID
    "observacion": str,         # Description/notes (uppercased)
    "observacion_facturador": str,  # Internal facturador note
    "estado": str,              # "S" (pendiente) or "N" (resuelto)
    "responsable": str,         # nombre_completo of assigned facturador
    "validador": str,           # Who created the record (session name)
    "creado_en": str,           # ISO datetime
    "actualizado_en": str,      # ISO datetime
    "imagenes_count": int,      # Added dynamically at list time
}
```

**There is NO "rol" field** in the error record. The `responsable` field stores only the user's `nombre_completo` (e.g., "JUAN PEREZ") — no role information is persisted.

**How "responsable" flows:**
1. `get_facturadores()` in `users_store.py` filters users where `rol == "facturador"` and returns them with `username`, `nombre_completo`, and **`rol`** fields
2. `get_opciones()` in the service layer calls `get_facturadores()` and extracts the name list for the `<select>` options
3. When creating/updating an error, only the `nombre_completo` string is stored as `responsable`
4. The fallback (hardcoded names in `constants/urgencias.py`) has NO role information

**How the table renders:**
- Template `control_errores.html` — pure Jinja2 base page with client-side JS rendering
- Data loads via `GET /api/control-errores` → JS `cachedErrores` array → `renderFilteredTable()`
- Current columns: **Validador | Factura | Creado | Categoría | Descripción | Responsable | Pendiente | Acciones**
- `renderTable()` and `renderFilteredTable()` both generate `<tr>` with 8 `<td>` elements (and `colspan="8"` for empty/new-row states)
- CSV export uses fixed header array with 8 columns

**Table width:**
- CSS `table-layout: fixed` with percentage-based column widths summing to 100%
- Wrapper `.table-wrapper` has `overflow-x: auto` — table can expand beyond viewport
- Column widths (nth-child 1-8): 6%, 8%, 8%, 11%, 36%, 15%, 6%, 10%
- Adding a column requires adjusting widths and updating `colspan` values

**The session always has `rol`:**
- On login (`auth_session.do_login()`), `session["rol"]` is set from `users.json` data
- Roles: `"admin"`, `"usuario"`, `"medico"`, `"facturador"`
- This is the CURRENT USER's role, NOT the responsible user's role

### Affected Areas

- `app/services/control_errores_service.py` — `get_errores()` needs enrichment: look up `rol` from `get_facturadores()` for each error's `responsable` and inject into response
- `app/templates/control_errores.html` — Add "Rol" column in `renderTable()`, `renderFilteredTable()`, `addNewRow()`, CSV export, empty-state `colspan`, new-row `colspan`
- `app/static/css/legacy/control_errores.css` — Add nth-child(9) column width; adjust existing nth-child widths (6-8) to free up space
- `tests/services/test_control_errores_service.py` — New tests for the enriched `get_errores()` behavior (rol enrichment)
- `tests/services/test_control_errores_integration.py` — New integration test verifying rol appears in GET response

### Approaches

1. **Enrich in service layer + frontend column** — recommended
   - In `get_errores()`, after calling `listar_errores()`, build a `responsable → rol` map from `get_facturadores()` and inject `responsable_rol` into each error dict
   - In the template, read `e.responsable_rol` and display it in a new `<td>`
   - No schema change to the JSON storage
   - Pros: Minimal coupling, no data migration, follows existing pattern (imagenes_count is already enriched dynamically)
   - Cons: Requires repeated lookup on every fetch (negligible — in-memory JSON)
   - Effort: Low

2. **Store rol in error record on create/update**
   - Add `responsable_rol` field to `crear_error()` and `actualizar_error()`
   - Look up rol from `get_facturadores()` at write time
   - Pros: Single lookup per write, no per-read enrichment
   - Cons: Schema change + migration for existing records, duplicate data, stale role if user's role changes later
   - Effort: Medium

3. **Extend opciones API to include responsible roles**
   - Add `responsables_con_roles` map to `/api/control-errores/opciones` endpoint
   - Frontend looks up rol from the map when rendering each row
   - Pros: Clean separation
   - Cons: Couples rendering to external lookup map, more complex frontend logic, awkward fallback handling
   - Effort: Medium

### Recommendation

**Approach 1 — Enrich in service layer.** It's the simplest change with no data migration, follows the existing pattern (`imagenes_count` is already injected dynamically in `listar_errores()`), and the `get_facturadores()` already returns `rol` for each facturador. The fallback (no facturadores) returns empty string for rol, which is acceptable since the hardcoded fallback is a legacy setup path.

**For table width**: Reduce "Responsable" column from 15% to 10%, reduce "Descripción" from 36% to 30%, add "Rol" column at 8%. The wrapper supports horizontal overflow so the table can still scroll if needed.

### Risks

- **Fallback empty roles**: When no facturadores exist in `users.json` (using hardcoded fallback), the rol will be empty. The UI should display "-" or "N/A" gracefully. This is a temporary scenario during initial system setup.
- **colspan values**: There are 5 hardcoded `colspan="8"` values in the template that must all be updated to `colspan="9"`. Missing one will break table rendering.
- **CSV export column order**: The CSV export uses a separate hardcoded header array and row builder — must be kept in sync with the table columns.

### Ready for Proposal

Yes. The change is well-understood, the approach is straightforward, and all affected files are identified. The orchestrator can move to `sdd-propose`.
