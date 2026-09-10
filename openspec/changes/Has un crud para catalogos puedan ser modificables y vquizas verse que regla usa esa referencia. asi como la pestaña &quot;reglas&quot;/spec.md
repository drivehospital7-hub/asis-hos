# Catalogos CRUD Specification

## Purpose

CRUD completo sobre la tabla `catalogos` (JSONB) + consulta de reglas que referencian cada catálogo. Reemplaza la manipulación directa en DB permitiendo crear, editar y eliminar catálogos desde la UI con validación de dependencias.

---

## Requirements

### R1: Listar catálogos (`GET /api/catalogos`)

The system MUST return a paginated list of all catalogs. Each item SHALL include: `key`, `descripcion`, `dominio`, `value` (preview array), `value_count` (number of elements), and `regla_count` (number of rules referencing this key via `cat_in`). Response SHALL include `total` and pagination fields.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List with results | 5 catalogs exist, 2 referenced by rules | `GET /api/catalogos` | returns `data.items` with 5 entries, each with `regla_count`, `total: 5` |
| Empty | no catalogs exist | `GET /api/catalogos` | `data.items` empty array, `total: 0` |

### R2: Obtener catálogo (`GET /api/catalogos/<key>`) — **existing, verify**

The system MUST return the full catalog object: `key`, `value` (full JSONB array), `value_count`, `descripcion`, `dominio`, `updated_at`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Found | catalog with key `prof_odon` exists | `GET /api/catalogos/prof_odon` | returns data with `key="prof_odon"`, `value=[...]`, `descripcion` |
| Not found | key `fake_key` does not exist | `GET /api/catalogos/fake_key` | returns 404 |

### R3: Crear catálogo (`POST /api/catalogos`)

The system MUST create a new catalog entry. Request body SHALL include `key` (required, unique), `value` (JSONB array, default `[]`), `descripcion` (optional), `dominio` (optional). Key is immutable after creation. Response SHALL return the created catalog with status 201.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create success | body `{key: "nuevos_cups", value: ["CUPS1"], descripcion: "..."}` | `POST /api/catalogos` | 201, returns created catalog with `key="nuevos_cups"` |
| Duplicate key | catalog `prof_odon` already exists | `POST /api/catalogos` with `key: "prof_odon"` | 409, error message about duplicate key |
| Missing key | body without `key` field | `POST /api/catalogos` | 400, `"Campo requerido: key"` |
| Non-array value | body `{key: "x", value: "string"}` | `POST /api/catalogos` | 422, error indicating value MUST be a JSON array |

### R4: Actualizar catálogo (`PUT /api/catalogos/<key>`)

The system MUST update `value`, `descripcion`, and `dominio`. The `key` field SHALL NOT be changeable — any `key` in the body SHALL be ignored or rejected. `value` SHALL be a JSONB array (rejected otherwise). Returns updated catalog.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Update value | catalog `prof_odon` with value `["A"]` | `PUT /api/catalogos/prof_odon` `{value: ["A","B"]}` | value becomes `["A","B"]`, `updated_at` refreshes |
| Update descripcion | catalog exists | `PUT /api/catalogos/prof_odon` `{descripcion: "nueva desc"}` | only descripcion changes, key unchanged |
| Key ignored | body includes `key: "otro"` | `PUT /api/catalogos/prof_odon` | key remains `prof_odon`, ignored or 400 |
| Not found | key does not exist | `PUT /api/catalogos/fake` | 404 |
| Non-array value | body `{value: "string"}` | `PUT /api/catalogos/prof_odon` | 422 |

### R5: Eliminar catálogo (`DELETE /api/catalogos/<key>`)

The system MUST delete the catalog ONLY if no **active** rule references it via `condiciones WHERE operador='cat_in' AND valor_esperado=<key>`. If active rules exist → 409 with list of `{regla_id, nombre, estado, version}`. If only non-active rules (draft/retired) → allow with warning in response.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| No rules reference it | catalog `huérfano` has no condiciones referencing it | `DELETE /api/catalogos/huérfano` | 200, catalog deleted |
| Active rules reference it | 2 active rules use `cat_in` with key `prof_odon` | `DELETE /api/catalogos/prof_odon` | 409, `errors` lists `{regla_id, nombre, estado}` for each |
| Non-active rules only | 1 retired rule references key `old_cat` | `DELETE /api/catalogos/old_cat` | 200 with warning in response data |
| Not found | key does not exist | `DELETE /api/catalogos/fake` | 404 |

### R6: Listar reglas que referencian un catálogo (`GET /api/catalogos/<key>/reglas`)

The system MUST return all rules that have at least one condition using `operador='cat_in'` and `valor_esperado=<key>`. Each rule SHALL include `id`, `nombre`, `dominio`, `estado`, `version`, `activo`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has references | 2 rules use `cat_in` with `prof_odon` | `GET /api/catalogos/prof_odon/reglas` | returns array with 2 rules, each with id/nombre/estado |
| No references | catalog `sin_reglas` is unused | `GET /api/catalogos/sin_reglas/reglas` | empty array |
| Not found | key does not exist | `GET /api/catalogos/fake/reglas` | 404, or empty array (404 preferred) |

### R7: Frontend page (`/admin/catalogos`)

The React page SHALL follow the existing pattern in `admin-reglas/`: `index.html` → `main.tsx` → `page.tsx`, with entry registered in `vite.config.ts`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Main table renders | 5 catalogs exist | page loads | table shows rows: key, descripción, dominio, value preview (truncated), rule count badge |
| Create dialog | user clicks "Nuevo catálogo" | modal opens with form | fields: key (required), descripcion, dominio, value (tag input). Submit calls `POST /api/catalogos` |
| Edit dialog | user clicks edit on `prof_odon` | modal opens pre-filled | key is read-only (disabled input), other fields editable. Submit calls `PUT /api/catalogos/prof_odon` |
| Delete with rules | `prof_odon` has 2 active rules | user clicks delete | confirmation shows "2 reglas activas referencian este catálogo", confirm returns 409 error display |
| Delete without rules | `huérfano` has no rules | user clicks delete | confirmation dialog, confirm succeeds, row removed from table |
| View rules | catalog has 3 referencing rules | user clicks "Ver reglas" | modal/section shows table: regla_id, nombre, estado, dominio badge |
| Loading state | API in-flight | page mounts | spinner / Loader2 shown |
| Error state | API returns 500 | fetch fails | error message + retry button |

---

## Validation Rules

| Field | Rule |
|-------|------|
| `key` (POST) | MUST be non-empty, unique, immutable after creation |
| `value` (POST/PUT) | MUST be a JSON array — non-array values MUST be rejected with 422 |
| `descripcion` | MAY be null or empty string |
| `dominio` | MAY be null — informational, not used as engine filter |
| DELETE guard | MUST reject with 409 if `condiciones` has rows with `operador='cat_in'` AND `valor_esperado=<key>` AND `regla.activo=true` |

---

## Acceptance Criteria

- [ ] CRUD endpoints: list, get, create, update, delete all functional
- [ ] Delete blocked (409) when active rules reference the catalog
- [ ] Delete allowed when no rules or only non-active rules reference it
- [ ] Non-array `value` rejected (422) on create and update
- [ ] Duplicate `key` rejected (409) on create
- [ ] Key immutable on update (PUT ignores/rejects key change)
- [ ] `GET /api/catalogos/<key>/reglas` returns referencing rules
- [ ] Page `/admin/catalogos` renders table, create/edit/delete dialogs, rules view
- [ ] Vite build succeeds with new `admin-catalogos` entry point
- [ ] Tests pass for all CRUD endpoints + dependency validation
