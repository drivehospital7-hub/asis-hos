# Design: Validador Column in Control de Novedades

## Technical Approach

Add a read-only "Validador" column as the first column in the Urgencias control de novedades table. The field auto-fills server-side on creation from `session["primer_nombre"] + " " + session["apellido_1"]`, stored in the JSON flat file as a new key `validador`. Three files change: storage (`crear_error` signature), service (`add_error` composes from session), and template (Jinja2 + inline JS rendering). No API schema change, no client-side input.

## Architecture Decisions

### Decision: Full name string vs. separate first/last storage

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Store `primer_nombre + apellido_1` as a single `"validador"` string | Simpler storage, no recomposition needed for display | ✅ **Chosen** |
| Store first/last as separate keys | More precise data, duplicates session info | ❌ Rejected — display-only field, no querying needed |

**Rationale**: The validador is display-only metadata, never queried or searched. A single string matches the "Creado" pattern (timestamp is pre-composed, not stored as separate date/time). Saves a template-side recomposition.

### Decision: Default empty string for `validador` param

**Choice**: `validador: str = ""` as keyword argument in `crear_error()`
**Alternatives considered**: Making it required (breaks existing callers), defaulting to `session` lookup inside storage (couples storage to Flask)
**Rationale**: Matches existing pattern (`observacion_facturador: str = ""`). Keeps storage layer Flask-agnostic. The service layer owns the session read.

### Decision: No CSV export change

**Choice**: Leave CSV export as-is (6 columns: Factura, Creado, Categoría, Descripción, Responsable, Estado)
**Rationale**: The proposal scopes only the Jinja2 table. CSV is an export format, not the interactive table. Adding Validador to CSV would be a separate request.

## Data Flow

```
POST /api/control-errores
       │
       ▼
control_errores_service.py::add_error(data)
       │  reads session["primer_nombre"] + session["apellido_1"]
       │  composes validador string
       ▼
errores_storage.py::crear_error(..., validador="Juan Pérez")
       │  appends {"validador": "Juan Pérez", ...} to JSON
       ▼
control_errores.json  ←  new entry with validador key
       │
       ▼  (subsequent GET /api/control-errores returns it)
       │
       ▼
control_errores.html  ←  Jinja2 template renders
       │  {{ e.validador or '-' }} in read-only <td>
       │  colspan="7" → "8" in 4 places
       ▼
      Table shows Validador as first column
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/utils/errores_storage.py` | Modify | `crear_error()` gets `validador: str = ""` param, stores as `"validador"` key in JSON dict |
| `app/services/control_errores_service.py` | Modify | `add_error()` reads `session["primer_nombre"]` and `session["apellido_1"]`, composes `f"{p} {a}".strip()`, passes to `crear_error()` |
| `app/templates/control_errores.html` | Modify | New `<th>` first column, read-only `<td>` per row, `colspan` 7→8 in 4 places, `addNewRow()` gets static validador cell, `renderTable()` and `renderFilteredTable()` include validador cell, CSV export unchanged |

## Interfaces / Contracts

### Storage

```python
# Before
def crear_error(tipo_error, factura, observacion, estado, responsable, observacion_facturador=""):

# After
def crear_error(tipo_error, factura, observacion, estado, responsable, observacion_facturador="", validador=""):
```

New key in stored dict: `"validador": validador`

`actualizar_error()` explicitly does NOT accept `validador` — the field is set-once on creation only.

### Service

```python
# In add_error(), after extracting request data:
validador = f"{session.get('primer_nombre', '')} {session.get('apellido_1', '')}".strip()
nuevo = crear_error(tipo_error, factura, observacion, estado, responsable, observacion_facturador, validador=validador)
```

No new route or API endpoint. The validador is NEVER accepted from client JSON — server-side only.

### Template rendering

```html
<!-- Table header — NEW first col -->
<th>Validador</th>
<th>Factura</th>
...

<!-- Per-row read-only cell (no editable-cell class, no onclick) -->
<td class="fecha-creado">${escapeHtml(e.validador || '-')}</td>

<!-- colspan updates: "7" → "8" in 4 places (lines 103, 375, 395, 1252) -->
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `crear_error()` stores `validador` key | Patch `_escribir_datos`, call with `validador="Juan Pérez"`, assert dict has `"validador": "Juan Pérez"` |
| Unit | `add_error()` composes validador from session | Mock `session`, assert `crear_error` called with expected `validador` value |
| Unit | Existing entries without `validador` render `-` | Template renders `e.validador || '-'` — verify logic in JS `renderTable()` |
| Unit | `actualizar_error()` does NOT touch validador | Verify `validador` not in kwargs sent to storage |
| E2E | Full flow: POST creates entry with validador, GET returns it | Flask test client with `session_transaction()` |

### Test patterns (follow existing)

- Use `_APP.test_request_context()` and `patch()` (see `test_control_errores_service.py`)
- Integration tests use `app_client` fixture with `session_transaction()` (see `test_control_errores_integration.py`)
- Test file: `tests/services/test_control_errores_service.py` (add class within existing file) or new `tests/services/test_validador_columna.py`

## Migration / Rollout

**No migration required.** Existing entries lack the `validador` key — template renders `e.validador || '-'` which yields `-`. Orphaned key is harmless if reverted.

**Rollback**: `git revert` the implementation commits. JSON data with `validador` keys becomes harmless orphaned fields. No data loss.

## Open Questions

- [ ] CSV export: should the Validador column be added to exported CSV? Currently not in proposal scope. Defer unless team requests.
