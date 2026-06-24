# Tasks: Admin UI para Motor de Reglas

## Review Workload Forecast

Estimated ~1400–1700 changed lines across DB, services, API, React, and tests. Exceeds 400-line budget — chained PRs recommended.

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1400–1700 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend → PR 2: Frontend → PR 3: Integration |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes — resolved as single PR (size:exception)
Chained PRs recommended: Yes — waived by maintainer (size:exception)
Chain strategy: single-pr
400-line budget risk: High — waived by maintainer (size:exception)

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | DB migration + 5 services + API routes + backend tests | PR 1 | Backend core, end-to-end testable via Flask client |
| 2 | React UI (5 views) + API client + admin route | PR 2 | All frontend files + reglas_admin.py + vite.config.ts |
| 3 | Integration: build + pytest pass + final fixes | PR 3 | Build verification, test suite green, polish |

---

## Phase 1: Foundation

- [x] 1.1 `app/models.py`: Add `rule_base_id` (Integer, nullable), drop `unique=True` on `nombre`, add `__table_args__` with `UniqueConstraint('nombre', 'version')`. Backfill existing rows with `rule_base_id = id`.
- [x] 1.2 Create `app/services/reglas/__init__.py` — package init.
- [x] 1.3 Create `app/services/reglas/rule_service.py` — `list_rules()` (filterable), `get_rule()` (nested tree + exceptions), `create_rule()` (draft, v1), `update_rule()` (transactional deprecate+create, partial update, no-op guard), `soft_delete()` (estado=retired), `list_versions()` (by rule_base_id, ordered DESC), `clone_as_draft()` (copy as new draft).
- [x] 1.4 Create `app/services/reglas/exception_service.py` — `list()`, `create()`, `toggle_active()` for exceptions linked to `regla_id`.
- [x] 1.5 Create `app/services/reglas/evidence_service.py` — `query()` wrapping `EvidenceRepository` with pagination (limit/offset) and canonical envelope.
- [x] 1.6 Create `app/services/reglas/audit_service.py` — `query()` over `ResultadoAuditoria` with pagination and filters.
- [x] 1.7 Create `app/services/reglas/simulator_service.py` — `simulate()`: parse Excel (Polars), run `RuleBasedDetector` + legacy detectors on first 100 rows, build diff (matched/mismatched/engine-only/legacy-only).

## Phase 2: API & Routes

- [x] 2.1 Create `app/routes/reglas_api.py` — Blueprint `reglas_api` (`url_prefix=/api/reglas`): 12 endpoints (see design) delegating to services, `@admin_requerido`, canonical `{"status","data","errors"}` envelope.
- [x] 2.2 Create `app/routes/reglas_admin.py` — Blueprint `reglas_admin`: serves React shell at `/admin/reglas` with `entry_js`/`entry_css` from Vite manifest (same pattern as `catalogo.py`).
- [x] 2.3 Modify `app/__init__.py` — register `reglas_api_bp` and `reglas_admin_bp`.

## Phase 3: React Frontend

- [x] 3.1 Create `frontend/src/lib/api-reglas.ts` — typed client with 11 methods (list, get, create, update, delete, versionar, listExceptions, createException, queryEvidence, queryAudit, simulate), reusing existing `apiGet`/`apiPost`/`apiPut`/`apiDelete` helpers.
- [x] 3.2 Create `frontend/src/pages/admin-reglas/index.html` — Vite entry (copied from `catalogo/index.html`, change title to "Admin Reglas").
- [x] 3.3 Create `frontend/src/pages/admin-reglas/main.tsx` — React root with `AppLayout` + `AdminReglasPage`.
- [x] 3.4 Create `frontend/src/pages/admin-reglas/page.tsx` — RulesListView: table with badges (estado/severidad), dominio+estado filters, search input, empty/loading/error states.
- [x] 3.5 Add RuleDetailForm to `page.tsx` — editable form + condition tree builder (selects for composite/atomic nodes, add/remove, serializes to JSON).
- [x] 3.6 Add ExceptionsPanel to `page.tsx` — table + create modal + activo toggle.
- [x] 3.7 Add VersionTimeline to `page.tsx` — newest-first list with color-coded badges + "Ver detalle" (read-only mode) + "Versionar" button.
- [x] 3.8 Add EvidenceDashboard to `page.tsx` — search filters (factura, regla_id, dominio, date range) + paginated results table with total.
- [x] 3.9 Add SimulatorView to `page.tsx` — file upload (Excel validation) + rule selector + side-by-side tables + diff summary (matched/mismatched/unique).
- [x] 3.10 Modify `frontend/vite.config.ts` — add entry: `src/pages/admin-reglas/index.html`.
- [x] 3.11 Run `npm run build` in frontend, verify manifest includes admin-reglas entry.

## Phase 4: Testing

- [x] 4.1 Create `tests/reglas/__init__.py`.
- [x] 4.2 Create `tests/reglas/test_rule_service.py` — unit tests: CRUD operations, auto-version transaction (mock DB), rollback on failure, no-op on unchanged data.
- [x] 4.3 Create `tests/reglas/test_simulator.py` — unit tests: mock `RuleBasedDetector` + legacy, assert diff fields.
- [x] 4.4 Create `tests/reglas/test_api_routes.py` — Flask test client: all 12 endpoints, canonical envelope, status codes, DB state assertions, auto-versioning integration.
- [x] 4.5 Run `python -m pytest tests/reglas/ -v`, fix failures.
