# Delta Specification: sincronizar-dashboard-permisos

## New Domain: dashboard-permissions

### Purpose

Centralize the mapping between dashboard home areas and user permissions, filter areas server-side by `session["permisos"]`, remove the hardcoded frontend fallback, and add a route guard for `/derechos`.

---

### Requirements

#### R1: DASHBOARD_AREAS in `base.py`

The system MUST define `DASHBOARD_AREAS` in `app/constants/base.py` as a `list[dict]` with exactly 6 entries. Each dict MUST contain `title`, `slug`, `permiso`, `href`, `tone`, and `pending_label` per the proposal's table.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| All areas defined | constants loaded | inspect DASHBOARD_AREAS | 6 entries with correct mappings: urgencias, odontologia, control_errores, abiertas_urgencias, ordenado_facturado, derechos |
| Admin mapped separately | DASHBOARD_AREAS defined | check all permiso values | none is `"*"` — admin handled by filter, not constant |

#### R2: Backend filter in `home_react()`

The `home_react()` route MUST filter `DASHBOARD_AREAS` against `session["permisos"]`: include area only if its `permiso` field matches a user permiso. If `"*"` in permisos, SHALL return all areas unchanged.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin | `permisos=["*"]` | home_react() called | initialData.areas has all 6 DASHBOARD_AREAS |
| Single match | `permisos=["odontologia"]` | home_react() called | 1 area: odontologia |
| Multiple match | `permisos=["urgencias","facturas_abiertas"]` | home_react() called | 2 areas: urgencias, abiertas_urgencias |
| No mapped permiso | `permisos=["cruce_facturas"]` | home_react() called | `areas=[]` |
| Empty or missing | `permisos=[]` or key absent | home_react() called | `areas=[]` |

#### R3: Frontend — remove hardcoded fallback

The frontend `page.tsx` MUST use `initialData.areas` as the sole source for area cards. The hardcoded `areas` fallback array SHALL be removed. If `initialData?.areas` is null/undefined, SHALL resolve to `[]`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Backend provides areas | initialData.areas has 3 items | page renders | 3 cards shown |
| Empty from backend | initialData.areas=[] | page renders | no area cards, only KPIs and title |
| null initialData | `__INITIAL_DATA__` undefined | page renders | `areas=[]` via `?? []`, no crash |

#### R4: Derechos route guard

`derechos_react()` MUST be decorated with `@permiso_requerido("derechos")`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has permiso | `permisos=["derechos"]` | GET /derechos | 200, page renders |
| No permiso | `permisos=["odontologia"]` | GET /derechos | 403 |
| Admin bypass | `permisos=["*"]` | GET /derechos | 200 |
| Write-only | `permisos=["derechos:write"]` | GET /derechos | 403 (write != read) |
| Unauthenticated | no session | GET /derechos | 401 or redirect |

---

### Validation Rules

| Rule | Detail |
|------|--------|
| Admin sees all | `"*"` in permisos SHALL bypass all DASHBOARD_AREAS filtering |
| Empty permisos → empty dashboard | MUST NOT crash — empty list is valid |
| Filter by permiso field | Match against each area's `permiso` key only |
| `derechos:write` ≠ `derechos` | `@permiso_requerido("derechos")` requires exact string match |

### Edge Cases

| Case | Expected |
|------|----------|
| User has permisos matching zero DASHBOARD_AREAS | Empty dashboard, no crash |
| New area added to DASHBOARD_AREAS but missing from sidebar | Acceptable — sync is backend→dashboard only (sidebar is TS-side) |
| `session["permisos"]` key missing entirely | Treated as `[]` |
| `initialData` null/undefined on frontend | `initialData?.areas ?? []` |

---

## Modified Domain: admin-users-permissions

### Requirements (No Behavioral Change)

The proposal lists `admin-users-permissions` as a modified capability. However, `"derechos"` is already present in both `ALLOWED_PERMISOS` in `app/constants/base.py` (line 64) and the permisos checkboxes template in the existing spec (line 232 of `openspec/specs/admin-users-permissions/spec.md`).

No behavioral changes to the existing `admin-users-permissions` requirements are needed. The addition of `DASHBOARD_AREAS` (dashboard-permissions above) provides the synchronization layer that was previously missing between the permission system and the dashboard display.
