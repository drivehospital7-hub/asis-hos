# Delta for control_errores

## ADDED Requirements

### R13: Role-Based Record Filtering

`get_errores()` MUST apply role-based filtering after enrichment, per the role-permission-model (PM1). Admin, Auditor, and Write users see all records. Facturador sees médico-assigned + self-created records. Médico sees only self-assigned records where `responsable_rol == "medico"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin unfiltered | admin session | `get_errores()` called | all records returned |
| Facturador filtered | facturador session; records include no médico-assigned | `get_errores()` called | only médico + self-created records returned |
| Médico filtered | médico "Juan Pérez"; record with responsable "María López" | `get_errores()` called | María's record excluded |

### R14: Facturador Creation Restricted to Médicos

Facturadores MUST only create records for responsables whose role is `medico`. The `responsables_por_rol` endpoint SHALL return only médicos for facturador sessions. Non-médico creation SHALL return 403.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador creates for médico | facturador; responsible is médico | POST valid payload | 201; `created_by` set |
| Facturador blocked on non-médico | facturador; responsible is facturador | POST | 403 |
| Dropdown filtered | facturador session | load create form | only médicos in responsable dropdown |

### R15: Médico Cannot Create Records

Users with médico role MUST NOT create records. POST `/api/control-errores` SHALL return 403. UI guard `addNewRow()` SHALL return early for médicos.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Médico POST blocked | médico session | POST valid payload | 403 |
| Médico UI button hidden | médico session | page renders | add row button disabled or hidden |

### R16: Ownership-Based Edit and Delete

`update_error()` and `delete_error()` MUST enforce ownership checks before field-level validation, per PM3. Facturador may edit/delete médico records. Médico may only partial-write on self-assigned records. Admin/Auditor/Write bypass ownership checks.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador deletes médico record | facturador; record with médico responsable | DELETE | 200; record removed |
| Facturador blocked on own-only record | facturador; record with facturador responsable, not self-created | DELETE | 403 |
| Médico partial write on own | médico; record where they are responsable | PUT `{"estado":"R"}` | 200 |
| Médico delete blocked | médico; record where they are responsable | DELETE | 403 |

## MODIFIED Requirements

### R1: Partial Write — Role-Aware Enforcement

The system MUST restrict PUT `/api/control-errores/<id>` to fields `estado` and `observacion_facturador` for users lacking `control_urgencias:write` or `*`, with role-based exceptions: facturadores SHALL have full write on records where `responsable_rol == "medico"`; médicos SHALL only have partial write on records where they are the `responsable`. Prohibited field edits outside the user's scope SHALL return 403 with no side effects.
(Previously: partial write applied uniformly to all users without `:write` or `*`, without role-based record scoping.)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Edit estado | `control_urgencias` | PUT `{"estado":"R"}` | 200 |
| Edit obs.facturador | `control_urgencias` | PUT `{"observacion_facturador":"Ok"}` | 200 |
| Reject prohibited | `control_urgencias` | PUT `{"tipo_error":"X"}` | 403 |
| Reject mixed payload | `control_urgencias` | PUT `{"estado":"R","responsable":"Juan"}` | 403 |
| Facturador full edit on médico | facturador; record with médico responsable | PUT `{"tipo_error":"X"}` | 200 |
| Facturador partial on own | facturador; own record (no médico responsable) | PUT `{"tipo_error":"X"}` | 403 |
| Médico partial on own | médico; record where responsable is themselves | PUT `{"estado":"R"}` | 200 |
| Médico full edit blocked | médico; record where responsable is themselves | PUT `{"tipo_error":"X"}` | 403 |

### R2: Full Write — Extended Roles

Users with `*` (admin), Auditor role, or `control_urgencias:write` MUST retain full write access to ALL fields on ALL records — no regression.
(Previously: only `control_urgencias:write` and `*` had full write; Auditor not listed.)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Write user edits any field | `control_urgencias:write` | PUT any field on any record | 200 |
| Admin edits any field | `*` | PUT any field on any record | 200 |
| Auditor edits any field | Auditor | PUT any field on any record | 200 |

### R5: Prohibited UI Actions — Role-Based Guards

The UI MUST prevent unauthorized actions per the permission matrix. Guard functions SHALL evaluate `window._userRole` combined with per-record `can_edit`/`can_delete` flags from PM6, replacing the single `window._canWrite` boolean. Add row SHALL show médico-only dropdown for facturadores and be blocked for médicos. Delete SHALL be blocked for médicos. Export and bulk upload SHALL remain blocked for all non-write users.
(Previously: all guards used a single `window._canWrite` boolean uniformly for all non-write users.)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Facturador add row | facturador | clicks add button | `addNewRow()` opens médico-only dropdown |
| Médico add blocked | médico | clicks add button | `addNewRow()` returns early |
| Médico delete blocked | médico | clicks delete icon | `deleteError()` returns early |
| Facturador delete médico record | facturador; record `can_delete: true` | clicks delete icon | `deleteError()` proceeds |
| Export blocked | facturador or médico | clicks export | `exportToCSV()` returns early |
| Bulk upload blocked | facturador or médico | clicks carga masiva | `openCargaMasiva()` returns early |
