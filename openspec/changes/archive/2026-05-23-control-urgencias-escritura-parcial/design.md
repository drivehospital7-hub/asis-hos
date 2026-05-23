# Design: Control Urgencias — Escritura Parcial

## Technical Approach

Three-layer defense-in-depth: (1) route decorator lets `control_urgencias` through, (2) service layer validates field-level permissions via `session["permisos"]`, (3) frontend JS guards use server-rendered `window._canWrite` for UX. Only PUT changes; all other mutations stay at `:write`.

## Architecture Decisions

### Decision: Permission check in service, not decorator

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New decorator for partial write | Cleaner route, but duplicates decorator logic per-endpoint | ❌ |
| Custom `permiso_requerido` with field arg | Overcomplicates the generic decorator | ❌ |
| **Check in `update_error()` via `session["permisos"]`** | Single place, follows existing `ce_authenticated` pattern, no new abstractions | ✅ |

**Rationale**: The decorator controls route *access* (enter/deny). The service controls *what you can do once inside*. Adding field-level logic to the decorator would break SRP and couple auth to data validation.

### Decision: `window._canWrite` replaces `ceAuth.isAuth()` only in control_errores.html

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Fix `ceAuth.isAuth()` in base.html | Affects other modules, risks regressions | ❌ |
| Replace all 9 guards in control_errores.html only | Targeted, risk-isolated | ✅ |

**Rationale**: The legacy `ceAuth.isAuth()` reads localStorage (`ce_authenticated` boolean) which is set on login and never cleared on logout or permission change. `_canWrite` evaluates permission server-side each page render, so it's always accurate. The `updateDisabledState()` function already uses `_canWrite` — the inconsistency was that individual guard functions still used the old method.

### Decision: Prohibited fields in PUT return 403 with field names

**Rationale**: Follows existing project pattern (see `control_errores_service.py:114-121`). The error message includes which fields were rejected, making debugging easy for future developers.

## Security Model

| Layer | Mechanism | What it blocks |
|-------|-----------|----------------|
| Route decorator (L1) | `@permiso_requerido("control_urgencias")` | Non-authenticated, no `control_urgencias` perm |
| Service layer (L2) | `session["permisos"]` check on `data.keys()` | Prohibited fields even if client sends them |
| Frontend guards (L3) | `window._canWrite` | UX: buttons don't work, cells show tooltips |

The service layer is the authoritative gate. Frontend guards are UX-only — a malicious client cannot bypass L2.

## Data Flow

```
Browser                          Flask Route                    Service
  │                                 │                             │
  │ PUT /api/control-errores/<id>   │                             │
  │ ──────────────────────────────► │                             │
  │                                 │ @permiso_requerido          │
  │                                 │ ("control_urgencias")       │
  │                                 │   ├─ sin permiso → 403     │
  │                                 │   └─ ok → route handler    │
  │                                 │        │                    │
  │                                 │   update_error(id, data)    │
  │                                 │ ──────────────────────────► │
  │                                 │                             │
  │                                 │   session["permisos"]:      │
  │                                 │   ├─ "*" or ":write" → all  │
  │                                 │   └─ "control_urgencias"    │
  │                                 │        → solo estado/obs_f  │
  │                                 │            ├─ prohibited?   │
  │                                 │            │  → 403 + list  │
  │                                 │            └─ ok → update   │
  │                                 │                             │
  │  ←── 200 {status, data} ────── │  ←── 200/403 ────────────── │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/control_errores.py:81` | Modify | PUT decorator: `control_urgencias:write` → `control_urgencias` |
| `app/services/control_errores_service.py:109-122` | Modify | Replace `session.get("ce_authenticated")` with permission-based check |
| `app/templates/control_errores.html` | Modify | 9 JS guard functions: `ceAuth.isAuth()` → `_canWrite` + image modal visibility |

## Backend Design

### Route change (control_errores.py:81)

```python
# Before
@permiso_requerido("control_urgencias:write")

# After
@permiso_requerido("control_urgencias")
```

### Service change (control_errores_service.py:109-122)

