# react-frontend Specification

## Purpose

React pages served from Flask via Vite build pipeline and shadcn/ui component library.
Each React page is a standalone entry point (Multi-Page App) embedded in a Flask shell
template that extends `base.html`.

## Requirements

### Requirement: React page renders via Flask shell

The system MUST serve a React-powered page at `/abiertas-urgencias/react`
that visually matches the component in `data/import/abiertas-urgencias.tsx`,
using a Flask shell template (`react_shell.html`) extending `base.html`
with a `<div id="root">` mount point.

#### Scenario: Page loads with all three cards

- GIVEN an authenticated user with `facturas_abiertas` permission
- WHEN they navigate to `/abiertas-urgencias/react`
- THEN the shell template extends `base.html` (sidebar, header render)
- AND the content area renders three Card sections in order:
  Asignar responsable, Ver horario, Aviso (falta cargar horario)

#### Scenario: Existing Jinja2 route unchanged

- GIVEN the React route exists at `/abiertas-urgencias/react`
- WHEN navigating to `/abiertas-urgencias` (without `/react`)
- THEN the original Jinja2 template is served

### Requirement: Collapsible sections with icon and color scheme

Each Card section MUST have a clickable header with icon, title, subtitle,
and a chevron toggle (ChevronDown/ChevronUp). Only the warning card
(Aviso) MUST be non-collapsible and always visible.

#### Scenario: Asignar responsable opens and closes

- GIVEN the page has loaded
- WHEN the user clicks the "Asignar responsable" card header
- THEN the collapsible body toggles visibility
- AND the chevron icon flips between ChevronDown and ChevronUp

#### Scenario: Ver horario opens and closes

- GIVEN the page has loaded
- WHEN the user clicks the "Ver horario" card header
- THEN the schedule table section toggles visibility
- AND the chevron icon flips accordingly

#### Scenario: Warning card is non-collapsible

- GIVEN the page has loaded
- WHEN the user clicks the "Falta cargar el horario" card
- THEN no toggle occurs — it is a static alert

### Requirement: Empty schedule state

The Ver horario card MUST show an empty state with CalendarDays icon,
"Sin datos de horario" message, and instructional subtext when no
schedule data is available.

#### Scenario: No schedule shows empty state

- GIVEN the page has loaded with no schedule data
- WHEN the Ver horario section is expanded
- THEN a table is rendered with column headers (Día, 07:00–13:00,
  13:00–19:00, 19:00–07:00)
- AND a single cell spans all columns showing the empty state

### Requirement: Server-to-client data injection

The system MUST set `window.__INITIAL_DATA__` in the shell template
via Jinja2 before the React bundle loads, containing initial schedule
and user permission data.

#### Scenario: Initial data accessible in React

- GIVEN the React bundle has loaded
- WHEN the component mounts
- THEN `window.__INITIAL_DATA__` is a non-null object with expected
  shape (schedule data, permissions)
- AND the component can read and render based on this data

#### Scenario: Non-JavaScript fallback

- GIVEN a user with JavaScript disabled
- WHEN `/abiertas-urgencias/react` loads
- THEN a `<noscript>` tag SHOULD display a message prompting the
  user to enable JavaScript

### Requirement: Build pipeline produces correct assets

The Vite build (frontend/`npm run build`) MUST output bundled JS
and CSS to `app/static/react-dist/` with hashed filenames under
`assets/`, and Flask MUST serve them via `/static/react-dist/...`.

#### Scenario: Build output structure

- GIVEN a successful `npm run build` in `frontend/`
- THEN `app/static/react-dist/assets/` contains `index-*.js`
  and optionally `index-*.css`
- AND the shell template references the correct hashed filenames

#### Scenario: Broken build prevents update

- GIVEN a Vite build that fails
- THEN the previous build output remains intact
- AND Flask continues serving the previous bundle

## Out of Scope

- TanStack Router (Phase 1 uses MPA without client-side routing)
- Migration of other Flask pages (abiertas-urgencias, index/dashboard, control-novedades, and urgencias are React pages; remaining pages stay Jinja2)
- React testing framework (deferred to a later phase)
- Hot reload or Vite dev proxy in development mode
- Component-level unit tests

## ADDED Requirements

### Requirement: Dashboard page at `/react`

The system MUST serve a React dashboard at `/react` matching `data/import/index.tsx`
(3 KPI cards, 3 area Link cards with StatusBadge for pending counts, footer).

#### Scenario: Full page renders with KPIs and area cards

- GIVEN initial data loaded via `window.__INITIAL_DATA__`
- WHEN navigating to `/react`
- THEN three KPI cards render with value, trend subtext, and icon
- AND three area Link cards render with icon, title, description, and zero or more StatusBadge
- AND footer displays version text

#### Scenario: Zero-pending area hides badge

- GIVEN an area with `pending: 0`
- WHEN the card renders
- THEN no StatusBadge appears for that card

### Requirement: Control Novedades page at `/control-errores/react`

The system MUST serve a React page at `/control-errores/react` matching
`data/import/control-novedades.tsx` (month tabs bar with counts, 3 KPI cards,
filter bar with Search input + category/state/responsible selects + Limpiar,
table with Factura/Creado/Categoría/Descripción/Facturador/Estado/Acciones
columns and Eye/Pencil/Trash2 action icons).

#### Scenario: Full page renders all sections

- GIVEN initial months and novedades data
- WHEN navigating to `/control-errores/react`
- THEN month tabs bar renders with active tab highlighted (primary border + filled badge)
- AND 3 KPI cards display (Total registrados, Pendientes, Resueltos)
- AND filter bar renders with all controls
- AND table renders with all columns and rows including action icons

#### Scenario: Month tab switches on click

- GIVEN the tabs bar with multiple month entries
- WHEN clicking a non-active tab
- THEN that tab becomes active (primary border bottom + filled count badge)
- AND the previously active tab reverts to default styling

### Requirement: Urgencias page at `/urgencias/react`

The system MUST serve a React page at `/urgencias/react` matching
`data/import/urgencias.tsx` (upload card with dashed-border drop zone, file name
display, info alert, Procesar button; error detection card with total counter,
category grouping via StatusBadge, error table with Controlar button per row).

#### Scenario: Page loads with upload and error cards

- GIVEN initial data
- WHEN navigating to `/urgencias/react`
- THEN upload card renders with dashed-border drop zone and Upload icon
- AND info alert shows file requirements
- AND error card renders with AlertTriangle icon, total count, and category badge

#### Scenario: File selection reveals name in drop zone

- GIVEN the upload card with no file selected (placeholder text visible)
- WHEN user selects an accepted-format file via the hidden input
- THEN file name appears with FileSpreadsheet icon
- AND Procesar button with ArrowRight icon is visible

#### Scenario: Error table has Controlar action per row

- GIVEN errors exist in initial data
- WHEN the error table renders
- THEN each row shows Factura (monospace), Responsable, Descripción, Procedimiento, Detalle (as StatusBadge)
- AND a "Controlar" button with ArrowRight icon renders in the last column

### Requirement: Shared components

The system MUST provide StatusBadge (tones: danger, warning, success, info,
neutral; optional `dot` prop), Input (shadcn Input), and Select (native
`<select>` styled via className) components available to all three pages.

#### Scenario: StatusBadge renders all tone variants

- GIVEN the StatusBadge component
- WHEN rendered with each tone value
- THEN each variant produces a distinct visual color scheme
- AND the `dot` prop prepends a colored circle prefix

#### Scenario: Select renders native element

- GIVEN a Select component with `<option>` children
- WHEN rendered
- THEN a native `<select>` element is output with consistent border, background, and height
