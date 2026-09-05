# Procesar — Unified Processing Specification

## Purpose

The `/procesar` endpoint is the single unified entry point for all Excel-based medical billing processing. It replaces the old area-specific routes (`/odontologia/`, `/urgencias/`, `/odontologia-equipos-basicos/`). Access is gated by the `procesar` permission; write operations additionally require `procesar:write`.

---

## Requirements

### R1: Route Permission Gate

`GET /procesar/` and `POST /procesar/` MUST require `procesar` in `session["permisos"]`. Admin (`"*"`) bypasses all checks.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has permiso | user with `procesar` | GET `/procesar/` | 200 — renders React shell |
| No permiso | user without `procesar` | GET `/procesar/` | 403 or redirect to home |
| Admin bypass | user with `"*"` only | GET `/procesar/` | 200 — admin always passes |
| Unauthenticated | no active session | GET `/procesar/` | 401 or redirect to login |

### R2: Write Gate (`can_write`)

The `can_write` boolean passed to the React frontend MUST be `True` when `"*"` or `procesar:write` is in `session["permisos"]`. The old `urgencias:write` check SHALL be removed.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Write permiso | user with `procesar:write` | GET `/procesar/` | `can_write: true` in `initial_data` |
| Read-only | user with `procesar` only | GET `/procesar/` | `can_write: false` |
| Admin | user with `"*"` | GET `/procesar/` | `can_write: true` |
| Old perm ignored | user with `urgencias:write` only (no `procesar:write`) | GET `/procesar/` | `can_write: false` — old write perms don't grant write |

### R3: POST Processing

`POST /procesar/` MUST accept an Excel file, auto-detect the area type from `Tipo Factura Descripción`, and run the appropriate detection pipeline.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy path | valid `.xlsx`, user has `procesar` | POST | 200 JSON with `status: "success"` and problem list |
| No file | empty body | POST | 400 — `"Debes seleccionar un archivo"` |
| Invalid column headers | missing required columns | POST | 200 — `status: "error"` with `missing_columns` |
| No permiso | user without `procesar` | POST | 403 — `"Permiso denegado"` |
| Rate limited | same user, 2nd request within 120s | POST | 429 — rate limit active |

### R4: Migration Compatibility

Old permissions (`urgencias`, `odontologia`, `odontologia_equipos_basicos`) MUST be treated as equivalent to `procesar` for backward compatibility during the transition period. Users MAY hold old permissions and still access `/procesar`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Legacy user | user with only `odontologia` | GET `/procesar/` | 403 — `odontologia` is NOT a valid gate for `procesar` after migration |
| Migrated user | user's perms include `procesar` (migrated from `odontologia`) | GET `/procesar/` | 200 — migration resolved access |

---

## Validation Rules

| Field | Rule |
|-------|------|
| `procesar` | MUST be in `ALLOWED_PERMISOS` in `app/constants/base.py` |
| `procesar:write` | MUST be in `ALLOWED_PERMISOS` and SHOULD grant base `procesar` via `:write` expansion |
| Permiso mutual exclusion | `procesar` and `procesar:write` MUST be in `PERMISO_MUTUAL_EXCLUSION` (cannot have both) |

---

## Acceptance Criteria

- [ ] `procesar` and `procesar:write` in `ALLOWED_PERMISOS`
- [ ] `@permiso_requerido("procesar")` on GET and POST routes
- [ ] `can_write` checks `procesar:write`, not `urgencias:write`
- [ ] `procesar` / `procesar:write` pair in `PERMISO_MUTUAL_EXCLUSION`
- [ ] Sidebar Procesar nav item uses `permiso: "procesar"`
- [ ] Dashboard `DASHBOARD_AREAS` Procesar entry uses `permiso: "procesar"`
- [ ] Old perms removed from `ALLOWED_PERMISOS`, `DEFAULT_TEMPLATES`, `DEFAULT_USERS`
- [ ] All existing tests pass
