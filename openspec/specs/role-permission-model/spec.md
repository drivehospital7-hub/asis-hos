# Role Permission Model

## Purpose

Defines role-based access control for the control-errores module: record filtering, ownership tracking (`created_by`), server-side permission evaluation, and per-record capability flags.

## Permission Matrix

| Rol | Ver | Crear | Editar | Eliminar | Cambiar estado |
|-----|-----|-------|--------|----------|----------------|
| Admin (`*`) | Todos | Cualquiera | Todos | Todos | Todos |
| Auditor | Todos | Cualquiera | Todos | Todos | Todos |
| Write (`control_urgencias:write`) | Todos | Cualquiera | Todos | Todos | Todos |
| Facturador | Médicos + propios | Solo médicos | Solo médicos | Solo médicos | Sí |
| Médico | Solo propios | NO | No | No | Sí (propios) |

Admin and Auditor are equivalent within control-errores. Admin additionally has configuration access in other modules.

## Requirements

### PM1: Role-Based Record Filtering

`get_errores()` MUST filter records by user role after enrichment. Admin, Auditor, and Write users see all records. Facturador sees records where `responsable_rol == "medico"` OR `created_by == session_username`. Médico sees only records where `responsable == full_name` AND `responsable_rol == "medico"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin sees all | admin session | `get_errores()` called | all records returned |
| Facturador filtered | facturador session; mix of médico, own, and write-user records | `get_errores()` called | only médico-assigned + self-created records returned |
| Médico filtered | médico session | `get_errores()` called | only records where responsable matches the médico's full name |

### PM2: created_by Tracking

All new records MUST carry `created_by` set from `session["username"]`. The field SHALL be server-side only — client payloads with `created_by` MUST be ignored.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| created_by auto-set | authenticated user creates record | POST valid payload | `created_by` equals `session["username"]` |
| Client override rejected | user posts `{"created_by":"hacker"}` | POST | `created_by` uses session, not payload |

### PM3: Ownership-Based Edit and Delete

`update_error()` and `delete_error()` MUST verify record-level access before field-level restrictions. Admin, Auditor, and Write bypass all ownership checks. Facturador may edit/delete if `responsable_rol == "medico"` OR `created_by == username`. Médico may only update `estado`/`observacion_facturador` on self-assigned records; delete is always denied.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador edits médico record | facturador; record with médico responsable | `update_error()` | 200 |
| Facturador blocked on write record | facturador; record created by write user, not médico-assigned | `update_error()` | 403 |
| Médico partial edit | médico; record assigned to them | PUT `{"estado":"R"}` | 200 |
| Médico full edit blocked | médico; record assigned to them | PUT `{"tipo_error":"X"}` | 403 |
| Médico delete blocked | médico | DELETE | 403 |

### PM4: Facturador Creation Restricted to Médicos

Facturadores MUST only create records where `responsable` is a médico. Creation with non-médico `responsable_rol` SHALL return 403.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador creates for médico | facturador; responsable is médico | POST valid payload | 201 |
| Facturador creates for non-médico | facturador; responsable is facturador | POST | 403 |

### PM5: Legacy Record Handling

Records missing `created_by` SHALL be treated as admin-created for ownership checks. They fail `created_by == username` for facturadores but remain accessible via `responsable_rol == "medico"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Legacy médico record | facturador; legacy record (no `created_by`) with médico responsable | `update_error()` | 200; allowed via `responsable_rol` path |
| Legacy non-médico record | facturador; legacy record with non-médico responsable | `update_error()` | 403 |

### PM6: Per-Record Permission Flags

Each record in `get_errores()` response MUST include `can_edit` and `can_delete` booleans, evaluated server-side from the permission matrix. Frontend SHALL use these flags per-row instead of a global `window._canWrite`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador on médico record | facturador; médico-assigned record | response serialized | `can_edit: true`, `can_delete: true` |
| Médico on own record | médico; self-assigned record | response serialized | `can_edit: false`, `can_delete: false` |
| Admin on any record | admin | response serialized | `can_edit: true`, `can_delete: true` |
