# Proposal: HAZLO E INTEGRAKO — Visual Catalog Management UI

## Intent

Provide a visual interface to manage the entity-procedure relationship chain (EpsContratado ↔ Procedimiento via SQLAlchemy) plus PostgreSQL procedimientos, replacing direct DB manipulation.

## Scope

### In Scope
- React page under `/catalogo` for catalog management
- Backend `GET /api/eps/<id>/procedimientos` for the relationship chain
- CRUD visualization for EpsContratado, Procedimiento (SQLite), Procedimientos (PostgreSQL)
- Flask Blueprint `app/routes/catalogo.py` + nav entry
- Protection behind `permiso: "*"` (admin-only)

### Out of Scope
- NotaHoja, NotasTecnicas, EpsNota CRUD (deferred to P1)
- Chain tree visualization (P2)
- Bulk import/export
- Audit logging

## Capabilities

### New Capabilities
- `catalog-management`: Visual CRUD for procedure and entity catalogs across SQLite and PostgreSQL databases

### Modified Capabilities
- None

## Approach

Single React page under `/catalogo` with 3 tabs:

1. **EpsContratado** — table + create/edit modal consuming `/api/eps`
2. **Procedimiento (SQLite)** — table + create/edit modal consuming `/api/procedimientos`
3. **Procedimientos (PostgreSQL)** — table + create/edit modal consuming `/procedimientos`

Reuse existing table+modal pattern from usuarios page. Add `GET /api/eps/<id>/procedimientos` to `notas_api.py` for chain queries. Protect with `@admin_requerido`. Data flow: fetch on mount → table render → modal create/edit → POST/PUT → re-fetch. Plain `useState` + `useEffect`, no new dependencies.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/routes/catalogo.py` | **NEW** | Flask Blueprint: `GET /catalogo` → React shell |
| `app/__init__.py` | Modified | Register `catalogo` blueprint |
| `app/routes/notas_api.py` | Modified | Add `GET /api/eps/<id>/procedimientos` |
| `frontend/vite.config.ts` | Modified | Add `catalogo` entry in rollupOptions.input |
| `frontend/src/pages/catalogo/` | **NEW** | `index.html` + `main.tsx` + `page.tsx` |
| `frontend/src/components/app-sidebar.tsx` | Modified | Add nav link to `/catalogo` with `permiso: "*"` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Two DBs in one UI confuses users | Low | Clear tab labels and section headers |
| No pagination on large datasets | Low | Acceptable for local catalogs (<500 records) |
| Permission model unclear | Med | Admin-only via `permiso: "*"` in sidebar + `@admin_requerido` |

## Rollback Plan

1. Remove blueprint registration from `app/__init__.py`
2. Remove nav entry from `app-sidebar.tsx`
3. Remove `vite.config.ts` entry → rebuild
4. Delete `app/routes/catalogo.py`
5. Delete `frontend/src/pages/catalogo/`
6. Remove relationship endpoint from `notas_api.py` if unused elsewhere

## Dependencies

- Existing CRUD endpoints in `notas_api.py` — no new backend dependencies
- Existing React components: Card, Button, Input, StatusBadge, PageTitle

## Success Criteria

- [ ] `/catalogo` loads all 3 entity tables with data from their respective APIs
- [ ] Create/edit/delete operations work for each entity
- [ ] `GET /api/eps/<id>/procedimientos` returns correct chain data
- [ ] Page protected behind admin role — non-admins get 403
- [ ] Vite build succeeds with the new entry point
