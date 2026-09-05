## Exploration: HAZLO E INTEGRAKO — Visual Management UI for Entity-Procedure Relationship Chain

### Current State

**Two independent databases coexist, each with its own CRUD layer:**

| Aspect | SQLite (local catalog) | PostgreSQL (external DB) |
|--------|----------------------|--------------------------|
| Models | `app/models.py` — EpsContratado, Procedimiento, NotaHoja, NotasTecnicas, EpsNota | `app/services/procedimientos_db.py` — procedimientos table |
| API | `app/routes/notas_api.py` — `/api/eps`, `/api/procedimientos`, `/api/notas-hoja`, `/api/notas-tecnicas`, `/api/eps-nota` (FULL CRUD) | `app/routes/procedimientos.py` — `/procedimientos` (FULL CRUD) |
| CRUD services | 5 files in `app/services/` (eps_contratado_crud, procedimiento_crud, nota_hoja_crud, notas_tecnicas_crud, eps_nota_crud) | 2 files in `app/services/` (procedimientos_db, procedimientos_crud) |
| Frontend | ❌ NONE — no React pages exist for catalog management | ❌ NONE — no React pages exist for PostgreSQL procedimientos |

**The relationship chain (SQLite) visualized:**

```
EpsContratado (cod_contrato, eps, regimen)
    └── EpsNota (id_eps_contratado → id_nota_hoja)
            └── NotaHoja (nota)
                    └── NotasTecnicas (id_nota_hoja → id_procedimiento, tariff)
                            └── Procedimiento (cups, procedimiento)
```

**How `detect_cups_sin_contrato` consumes this chain today** (`app/services/transversales/procedimiento_contratado.py`):

1. Opens a SQLAlchemy session to SQLite
2. Joins through all 5 tables: `EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento`
3. Builds a `set[(cod_contrato, cups)]` of valid pairs
4. For each Excel row, checks if `(cod_entidad_cobrar, codigo)` is in that set
5. Returns "CUPS no contratado" errors for missing pairs

**Existing API endpoints for SQLite models** (`app/routes/notas_api.py`):

| Entity | GET list | GET by id | POST | PUT | DELETE |
|--------|----------|-----------|------|-----|--------|
| EpsContratado | `/api/eps` | `/api/eps/<id>` | ✅ | ✅ | ✅ |
| Procedimiento | `/api/procedimientos` | `/api/procedimientos/<id>` | ✅ | ✅ | ✅ |
| NotaHoja | `/api/notas-hoja` | `/api/notas-hoja/<id>` | ✅ | ✅ | ✅ |
| NotasTecnicas | `/api/notas-tecnicas` | `/api/notas-tecnicas/<id>` | ✅ | ✅ | ✅ |
| EpsNota | `/api/eps-nota` | `/api/eps-nota/<id>` | ✅ | ❌ (no PUT) | ✅ |

**Missing API capabilities:**
- No endpoint for "get all procedures for a given EPS through the chain" (`/api/eps/<id>/procedimientos`)
- No endpoint for "get the full chain as a tree" relevant to the cruce validation
- No endpoint for the PostgreSQL `procedimientos` table consumed from React

**Frontend patterns already established** (fully reusable):
- MPA architecture with Vite multi-entry build (`vite.config.ts` lists 12 HTML entries)
- Each page = `index.html` + `main.tsx` (entry) + `page.tsx` (component) in its own directory under `frontend/src/pages/`
- Common components: `AppLayout`, `AppSidebar`, `AppHeader`, `Card`, `Button`, `Input`, `PageTitle`, `StatusBadge`, `Breadcrumbs`, `ConfirmDialog`
- `lib/utils.ts` has `cn()` helper (clsx + tailwind-merge)
- Data initialization via `window.__INITIAL_DATA__` injected in Jinja2 template
- Async operations via raw `fetch()` with JSON parsing (no axios, no react-query)
- Tailwind v4 with custom oklch design tokens
- Authentication via Flask session cookie (session-based, not JWT)

**The Flask route pattern for serving a React page** (shown in `app/routes/odontologia_equipos_basicos.py`, `app/routes/home.py`, `app/routes/auth.py`):
1. Read manifest.json for the entry JS/CSS
2. Render `react_shell.html` with `initial_data` dict
3. Decorate with `@permiso_requerido(...)` or `@admin_requerido`
4. Register blueprint in `app/__init__.py`
5. Add entry to `frontend/vite.config.ts` rollupOptions.input
6. Add navigation entry in `frontend/src/components/app-sidebar.tsx`

