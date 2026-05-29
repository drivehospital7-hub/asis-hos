# Design: HAZLO E INTEGRAKO — Visual Catalog Management UI

## Technical Approach

Single React page under `/catalogo` with 3 tabs (EpsContratado / Procedimiento-SQLite / Procedimientos-PostgreSQL). Each tab fetches from its existing API endpoint and renders a table + modal for create/edit/delete, following the exact pattern from `usuarios/page.tsx`.

New Flask blueprint `catalogo.py` serves the React shell and sits behind `@admin_requerido`. A relationship endpoint `GET /api/eps/<id>/procedimientos` joins the 5-model chain via SQLAlchemy ORM.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Page structure | Tabs / Sub-pages / Single list with filters | **Tabs** | 3 entities with different schemas — tabs keep all accessible from one URL, matching control-novedades "meses" pattern. |
| API client | fetch wrapper / generated client (OpenAPI) / react-query | **fetch wrapper** (`lib/api-catalogo.ts`) | No existing API generation infra. Plain fetch keeps deps at zero. Each tab calls its endpoint on mount + after mutate. |
| Relationship endpoint design | Flask route in `notas_api.py` / new service | **Route in `notas_api.py`** | Follows existing convention — all `/api/` endpoints live there. Query via SQLAlchemy ORM chaining with joinedload to avoid N+1. |
| Permission model | `@admin_requerido` / `@permiso_requerido("catalogo")` | **`@admin_requerido`** | Existing pattern for admin-only pages (usuarios, import-facturas). Matches sidebar `permiso: "*"`. No need for a new permiso. |
| Error handling | Per-table error state / global toast / modal | **Per-table error state** | Each tab independent — a PG connection failure shouldn't block SQLite tabs. Shows inline error with retry button. |
| State management | useState+useEffect per tab / Context / Zustand | **`useState` + `useEffect` per tab** | Tabs are independent data islands. No shared state needed. Matches all existing pages. |

## Data Flow

```
Browser                          Flask                          SQLite / PG
  │                                │                                │
  ├─ GET /catalogo                 │                                │
  │  ──────────────────────────►   │                                │
  │  ◄── react_shell.html ──────   │                                │
  │                                │                                │
  ├─ Tab 1: GET /api/eps           │                                │
  │  ──────────────────────────►   ├─ eps_contratado_crud.get_all()─►│
  │  ◄── list[EPS] ────────────────◄───────────────────────────────  │
  │                                │                                │
  ├─ Tab 2: GET /api/procedimientos│                                │
  │  ──────────────────────────►   ├─ procedimiento_crud.get_all() ─►│
  │  ◄── list[Proc (SQLite)] ──────◄───────────────────────────────  │
  │                                │                                │
  ├─ Tab 3: GET /procedimientos    │                                │
  │  ──────────────►               ├─ procedimientos_db ────────────►│
  │  ◄── list[Proc (PG)] ──────────◄───────────────────────────────  │
  │                                │                                │
  ├─ POST/PUT/DELETE on any tab    │                                │
  │  ──────────────►               ├─ CRUD service ─────────────────►│
  │  ◄── response ──────────────── ◄───────────────────────────────  │
  │  (re-fetch on success)         │                                │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/catalogo.py` | **Create** | Flask Blueprint `catalogo_bp` with `GET /catalogo` → renders `react_shell.html` for `src/pages/catalogo/index.html`. Protected by `@admin_requerido`. |
| `app/__init__.py` | Modify | Import and register `catalogo_bp` without url_prefix (route is `/catalogo`). |
| `app/routes/notas_api.py` | Modify | Add `GET /api/eps/<int:id>/procedimientos` returning full chain (EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento). |
| `frontend/src/pages/catalogo/page.tsx` | **Create** | Main page component with 3-tab structure. Each tab: data table + create/edit modal. |
| `frontend/src/pages/catalogo/main.tsx` | **Create** | React mount — `createRoot` + `<AppLayout><CatalogoPage /></AppLayout>`. |
| `frontend/src/pages/catalogo/index.html` | **Create** | Entry HTML (mirrors `usuarios/index.html`). |
| `frontend/src/lib/api-catalogo.ts` | **Create** | Typed fetch wrapper: `fetchEps()`, `fetchProcSqlite()`, `fetchProcPg()`, plus CRUD helpers with error handling. |
| `frontend/vite.config.ts` | Modify | Add `src/pages/catalogo/index.html` to `rollupOptions.input`. |
| `frontend/src/components/app-sidebar.tsx` | Modify | Add `{ label: "Catálogos", href: "/catalogo", icon: BookType, permiso: "*" }`. |

## Interfaces / Contracts

### Relationship endpoint: `GET /api/eps/<id>/procedimientos`

```json
{
  "status": "success",
  "data": {
    "eps": { "id": 1, "cod_contrato": "...", "eps": "EMSSANAR", "regimen": "SUBSIDIADO" },
    "procedimientos": [
      {
        "eps_nota_id": 1,
        "nota_hoja": "FACTURA ODONTO",
        "cups": "890201",
        "procedimiento": "EXODONIA SIMPLE",
        "tarifa": 45000.00
      }
    ]
  },
  "errors": []
}
```

### Frontend types (in `api-catalogo.ts`)

```typescript
interface EpsContratado { id: number; cod_contrato: string; eps: string; regimen: string; }
interface ProcedimientoSqlite { id: number; cups: string; procedimiento: string; }
interface ProcedimientoPg { id: string; eps: string; codigo_cups: string; descripcion: string | null; tarifa: number | null; }
```

### React component props (following existing pattern)

```typescript
interface TabTableProps<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  columns: ColumnDef<T>[];
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Relationship endpoint query logic | New test for `eps_contratado_crud` getting full chain — mock DB session with known relationships |
| Integration | Relationship endpoint via Flask test client | `app_client.get("/api/eps/1/procedimientos")` with seeded test DB |
| Integration | Catalogo blueprint returns 200 | Flask test client `GET /catalogo` with admin session |
| Frontend | Tab component renders data | React Testing Library — mount CatalogoPage with mock fetch |
| Frontend | Tab switching | Verify click changes visible content |

## Migration / Rollout

No migration required. Additive change — all new files and routes. Blueprint registration is the only activation step. Relationship endpoint can be tested independently before page goes live.

## Open Questions

- [ ] Permission model for the relationship endpoint: should it also be `@admin_requerido` or generic `@permiso_requerido`?
- [ ] Should the PostgreSQL procedimientos tab show a search/filter field? Currently returns all records which could be slow.
- [ ] Delete confirmation: use existing `window.__showConfirm` pattern or inline?