```python
# Replace lines 109-122:
user_permisos = session.get("permisos", [])
is_full_write = "*" in user_permisos or "control_urgencias:write" in user_permisos

if not is_full_write:
    prohibited = set(data.keys()) - {"estado", "observacion_facturador"}
    if prohibited:
        return {
            "status": "error",
            "data": {},
            "errors": [
                f"No autorizado. Solo puede cambiar 'estado' y "
                f"'observacion_facturador'. "
                f"Campos rechazados: {', '.join(sorted(prohibited))}"
            ],
        }, 403
```

Note: returns tuple `(dict, int)` — route must handle this. Currently `actualizar_error` does `return jsonify(update_error(...))` which would serialize the tuple incorrectly. The route needs:

```python
result = update_error(error_id, data)
if isinstance(result, tuple):
    return jsonify(result[0]), result[1]
return jsonify(result)
```

## Frontend Design

### JS Guards: `ceAuth.isAuth()` → `_canWrite`

| Function (line) | Current Guard | New Guard | Behavior Change |
|-----------------|---------------|-----------|-----------------|
| `handleCellClick` (1671) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` + `observacion`/`factura` → read-only tooltip |
| `openEditor` (1787) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` + field not `{estado, obs_facturador}` → return early |
| `addNewRow` (2166) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |
| `deleteError` (2245) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |
| `exportToCSV` (2392) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |
| `openImageModal` (2480) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → hide dropzone + delete buttons |
| `uploadImages` (2532) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |
| `deleteImage` (2548) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |
| `openCargaMasiva` (2873) | `ceAuth.isAuth()` | `_canWrite` | `!_canWrite` → return |

### `openEditor` guard logic change

**Before** (line 1786-1788):
```javascript
const authed = window.ceAuth && window.ceAuth.isAuth();
if (!authed && field !== 'estado' && field !== 'observacion_facturador' && field !== 'observacion' && field !== 'factura') return;
```

**After**:
```javascript
if (!window._canWrite && field !== 'estado' && field !== 'observacion_facturador') return;
```

Rationale: The proposal says urgencias should NOT edit `observacion` or `factura` directly — those are for audit users. The old check allowed observacion/factura for unauthenticated (but that was a bug in the original — observacion/factura should be tooltip-only for non-write). The new guard correctly restricts to only `estado` and `observacion_facturador`.

### `handleCellClick` observacion/factura logic

**Before** (lines 1671-1683):
```javascript
const authed = window.ceAuth && window.ceAuth.isAuth();
if (!authed && field === 'observacion') { showObservacionReadOnly(td); return; }
if (!authed && field === 'factura') { showObservacionReadOnly(td); return; }
```

**After**:
```javascript
if (!window._canWrite && (field === 'observacion' || field === 'factura')) {
  showObservacionReadOnly(td);
  return;
}
```

## Error Handling

### PUT — Prohibited fields (urgencias user)

```json
HTTP 403
{
  "status": "error",
  "data": {},
  "errors": ["No autorizado. Solo puede cambiar 'estado' y 'observacion_facturador'. Campos rechazados: responsable, tipo_error"]
}
```

### Any mutation endpoint — Missing permission

```json
HTTP 403
{
  "status": "error",
  "data": {},
  "errors": ["Permiso denegado"]
}
```

POST/DELETE/image-upload/image-delete keep `:write` decorator, so `control_urgencias` (without `:write`) gets standard 403 at the route level — never reaches service.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `update_error()` permission logic | Mock `session.get("permisos", [])` — test 4 scenarios: `*`, `:write`, `control_urgencias` (allowed fields), `control_urgencias` (prohibited fields) |
| Integration | PUT endpoint with different session states | Flask test client — verify 200 vs 403 + response body field names |
| E2E | Manual: urgencias user clicks cells | Verify tooltip shows, editor does not open, buttons disabled |
| Regression | Auditor/admin full write | Verify no change in behavior for users with `:write` or `*` |

## Migration / Rollout

No migration required. Permission check uses `session.get("permisos", [])` which already exists from the auth migration. The `ce_authenticated` legacy flag is simply ignored — no data migration needed.

Rollback: single commit revert of the 3 files.

## Open Questions

None.