### Affected Areas

| File | Role |
|------|------|
| `app/routes/notas_api.py` | **May need enrichment** — add relationship-aware endpoints (`/api/eps/<id>/procedimientos`, `/api/eps/<id>/chain`) |
| `app/services/` (5 CRUD files) | Already complete — no changes needed to the CRUD itself |
| `app/routes/procedimientos.py` | PostgreSQL routes already exist — no changes needed to backend |
| `app/__init__.py` | Must register new Blueprint for the catalog React page |
| `frontend/vite.config.ts` | Must add new HTML entry point(s) |
| `frontend/src/components/app-sidebar.tsx` | Must add navigation entry for the new pages |
| `frontend/src/pages/` | **NEW** — one or more React page directories for catalog management |
| `frontend/src/components/` | Reuse existing — no new components needed (Button, Card, Input, etc. already exist) |
| `app/templates/react_shell.html` | Already generic — no changes needed |

**New files to create:**

| New File | Purpose |
|----------|---------|
| `app/routes/catalogo.py` | Flask Blueprint: GET /catalogo → React shell, potentially new JSON API endpoints |
| `frontend/src/pages/catalogo/index.html` | HTML shell for catalog page |
| `frontend/src/pages/catalogo/main.tsx` | Entry point wrapping AppLayout |
| `frontend/src/pages/catalogo/page.tsx` | Main React component — central management UI |

### Approaches

1. **Custom React pages (one unified catalog page with tabs/sections)**
   - Build a single new React page at `frontend/src/pages/catalogo/` with multiple sections or tabs for each entity
   - Each section has a table (list) + inline form or modal for create/edit
   - Consume existing `/api/` endpoints directly from the browser
   - Add Flask Blueprint `app/routes/catalogo.py` for the React shell
   - Add relationship-rich JSON endpoints to `notas_api.py` as needed
   - **Pros**: Full control over UX, consistent with existing MPA patterns, no new dependencies, can show the chain visually (tree or nested table)
   - **Cons**: More upfront development per entity (5 entities = 5 sets of list/form views), no pagination on the backend (all `get_all()` queries)
   - **Effort**: High (est. 3-5 days for a complete page with all 5 entities + chain view + PostgreSQL integration)

2. **Flask-Admin auto-generated interface**
   - Install `Flask-Admin` (add to requirements.txt)
   - Register models and auto-generate CRUD views
   - Access at `/admin/` URL
   - **Pros**: Fastest to set up (hours, not days), all CRUD operations auto-generated, search/filter built-in
   - **Cons**: No visual chain view (flat per-model CRUD only), Jinja2-based (inconsistent with React frontend), styling mismatch with the shadcn/ui design system, hard to extend with custom business logic, adds a new dependency to maintain
   - **Effort**: Low (2-4 hours for initial setup)

3. **Hybrid: Flask-Admin for simple CRUD + Custom React for chain visualization**
   - Use Flask-Admin for per-entity CRUD (EpsContratado, Procedimiento, NotaHoja, etc.)
   - Build a single React page for the chain visualization (the hierarchical view showing EpsContratado → all linked procedures)
   - **Pros**: Quick CRUD for data entry, rich visualization for the complex chain view
   - **Cons**: Two UI systems to maintain (Jinja2 + React), styling split, navigation confusion, Flask-Admin still doesn't match the app's design system
   - **Effort**: Medium (React chain view similar to Approach 1, plus Flask-Admin setup)

### Recommendation

**Approach 1 — Custom React page(s).** Here's why:

1. **The project already has a mature React frontend pattern.** Adding Flask-Admin would introduce a second, inconsistent UI system. Every existing page uses React + shadcn/ui + Tailwind — the catalog should follow the same pattern.

2. **The chain visualization is the core value.** The most important view is not "edit a single NotasTecnicas row" but rather "see that EpsContratado X has procedures A, B, C through the chain." Only a custom React page can render this effectively (nested tables, tree view, or expandable rows).

3. **The backend CRUD already exists.** The 5 endpoint sets in `notas_api.py` plus the 5 CRUD service files are complete and tested. No backend work is needed for basic operations — just call them from fetch().

4. **Reuse is maximized.** The existing `Card`, `Button`, `Input`, `StatusBadge`, `PageTitle`, and `Breadcrumbs` components handle the full UI surface. The usuarios page (`page.tsx`) already demonstrates the table + modal pattern needed here.

