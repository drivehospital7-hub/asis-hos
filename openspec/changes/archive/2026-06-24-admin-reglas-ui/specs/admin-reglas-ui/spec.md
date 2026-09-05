# admin-reglas-ui Specification

## Purpose

React-based admin interface for the rule engine, following the same multi-page Vite pattern as `frontend/src/pages/catalogo/`. Users (admin role) SHALL be able to list, create, edit, version, and test rules without writing SQL. The UI SHALL use existing shadcn/ui components, Lucide icons, Tailwind CSS, and the `AppLayout` + `react_shell.html` rendering pipeline.

---

## ADDED Requirements

### R1: Rules List View

The main view MUST display a table of rules with columns: `nombre`, `dominio`, `estado` (color-coded badge), `version`, `prioridad`, `severidad` (color-coded badge), and action buttons (editar, versionar, desactivar/activar). Two filter controls SHALL be provided above the table: a `dominio` select and an `estado` select. A search input SHALL filter by `nombre` (client-side or debounced API search).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Render list | user with admin permisos navigates to page | `GET /api/reglas` resolves with 10 rules | table renders 10 rows with badges, actions visible |
| Filter by dominio | user selects "odontología" from domain filter | filter change triggers re-fetch | only odontología rules shown |
| Search by nombre | user types "decimal" in search box | search input with debounce | table filters to rules matching "decimal" in nombre |
| Empty state | no rules returned | API returns empty array | "No hay reglas" empty state rendered |
| Loading state | API in-flight | component mounts | spinner/Loader2 shown while data loads |
| Error state | API returns error | fetch fails | error message + retry button rendered |

### R2: Rule Detail / Edit Form

The rule detail view MUST show an editable form with fields: `nombre` (text), `descripcion` (textarea), `dominio` (select from allowed values), `severidad` (select: baja/media/alta/critica), `prioridad` (number). Below the basic fields, a **condition tree builder** SHALL allow editing the rule's condition tree.

Each tree node SHALL be:
- **Composite**: type AND/OR/NOT with a list of child nodes, each child removable via [×] button and new children addable via [+]
- **Atomic**: operator select (eq, gt, lt, gte, lte, in, contains, regex) + field selector + value input

The tree SHALL render with indentation/visual nesting. Save SHALL serialize the tree as JSON and `PUT /api/reglas/<id>`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Load for edit | user clicks "Editar" on a rule | `GET /api/reglas/<id>` returns rule with nested conditions | form populated, condition tree rendered with indentation |
| Add composite node | user clicks [+] on root node, selects AND | new AND node appears as child | tree updated, Save sends correct JSON |
| Add atomic leaf | user clicks [+] on AND node, fills operator+field+value | new atomic leaf appears | tree updated, Save sends correct JSON |
| Remove node | user clicks [×] on a child node | node removed from tree | Save sends tree without that node |
| Save changes | user edits nombre + adds a condition | clicks "Guardar" | `PUT /api/reglas/<id>` called, success toast shown, returns to list |
| Validation error | user submits with empty nombre | clicks "Guardar" | inline error on nombre field, no API call made |

### R3: Exceptions Panel

A tab or panel SHALL list all exceptions for the current rule in a table: `tipo_efecto`, `condicion_json` (truncated), `activo` (toggle badge). A "Nueva Excepción" button SHALL open a modal with fields for `tipo_efecto` (select), `condicion_json` (JSON textarea), `activo` (checkbox).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List exceptions | rule with 3 exceptions | view exceptions panel | table renders 3 exceptions |
| Create exception | user fills modal form | submits "Crear" | `POST /api/reglas/<id>/excepciones` called, modal closes, table refreshes |
| Toggle activo | exception is active | user clicks toggle | `PUT` call toggles state, badge updates |

### R4: Version History Timeline

A timeline view SHALL list all versions of a rule, ordered newest-first. Each entry SHALL display: version number, estado (color-coded badge: active/draft/deprecated/retired), `creado_en` timestamp, and a "Ver detalle" link (which loads that version's data read-only).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Version history | R1 has 4 versions | open version history tab | 4 entries shown, newest first, badges colored by estado |
| View old version | user clicks "Ver detalle" on v2 (deprecated) | detail loaded read-only | form fields show v2 data, inputs disabled, "Volver" button |
| Create new version | user clicks "Versionar" button | `POST /api/reglas/<id>/versionar` | new draft version created, timeline refreshes, toast confirms |

### R5: Evidence Dashboard

A search form SHALL provide filters: `factura` (text), `regla_id` (select or number), `dominio` (select), date range (`desde`/`hasta` date inputs). A "Buscar" button SHALL trigger `GET /api/evidencias` with the filters. Results SHALL render in a paginated table with columns: `factura`, `regla_id`, `version`, `dominio`, `resultado` (badge), `creado_en`. Pagination controls SHALL show page numbers and total count.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Search by factura | user inputs factura="F001" | clicks "Buscar" | evidence for F001 shown |
| Paginate results | 250 total results, page size 25 | user clicks page 2 | results 26-50 shown, total=250 displayed |
| No results | no evidence matches filters | clicks "Buscar" | "Sin resultados" empty state |
| Clear filters | filters populated | clicks "Limpiar" | all filters reset, fresh query without params |

### R6: Simulator View

A file upload area SHALL accept an Excel file (`.xlsx`/`.xls`). An optional rule selector SHALL allow filtering which rules to simulate. A "Simular" button triggers `POST /api/reglas/simular` (multipart). Results SHALL display in two side-by-side tables: **Engine Results** (DB-backed) vs **Legacy Results** (Python detectors), with a **diff summary** showing matched, mismatched, and only-in-engine/only-in-legacy counts.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Upload and simulate | user selects Excel with 50 rows, no rule filter | clicks "Simular" | spinner shown during request, then two tables + diff summary rendered |
| Show diff | engine detects 8 problems, legacy 10, 6 match | simulation completes | diff shows: 6 matched, 2 engine-only, 4 legacy-only |
| Invalid file | user uploads PDF | file input validates | inline error: "Formato no válido. Seleccioná un archivo Excel." |
| Large file warning | user uploads Excel with 500 rows | file selected | warning banner: "Solo se procesarán las primeras 100 filas." |
| No file | clicks "Simular" without file | submits form | inline validation: "Seleccioná un archivo Excel primero" |

---

## Acceptance Criteria

- [ ] All views render without JS errors — use `window.__INITIAL_DATA__` for user context
- [ ] Tree builder creates valid nested condition JSON matching the engine's tree format
- [ ] All CRUD operations reflect in the list within 1s (optimistic or refresh)
- [ ] Evidence search paginates correctly with total count
- [ ] Simulator comparison diff shows matched/mismatched/unique counts
- [ ] All pages follow the existing `catalogo/` pattern: `index.html`, `main.tsx`, `page.tsx`, entry in `vite.config.ts`
- [ ] API client in `api-reglas.ts` follows exact `api-catalogo.ts` pattern with typed functions and shared helpers
