# Control de Errores — Escritura Parcial

## Purpose

The `control_urgencias` user (without `:write`) needs partial access: edit `estado` and `observacion_facturador`, view read-only tooltips for `observacion`/`factura`, use filters, and view images. All other mutation actions (create, delete, export, upload images, bulk upload) SHALL be prohibited both in UI and API.

## Requirements

### R1: Partial Write — Backend Enforcement

The system MUST restrict PUT `/api/control-errores/<id>` to fields `estado` and `observacion_facturador` when the user has `control_urgencias` without `:write` or `*`. Prohibited fields in a PUT payload SHALL cause a 403 with no side effects.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Edit estado | `control_urgencias` | PUT `{"estado":"R"}` | 200; field updated |
| Edit obs.facturador | `control_urgencias` | PUT `{"observacion_facturador":"Ok"}` | 200; field updated |
| Reject prohibited | `control_urgencias` | PUT `{"tipo_error":"X"}` | 403; no changes |
| Reject mixed payload | `control_urgencias` | PUT `{"estado":"R","responsable":"Juan"}` | 403; no changes |
| Reject observacion edit | `control_urgencias` | PUT `{"observacion":"text"}` | 403; no changes |

### R2: Full Write — Unchanged

Users with `control_urgencias:write` or `*` (admin) MUST retain full write access to ALL fields — no regression.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Auditor edits any field | `control_urgencias:write` | PUT any valid field | 200; field updated |
| Admin edits any field | `*` | PUT any valid field | 200; field updated |

### R3: Read-Only Tooltip for observacion and factura

The system MUST show a read-only tooltip (via `showObservacionReadOnly()`) for `observacion` and `factura` cells when the user lacks write permission. Users with write permission SHALL continue to open the editor.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Click observacion | `control_urgencias` | clicks observacion cell | `showObservacionReadOnly()` shown |
| Click factura | `control_urgencias` | clicks factura cell | `showObservacionReadOnly()` shown |
| Click observacion (write) | `control_urgencias:write` | clicks observacion | editor opens (unchanged) |
| Click factura (write) | `control_urgencias:write` | clicks factura | editor opens (unchanged) |

### R4: Image Modal — Read-Only View

The system MUST allow non-write users to open the image modal and view images, but SHALL hide the dropzone and delete buttons. Direct API calls to upload/delete SHALL return 403.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Open modal read-only | `control_urgencias` | clicks eye icon | modal opens; dropzone hidden; no delete buttons |
| Upload via API | `control_urgencias` | POST `/api/.../imagenes` | 403; not saved |
| Delete via API | `control_urgencias` | DELETE `/api/.../imagenes` | 403; not deleted |

### R5: Prohibited UI Actions (Frontend Guards)

The UI MUST prevent non-write users from using: add new row, delete, export, bulk upload. Each guard function SHALL return early when `window._canWrite` is `false`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Export | `control_urgencias` | clicks export button | `exportToCSV()` returns early |
| Bulk upload | `control_urgencias` | clicks carga masiva | `openCargaMasiva()` returns early |
| Add row | `control_urgencias` | clicks add button | `addNewRow()` returns early |
| Delete row | `control_urgencias` | clicks delete icon | `deleteError()` returns early |

### R6: Filters (Unchanged)

All authenticated users with `control_urgencias` MUST be able to apply filters. No changes required.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Apply filters | `control_urgencias` | selects filter criteria | `loadErrores()` called with params |

### R7: Permission Check — Service Layer

`update_error()` MUST use `session.get("permisos", [])` instead of the legacy `session.get("ce_authenticated")` to determine field write scope.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Legacy flag ignored | `ce_authenticated=false`; `permisos=["control_urgencias:write"]` | PUT any field | 200 — legacy flag does not block |
| Only permisos matters | `ce_authenticated=true`; no `permisos` | PUT `{"tipo_error":"X"}` | 403 — only permisos checked |

### R8: Frontend Guard — Server Permission via Jinja

The system MUST evaluate `window._canWrite` server-side via Jinja (`session.get("permisos", [])`) instead of the legacy `ceAuth.isAuth()` which reads localStorage.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| `_canWrite` true | session has `control_urgencias:write` or `*` | page renders | `window._canWrite = true` |
| `_canWrite` false | session has `control_urgencias` only | page renders | `window._canWrite = false` |
| JS guard migration | any non-write user | calls any guarded function | guard reads `window._canWrite`, not `ceAuth.isAuth()` |

## Non-Functional Requirements

- **Performance**: No additional API calls or DB queries for permission checks — `session.get("permisos", [])` is already loaded on every request.
- **Security**: Backend SHALL be the authoritative gate. Frontend guards exist for UX only — prohibited fields rejected at service layer regardless of client.
- **Compatibility**: All existing behavior for `control_urgencias:write` and `*` users SHALL remain unchanged. Anonymous users SHALL keep current read-only tooltip behavior.
