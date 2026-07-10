# Design: Permisos Granulares por Roles en Control-Errores

## Technical Approach

Extend the service layer with role-aware permission helpers while keeping the existing flat `permisos` model as a fast path. The page (`/control-errores`) remains a single URL; behavior adapts from `session["rol"]` + `session["permisos"]`.

Two-tier check in every protected operation: (1) effective role resolution from session, (2) record-level ownership comparison via the new `created_by` username field. Admin, auditor, and write users retain full access via the existing `permisos` check — no role evaluation needed.

## Architecture Decisions

### AD-1: Effective role resolution

**Choice**: `_resolve_effective_role()` helper — if `session["permisos"]` contains `*` or `control_urgencias:write` → `"write"`; else use `session["rol"]`.  
**Rationale**: Permisos are the authoritative access signal today; role adds constraint for facturador/medico. Combining both into a single resolved string avoids repeating checks everywhere.  
**Alt rejected**: Route-level decorators. Too coarse — ownership checks need record ID which only the service has.

### AD-2: `created_by` field

**Choice**: Add `created_by: str` (username) to error JSON records alongside existing `validador` (display name). On creation, set from `session["username"]`.  
**Rationale**: `validador` uses display name (non-unique). Username is the system identifier needed for reliable ownership lookup. Keeping `validador` preserves backward compat for the UI.  
**Alt rejected**: Extend `validador` to include username. Breaks existing display logic and pollutes a UI-only field.

### AD-3: Legacy record handling

**Choice**: Records missing `created_by` → `created_by = None`. Permission helpers treat `None` as admin-created: editable only by write/admin/auditor.  
**Rationale**: ~400 existing records without `created_by`. Assuming they are admin-created is the safest default — facturadores can't accidentally edit records from write users.  
**Alt rejected**: Auto-migrate with `created_by = "migracion"`. Risky — we don't know the real creator.

### AD-4: Frontend permission model

**Choice**: Replace `window._canWrite` boolean with `window._userRole` (string) + per-record `can_edit` / `can_delete` booleans in API response.  
**Rationale**: A single boolean can't express record-level ownership. Per-record flags are computed server-side (single source of truth) and consumed by the existing `updateDisabledState()` pattern.  
**Alt rejected**: Compute permissions in JS. Would duplicate logic and require exposing `created_by` to the client.

### AD-5: Auditor role

**Choice**: New role `"auditor"` — treated identically to admin/write for control-errores (full access). Added to `update_user()` role validation and `_resolve_effective_role()`.  
**Rationale**: Auditor needs full visibility + edit capability per the permission matrix. No new permiso string needed — it's role-driven.

## Data Flow

```
Request → Route (permiso_requerido gate, unchanged)
  │
  ├── GET /api/control-errores
  │     → get_errores(filters, session)
  │        1. listar_errores() → raw records from JSON
  │        2. Enrich: responsable_rol + resolve created_by
  │        3. Resolve effective role → filter by role:
  │           - admin/auditor/write: return all
  │           - facturador: responsable_rol = MEDICO OR created_by = session.username
  │           - medico: responsable_rol = MEDICO AND (created_by = session.username
  │             OR responsible name matches session name)
  │        4. Compute per-record can_edit/can_delete flags
  │        5. Return { errores: [...], can_edit, can_delete }
  │
  ├── POST /api/control-errores
  │     → add_error(data, session)
  │        1. Resolve role → facturador? validate target rol = medico
  │        2. crear_error(...) with created_by = session["username"]
  │
  ├── PUT /api/control-errores/<id>
  │     → update_error(id, data, session)
  │        1. Fetch record → check exists
  │        2. Resolve role + ownership → can_edit? (AD-1 + AD-3)
  │        3. If not full-write: reject non-estado/observacion_facturador fields
  │        4. actualizar_error(...)
  │
  └── DELETE /api/control-errores/<id>
        → delete_error(id, session)
           1. Fetch record → check exists
           2. Resolve role → only write/admin/auditor can delete
           3. eliminar_error(...)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/control_errores_service.py` | Modify | Add `_resolve_effective_role()`, `_can_edit()`, `_can_delete()`, `_can_create_for()` helpers. Update `get_errores()` (role filtering + per-record flags), `add_error()` (created_by + facturador validation), `update_error()` (ownership check), `delete_error()` (role gate). |
| `app/utils/errores_storage.py` | Modify | Add `created_by: str` to `crear_error()` schema. Backward-compatible — existing records missing field get `None` at read time. |
| `app/routes/control_errores.py` | Modify | Pass `session` to `add_error()`, `update_error()`, `delete_error()`. No route decorator changes needed. |
| `app/templates/control_errores.html` | Modify | `window._userRole` replaces `window._canWrite`; `updateDisabledState()` consumes per-record flags; add/create-medico dropdown for facturador; guard add/edit/delete by role + flags. |
| `app/utils/users_store.py` | Modify | Add `"auditor"` to `update_user()` role validation. |
| `app/constants/base.py` | Modify | Update `DASHBOARD_AREAS` and `DEFAULT_TEMPLATES` if auditor dashboard access differs. |

## Interfaces / Contracts

```python
# New helpers in control_errores_service.py

def _resolve_effective_role() -> str:
    """
    Returns: "admin", "auditor", "write", "facturador", "medico", "read"
    Priority: permisos (* → admin, :write → write) > session["rol"]
    """

def _can_edit(record: dict, effective_role: str, username: str) -> bool:
    """
    admin/auditor/write → always True
    facturador → record.responsable_rol == "MEDICO" or record.created_by == username
    medico → record.created_by == username (only estado/obs fields)
    read → False (except estado/obs — handled at field level)
    Legacy (created_by is None) → only admin/auditor/write
    """

def _can_delete(record: dict, effective_role: str) -> bool:
    """Only admin/auditor/write. Others ALWAYS False."""

def _can_create_for(target_rol: str, effective_role: str) -> bool:
    """facturador → only "medico". Others → any."""

# API response enrichment
{
    "errores": [{ ...record, "can_edit": bool, "can_delete": bool }]
}
```

```python
# creado_error() signature change (errores_storage.py)
def crear_error(..., validador: str = "", created_by: str = "") -> dict:
    nuevo_error = { ..., "validador": validador, "created_by": created_by }
```

```javascript
// Frontend globals (control_errores.html)
window._userRole = "{{ session.get('rol', '') }}";
window._username = "{{ session.get('username', '') }}";
// Per-record flags consumed in renderRow() and updateDisabledState()
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `_resolve_effective_role()` with all perm+role combos | Parametrized pytest, table-driven |
| Unit | `_can_edit()`, `_can_delete()`, `_can_create_for()` with ownership scenarios + legacy records | Mock records, assert boolean outcomes per role |
| Integration | GET /api/control-errores — verify filtered results per role | Flask test client, 5 session fixtures (admin/auditor/write/facturador/medico) |
| Integration | POST — facturador denied for non-medico target; created_by populated | Flask test client, verify JSON + created_by field |
| Integration | PUT — ownership denied for facturador on write-created record; legacy 403 | Flask test client, create records with different created_by |
| Integration | DELETE — facturador/medico get 403 | Flask test client |

## Migration / Rollout

No data migration required. `created_by` field is additive — existing records without it return `None` from JSON, and all permission helpers treat `None` as admin-created (safe). Rollback: revert service-layer changes, drop `created_by` from `crear_error()` schema, restore `window._canWrite`.

## Open Questions

None — all questions from exploration (Q1–Q6) resolved in confirmed permission matrix.
