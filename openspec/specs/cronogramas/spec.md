# Cronogramas — Granular Permission Specification

## Purpose

Granular permissions for cronograma modules, replacing the admin-only (`"*"`) gate. The system now supports two distinct cronograma permissions: `cronograma_bacteriologas` and `cronograma_urgencias`.

---

## Requirements

### R1: `cronograma_bacteriologas` — Route Gate

All endpoints under `/cronograma-bacteriologas/` MUST require `cronograma_bacteriologas` in `session["permisos"]`. Admin (`"*"`) still bypasses.

**Decorator change**: `@permiso_requerido("*")` → `@permiso_requerido("cronograma_bacteriologas")`

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has permiso | user with `cronograma_bacteriologas` | GET `/cronograma-bacteriologas/` | 200 — renders React shell |
| No permiso | user without permiso | any `/cronograma-bacteriologas/` endpoint | 403 |
| Admin bypass | user with `"*"` only | any endpoint | 200 — admin always passes |
| API GET | user with permiso | GET `/cronograma-bacteriologas/api` | 200 — JSON cronograma data |
| API POST | user with permiso | POST `/cronograma-bacteriologas/api` | 200 — saves cronograma |
| API turno | user with permiso | GET `/cronograma-bacteriologas/api/turno` | 200 — turno data |

### R2: `cronograma_urgencias` — Route Gate

All endpoints under `/cronograma-urgencias/` MUST require `cronograma_urgencias` in `session["permisos"]`. Admin (`"*"`) still bypasses.

**Decorator change**: `@permiso_requerido("*")` → `@permiso_requerido("cronograma_urgencias")`

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has permiso | user with `cronograma_urgencias` | GET `/cronograma-urgencias/` | 200 — renders React shell |
| No permiso | user without permiso | any `/cronograma-urgencias/` endpoint | 403 |
| Admin bypass | user with `"*"` only | any endpoint | 200 |
| API GET | user with permiso | GET `/cronograma-urgencias/api` | 200 — JSON horario data |
| API POST | user with permiso | POST `/cronograma-urgencias/api` | 200 — saves horario |
| API DELETE | user with permiso | POST `/cronograma-urgencias/api/delete` | 200 — deletes horario |

### R3: Sidebar Visibility

Sidebar nav items for both cronogramas MUST use their respective granular permission names, not `"*"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Bacteriólogas visible | user with `cronograma_bacteriologas` | renders sidebar | "Cronograma Bacteriólogas" visible |
| Urgencias visible | user with `cronograma_urgencias` | renders sidebar | "Cronograma Urgencias" visible |
| Admin sees all | user with `"*"` | renders sidebar | both cronograma items visible |
| No permiso | user without either permiso | renders sidebar | neither cronograma item shown |

### R4: ALL_PERMISOS Registration

Both `cronograma_bacteriologas` and `cronograma_urgencias` MUST be registered in `ALLOWED_PERMISOS`, `ALL_PERMISOS` (frontend usuarios page), and `DEFAULT_TEMPLATES`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Backend constant | module initializes | check `ALLOWED_PERMISOS` | both values present |
| Frontend list | usuarios page loads | render `ALL_PERMISOS` | both checkboxes present |
| Template available | admin creates user | picks cronograma template | permisos include both cronograma values |

---

## Validation Rules

| Field | Rule |
|-------|------|
| `cronograma_bacteriologas` | MUST be in `ALLOWED_PERMISOS` |
| `cronograma_urgencias` | MUST be in `ALLOWED_PERMISOS` |
| No write variants | Cronograma permissions SHALL NOT have `:write` variants — access is all-or-nothing per route |

---

## Acceptance Criteria

- [ ] `cronograma_bacteriologas` and `cronograma_urgencias` in `ALLOWED_PERMISOS`
- [ ] `cronograma_bacteriologas.py` routes use `@permiso_requerido("cronograma_bacteriologas")`
- [ ] `cronograma_urgencias.py` routes use `@permiso_requerido("cronograma_urgencias")`
- [ ] Sidebar nav items use granular perms instead of `"*"`
- [ ] `ALL_PERMISOS` in usuarios page includes both cronograma perms
- [ ] Dashboard `DASHBOARD_AREAS` updated for both cronograma entries
- [ ] `DEFAULT_TEMPLATES` updated with cronograma options
- [ ] All existing tests pass
