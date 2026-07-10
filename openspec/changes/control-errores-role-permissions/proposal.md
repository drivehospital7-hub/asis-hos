# Proposal: Permisos Granulares por Roles en Control-Errores

## Intent

Replace the flat `permisos`-only model with role-based access. Today, any user with `control_urgencias:write` has full CRUD on all records. This is inappropriate — facturadores and médicos share the tool but operate at different privilege levels. Facturadores should create/edit only for médicos, médicos should see only their own records, and legacy records must be protected from unauthorized editing.

## Scope

### In Scope

- Role-aware filtering in `get_errores()`: admin sees all, facturador sees médicos + own, médico sees only self-assigned
- Record-level ownership checks in `update_error()` / `delete_error()`
- `created_by` (username) on all new records
- Create-for-médico dropdown (facturador + medico roles)
- Per-record `can_edit` / `can_delete` flags in API responses
- Legacy records (~400): treated as admin-created; facturadores blocked

### Out of Scope

- UI role tabs or separate pages — single page adapts via `session["rol"]`
- Real-time permission revocation (requires re-login)
- Role-based export restrictions beyond current model

## Capabilities

### New Capabilities
- `role-permission-model`: role-based filtering, ownership tracking (`created_by`), per-record permission flags evaluated server-side

### Modified Capabilities
- `control_errores`: extend R1-R12 with role-aware rules; all existing permission logic shifts from flat `permisos` to role+permisos matrix

## Approach

Same page (`/control-errores`), backend-enforced at service layer.

**Permission Matrix:**

| Rol | Ver | Crear para | Editar | Eliminar | Cambiar estado |
|-----|-----|-----------|--------|----------|----------------|
| Admin (`*`) | Todos | Cualquiera | Todos | Todos | Todos |
| Usuario c/write | Todos | Cualquiera | Todos | Todos | Todos |
| Facturador | Médicos + suyos (read-only) | Solo médicos | Solo de médicos | No | Sí (propios + médicos) |
| Médico | Solo suyos | Sí mismos | No | No | Sí (solo suyos) |

**Key changes:**
- `get_errores()` applies role filter on `responsable_rol` (from R12) + `created_by`
- `add_error()`: facturador only creates for medico; `responsable` auto-filled; `created_by` set from session
- `update_error()`: ownership check before field-level permission check
- `delete_error()`: facturador and médico prohibited
- Frontend: `window._userRole` + per-record `can_edit`/`can_delete` replace single `window._canWrite`
- Legacy records (no `created_by`): admin-created semantics — editable only by write users

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/control_errores_service.py` | Modified | Role filtering, ownership checks, create validation |
| `app/utils/errores_storage.py` | Modified | `created_by` field in record schema |
| `app/routes/control_errores.py` | Modified | `responsables_por_rol` endpoint |
| `app/templates/control_errores.html` | Modified | Role-aware guards, create-for-médico dropdown |
| `app/utils/users_store.py` | Modified | Role-filtered user listing |
| Tests | Modified | Role-based access test classes |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy records incorrectly editable by facturadores | Medium | No `created_by` → admin-created; facturadores get 403 |
| Race condition on ownership change mid-edit | Low | Re-check permissions inside `update_error()` |
| Name collision in `responsable` lookups | Low | `created_by` uses username (unique); `responsable` stays full-name |

## Rollback Plan

Revert service-layer to flat `permisos` checks. Drop `created_by` from schema (backward-compatible — existing code ignores unknown keys). Restore `window._canWrite` boolean guard. No DB schema changes to undo.

## Dependencies

- `control-errores-rol-column` (R12): `responsable_rol` already available for filtering
- `facturadores-dynamic-responsables`: dropdown data source stable

## Success Criteria

- [ ] Facturador sees only médicos' records + own; cannot edit write-user-created records
- [ ] Médico sees only self-assigned records; can toggle estado/observacion_facturador only
- [ ] Admin and write users retain full access (zero regression)
- [ ] All new records carry `created_by` username
- [ ] Legacy records (no `created_by`) blocked for facturadores with 403
- [ ] All existing tests pass with role-aware test data
