# Catalog Management Specification

## Purpose

Visual CRUD for entity-procedure catalogs across SQLite (EpsContratado, Procedimiento CUPS) and PostgreSQL (Procedimientos tariffs), replacing direct DB manipulation. Single React page under `/catalogo` with entity tabs, admin-only access.

## Requirements

### R1: Catalog Page Access — Admin-Only

`GET /catalogo` SHALL render the React shell. The route SHALL be protected by `@admin_requerido`; the sidebar nav entry SHALL carry `permiso: "*"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin access | user session has `"*"` in permisos | navigates to `/catalogo` | React shell loads with 3 tabs |
| Non-admin 403 | user session lacks `"*"` | navigates to `/catalogo` | 403 or redirect to home |

### R2: EpsContratado Tab — SQLite CRUD

The tab SHALL list all EpsContratado rows (`GET /api/eps`). Each row SHALL show `cod_contrato`, `eps`, `regimen` with Edit/Delete actions. Create via modal (cod_contrato, eps, regimen) posting `POST /api/eps`. Edit via modal `PUT /api/eps/<id>`. Delete via confirm + `DELETE /api/eps/<id>`. Tab header SHALL read "EPS Contratadas (SQLite)".

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List | data exists | tab mounts | table renders all rows |
| Create | modal filled | POST succeeds | row appears; modal closes |
| Edit | modal pre-filled | PUT succeeds | row updated in table |
| Delete | confirm dialog | DELETE succeeds | row removed |
| Empty state | no records | tab mounts | "No hay EPS contratadas" message shown |
| Duplicate cod_contrato | POST with existing code | create submitted | 400 error displayed in modal |
| Missing required fields | POST without `eps` | create submitted | 400 error displayed in modal |

### R3: Procedimiento Tab (CUPS) — SQLite CRUD

The tab SHALL list all Procedimiento rows (`GET /api/procedimientos`). Each row SHALL show `id`, `cups`, `procedimiento`. Create via modal (cups, procedimiento) posting `POST /api/procedimientos`. Edit via modal `PUT /api/procedimientos/<id>`. Delete via confirm + `DELETE /api/procedimientos/<id>`. Tab header SHALL read "Procedimientos CUPS (SQLite)".

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List | data exists | tab mounts | table renders all rows |
| Create | modal filled | POST succeeds | row appears |
| Edit | fields changed | PUT succeeds | row updated |
| Delete | confirmed | DELETE succeeds | row removed |
| Empty state | no records | tab mounts | "No hay procedimientos CUPS" message |
| Duplicate CUPS | POST with existing cups | create submitted | 400 error in modal |
| Missing cups | POST without cups | create submitted | 400: "Campo requerido: cups" |

### R4: Procedimientos Tab (Tariffs) — PostgreSQL CRUD

The tab SHALL list Procedimientos filtered by EPS (`GET /procedimientos?eps=<eps>&all=true`). An EPS selector SHALL appear before the table. Each row SHALL show `id`, `eps`, `codigo_cups`, `descripcion`, `tarifa`. Create via modal (eps, codigo_cups, descripcion, tarifa) posting `POST /procedimientos`. Edit via modal `PUT /procedimientos/<id>`. Delete via confirm + `DELETE /procedimientos/<id>`. Tab header SHALL read "Tarifas Procedimientos (PostgreSQL)".

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List by EPS | EPS selected | table loads | rows filtered for that EPS |
| EPS selector | EPS list fetched | dropdown rendered | `GET /procedimientos/eps` populates options |
| Create | EPS + codigo_cups filled | POST succeeds | row appears |
| Edit | tarifa changed | PUT succeeds | row updated |
| Delete | confirmed | DELETE succeeds | row removed |
| No EPS selected | tab mounts | initial state | EPS selector prompt shown |
| Empty EPS result | no tariffs for EPS | table loads | "No hay tarifas para esta EPS" message |
| Missing EPS/codigo | POST without required | create submitted | 400: error list displayed |

### R5: Relationship View — Procedimientos by Entity

The tab SHALL show a "Ver Procedimientos" action per EpsContratado row. Clicking SHALL fetch `GET /api/eps/<id>/procedimientos` traversing the chain EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento. Results SHALL display in a read-only table showing `cups`, `procedimiento`, `tarifa`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Chain has results | entity has linked procedimientos | click "Ver Procedimientos" | read-only table lists all linked procedimientos |
| Empty chain | entity has no linked procedimientos | click "Ver Procedimientos" | "Sin procedimientos vinculados" message |
| Entity not found | invalid id | fetch attempted | 404 error notification |
| Close view | results displayed | click "Cerrar" or overlay | view closes, list returns |

### R6: Data Source Labeling

Each tab header SHALL include the data source label in parentheses: `(SQLite)` or `(PostgreSQL)`. The EPS selector in the PostgreSQL tab SHALL also indicate the source.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Tab labels | all 3 tabs visible | page renders | each tab reads `{Name} (SQLite)` or `{Name} (PostgreSQL)` |
| EPS selector | PostgreSQL tab active | label visible | selector reads "EPS (PostgreSQL)" |

## Validation Rules

| Field | Entity | Rule |
|-------|--------|------|
| `cod_contrato` | EpsContratado | MUST be non-empty string |
| `eps` | EpsContratado | MUST be non-empty string |
| `cups` | Procedimiento (SQLite) | MUST be non-empty, MUST be unique |
| `procedimiento` | Procedimiento (SQLite) | MUST be non-empty string |
| `eps` | Procedimientos (PG) | MUST be non-empty |
| `codigo_cups` | Procedimientos (PG) | MUST be non-empty |
| `tarifa` | Procedimientos (PG) | SHOULD be numeric, MAY be null |

## Acceptance Criteria

- [ ] `/catalogo` renders React shell with 3 tabs; non-admin gets 403
- [ ] EpsContratado tab: list, create, edit, delete via `/api/eps` endpoints
- [ ] Procedimiento CUPS tab: list, create, edit, delete via `/api/procedimientos` endpoints
- [ ] Procedimientos Tariffs tab: EPS selector, list, create, edit, delete via `/procedimientos` endpoints
- [ ] Relationship view: `GET /api/eps/<id>/procedimientos` returns chain data in read-only table
- [ ] All tabs show data source label (SQLite / PostgreSQL)
- [ ] Empty states, duplicate/missing field errors handled per entity
- [ ] Vite build succeeds with new `catalogo` entry point
