# Design: CRUD catálogos modificables + reglas que los referencian

## Technical Approach

Backend: new SRP service `app/services/reglas/catalogos_service.py` + 6 new endpoints on existing `reglas_api` blueprint. Frontend: new MPA page `admin-catalogos` following `admin-reglas` pattern exactly (Vite entry, Flask shell route, React components with shadcn/ui). The `catalogos` table already exists in prod with columns `id, key, value (JSONB), dominio, descripcion, updated_at` — the inline `CREATE TABLE IF NOT EXISTS` in the old endpoint is stale; the migration is already done.

## Architecture Decisions

### Decision: Service location

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `app/services/reglas/catalogos_service.py` | Same package as rule services; clear SRP | ✅ **Selected** |
| `app/services/catalogos_service.py` | Root services dir, but no other root services exist | ❌ Inconsistent |
| Inline in routes | Violates AGENTS.md rules | ❌ Rejected |

### Decision: Routes on existing blueprint

`reglas_api_bp` already has `url_prefix="/api"` and an existing `GET /api/catalogos/<key>` endpoint. Adding sibling endpoints to the same blueprint avoids creating a new Blueprint registration and follows the principle of least surprise. The old `GET /api/catalogos/<key>` route will be refactored to delegate to the new service.

### Decision: DB queries via raw SQL (`text()`)

No model class exists for `catalogos`. Using `db.execute(text(...))` with named params matches the existing pattern in `reglas_api.py` and avoids creating an ORM model for a simple CRUD table.

### Decision: Key immutability (design-time, enforced by API)

`POST` defines the key, `PUT` does not accept key changes. UI will show key as read-only in edit mode. To "rename" a catalog, users must create a new one and manually migrate rule references.

## Data Flow

```
Frontend (admin-catalogos) ──HTTP──→ reglas_api_bp ──→ catalogos_service.py ──→ PostgreSQL
                                              │
                                              └──→ condiciones + reglas (DELETE/reglas check)
```

**DELETE flow**: service queries `condiciones WHERE operador='cat_in' AND valor_esperado=:key`, joins with `reglas` to get rule names + estado. If any active rule found → raises `ValueError("...")` → route returns 409 with rule list. Draft/retired/deprecated rules produce a warning field in the response but allow deletion.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/reglas/catalogos_service.py` | Create | SRP: list, get, create, update, delete, get_reglas for catalogos |
| `app/routes/reglas_api.py` | Modify | Add 6 endpoints; refactor existing `GET /api/catalogos/<key>` to delegate to service |
| `app/routes/reglas_admin.py` | Modify | Add `GET /admin/catalogos` route (same pattern as `/admin/reglas`) |
| `frontend/src/pages/admin-catalogos/index.html` | Create | HTML shell |
| `frontend/src/pages/admin-catalogos/main.tsx` | Create | React mount with AppLayout |
| `frontend/src/pages/admin-catalogos/page.tsx` | Create | CatalogosList, CatalogoDialog, DeleteConfirmDialog, ReglasVinculadas |
| `frontend/src/lib/api-reglas.ts` | Modify | Add `CatalogoListItem`, `ReglasQueReferencian` types + CRUD functions |
| `frontend/vite.config.ts` | Modify | Add `admin-catalogos/index.html` to `rollupOptions.input` |
| `tests/routes/test_catalogos_api.py` | Create | CRUD + delete validation tests |

## Interfaces / Contracts

### Backend API (on `/api` blueprint)

```
GET    /api/catalogos          → {status, data: CatalogoListItem[], errors}
GET    /api/catalogos/<key>    → {status, data: {key, values, count, dominio, descripcion}, errors}
POST   /api/catalogos          → {status, data: CatalogoRow, errors}
PUT    /api/catalogos/<key>    → {status, data: CatalogoRow, errors}
DELETE /api/catalogos/<key>    → {status, data: {warnings?: {...}}, errors}
                                 ↳ 409 on active rule dependency: {status: "error", data: {reglas: [...]}, errors}
GET    /api/catalogos/<key>/reglas → {status, data: ReglaRef[], errors}
```

### Key Types

```typescript
interface CatalogoListItem {
  key: string;
  descripcion: string | null;
  dominio: string | null;
  value_count: number;
  updated_at: string | null;
}

interface CatalogoRow extends CatalogoListItem {
  values: string[];
}

interface ReglaRef {
  id: number;
  nombre: string;
  dominio: string;
  estado: string;
}

interface CreateCatalogoPayload {
  key: string;
  values: string[];
  descripcion?: string;
  dominio?: string;
}
```

### Service API (Python)

```python
# catalogos_service.py
def list_catalogos(db: Session) -> list[dict]: ...
def get_catalogo(db: Session, key: str) -> dict | None: ...
def create_catalogo(db: Session, data: dict) -> dict: ...
def update_catalogo(db: Session, key: str, data: dict) -> dict: ...
def delete_catalogo(db: Session, key: str) -> dict: ...
def get_catalogo_reglas(db: Session, key: str) -> list[dict]: ...
```

### DB Table (already exists)

```sql
catalogos (
    id          SERIAL PRIMARY KEY,
    key         VARCHAR(200) NOT NULL UNIQUE,
    value       JSONB NOT NULL DEFAULT '[]'::jsonb,
    dominio     TEXT,
    descripcion TEXT,
    updated_at  TIMESTAMPTZ DEFAULT now()
)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (service) | CRUD operations, delete validation (empty, with draft rules, with active rules → 409), update no-op | pytest with real DB session, raw SQL assertions |
| Integration | Endpoint response format, 409 body structure | Flask test client with `reglas_api_bp` |
| Frontend | List renders, dialog opens, delete shows rule warning modal | Not in scope for this phase |

## Migration / Rollout

No migration required — table already exists. The inline `CREATE TABLE IF NOT EXISTS` in the old `GET /api/catalogos/<key>` will be removed during refactoring since the table is already deployed.

## Open Questions

None.