**What to build (prioritized):**

| Priority | Feature | Description |
|----------|---------|-------------|
| P0 | EpsContratado CRUD | Table + create/edit form (simplest, one field + regimen) |
| P0 | Procedimiento CRUD | Table + create/edit form (cups + procedimiento) |
| P0 | PostgreSQL procedimientos CRUD | Table linking to existing `/procedimientos` endpoints — bridge the two DBs in one UI |
| P1 | NotaHoja CRUD | Table + create/edit (single campo "nota") |
| P1 | NotasTecnicas CRUD | Table with foreign key selects (procedimiento dropdown + nota_hoja dropdown + tariff input) |
| P1 | EpsNota CRUD | Table with foreign key selects (eps dropdown + nota_hoja dropdown) |
| P2 | Chain visualization | For a selected EpsContratado, show all linked Procedimientos through the chain with tariffs |
| P2 | Search/filter | Search CUPS across both databases |

**Architecture of the catalog page:**

```
CatalogoPage
├── EpsContratadoSection
│   ├── Table (cod_contrato, eps, regimen, actions)
│   └── Modal (create/edit form)
├── ProcedimientoSection (SQLite)
│   ├── Table (cups, procedimiento, actions)
│   └── Modal (create/edit form)
├── ProcedimientoSection (PostgreSQL)
│   ├── Table (eps, codigo_cups, descripcion, tarifa, actions)
│   └── Modal (create/edit form)
├── NotaHojaSection
│   ├── Table (nota, actions)
│   └── Modal (create/edit form)
├── NotasTecnicasSection
│   ├── Table (id_procedimiento, id_nota_hoja, tariff, actions)
│   └── Modal (create/edit with foreign key dropdowns)
├── EpsNotaSection
│   ├── Table (id_eps_contratado, id_nota_hoja, actions)
│   └── Modal (create/delete)
└── ChainView
    ├── Select EpsContratado
    └── Tree/table showing all linked Procedimientos
```

**Data flow:**
- Each section fetches its data via `fetch("/api/...")` on mount
- Create/edit posts via `fetch("POST /api/...")` or `fetch("PUT /api/...")`
- Delete via `fetch("DELETE /api/...")`
- All responses follow the project's `{status, data, errors}` envelope
- No react-query or SWR — plain `useState` + `useEffect` (consistent with existing pages)

**Relationship endpoint to add to backend:**
- `GET /api/eps/<id>/procedimientos` — returns all procedimientos linked through the chain for a given EpsContratado
- This is the core query already implemented in `procedimiento_contratado.py` but filtered by EpsContratado

### Risks

- **All `get_all()` queries lack pagination.** If any table grows large (e.g., hundreds of Procedimientos), the frontend will load everything at once. This is acceptable for a local catalog (typically < 500 records) but should be noted.
- **Two databases in one UI.** The PostgreSQL `procedimientos` table is a separate system from the SQLite catalog. Users need to understand which is which. Clear labeling (tabs/sections) is critical.
- **No PUT for EpsNota.** The current API only supports create/delete (no update). This is fine for a many-to-many link table (replace = delete + recreate) but needs to be communicated in the UI.
- **Permission model.** The catalog page needs a new permission (e.g., `catalogo` or reuse `*` admin). Currently only admins manage these tables through direct SQL. Adding a UI means deciding who gets access.
- **Race conditions with `detect_cups_sin_contrato`.** If a user edits the catalog while someone runs a cruce, the validation results could be inconsistent. Low probability but worth noting.
- **Vite build complexity.** Adding a new entry point requires updating `vite.config.ts` rollupOptions.input. The existing list already has 12 entries — this is manageable but must not be forgotten.

### Ready for Proposal

**Yes.** The exploration is complete. The user should move to `sdd-propose` with this summary:

- The backend already has full CRUD for all 5 SQLite models via `notas_api.py` — no new endpoints needed for basic operations
- Only one relationship endpoint is missing: `GET /api/eps/<id>/procedimientos` (chain query already exists in `procedimiento_contratado.py`)
- The frontend pattern is well-established and fully reusable (MPA + shadcn/ui + fetch)
- **Recommendation**: Approach 1 — build a custom React page following the existing MPA pattern
- **No new backend dependencies** required; the work is ~80% frontend, ~20% backend (new Flask Blueprint + 1 enriched API endpoint)
- Key decision to discuss: What permission should protect the catalog page? (`catalogo` or `*` admin-only)
