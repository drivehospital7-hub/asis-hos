# Design: Admin UI para Motor de Reglas

## Technical Approach

API-first: Flask Blueprint (`/api/reglas`) delegates CRUD + versioning + simulation to SRP services in `app/services/reglas/`. React SPA in `frontend/src/pages/admin-reglas/` follows the exact `catalogo/` pattern (Vite multi-page, `react_shell.html`, `__INITIAL_DATA__`, shadcn/ui). Auto-versioning on PUT uses a **single DB transaction** (deprecate old + create new). Simulator runs the DB engine and legacy detectors side-by-side on ≤100 Excel rows and returns a diff.

## Architecture Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| **Blueprint prefix** | `/api/reglas` vs shared `/api` | **`/api/reglas`** (separate file `reglas_api.py`) | SRP separation from existing `notas_api.py`; evidence & audit endpoints share prefix to simplify route nesting |
| **Auto-versioning grouping** | `rule_base_id` vs `nombre`+drop unique | **Add `rule_base_id` to Regla model** | Spec R6 uses `rule_base_id`; avoids breaking existing `nombre` unique constraint; migration aligns with F1 schema |
| **Simulator engine invocation** | Direct `RuleEvaluationEngine` vs `RuleBasedDetector` | **`RuleBasedDetector`** | Legacy-compatible wrapper already exists in `app/services/engine/`; detect_all.py already uses this pattern |
| **React vs server-rendered** | Flask templates vs React SPA | **React SPA** | Spec requires `catalogo/` pattern which is React; tree builder needs interactive JS |
| **Client-side state** | React context vs inline per-component | **Per-component `useState`** | Follows existing `page.tsx` pattern; no global state needed for F2 scope |

## Data Flow

```
Browser                          Flask                          PostgreSQL
  │                                │                                │
  ├─ GET /admin/reglas             │                                │
  │  → react_shell.html            │                                │
  │  ← manifest.json(entry_js)     │                                │
  │                                │                                │
  ├─ PUT /api/reglas/1             │                                │
  │  → rule_service.update()       │                                │
  │                                ├─ BEGIN TX                     │
  │                                ├─ UPDATE reglas SET estado=     │
  │                                │   'deprecated' WHERE id=1     │
  │                                ├─ INSERT reglas (...) VALUES    │
  │                                │   (...version=old+1...)       │
  │                                ├─ INSERT condiciones (...)     │
  │                                │   (clone with new regla_id)   │
  │                                ├─ COMMIT (or ROLLBACK)         │
  │  ← {old_rule_id, new_rule_id,  │                                │
  │     old_version, new_version}  │                                │
  │                                │                                │
  ├─ POST /api/reglas/simular      │                                │
  │  → simulator_service.simulate()│                                │
  │  ├─ RuleBasedDetector.detect() ├─ RuleEvaluationEngine          │
  │  ├─ legacy detectors (inline)  │                                │
  │  └─ diff(matched, mismatched)  │                                │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/reglas_api.py` | Create | Blueprint `reglas_api`, url_prefix=`/api/reglas` — 12 REST endpoints |
| `app/routes/reglas_admin.py` | Create | Blueprint `reglas_admin` — serves React shell at `/admin/reglas` |
| `app/services/reglas/__init__.py` | Create | Package init |
| `app/services/reglas/rule_service.py` | Create | CRUD + auto-versioning + clone-as-draft |
| `app/services/reglas/exception_service.py` | Create | CRUD for exceptions linked to a rule |
| `app/services/reglas/evidence_service.py` | Create | Wraps `EvidenceRepository` with pagination + canonical envelope |
| `app/services/reglas/audit_service.py` | Create | Queries `ResultadoAuditoria` with pagination |
| `app/services/reglas/simulator_service.py` | Create | Dry-run: `RuleBasedDetector` + legacy detectors + diff |
| `frontend/src/pages/admin-reglas/index.html` | Create | Vite entry HTML (copy from `catalogo/index.html`, change title) |
| `frontend/src/pages/admin-reglas/main.tsx` | Create | React root with `AppLayout` + `AdminReglasPage` |
| `frontend/src/pages/admin-reglas/page.tsx` | Create | Main component: 6 sub-views (list, form, tree, exceptions, versions, evidence, simulator) |
| `frontend/src/lib/api-reglas.ts` | Create | Typed fetch client reusing `apiGet`/`apiPost`/`apiPut`/`apiDelete` helpers |
| `frontend/vite.config.ts` | Modify | Add entry: `src/pages/admin-reglas/index.html` |
| `app/__init__.py` | Modify | Register `reglas_api_bp`, `reglas_admin_bp` |
| `app/models.py` | Modify | Add `rule_base_id` (Integer) column to `Regla` for version grouping |
| `tests/reglas/` | Create | Package with test modules for all 5 services |

## Interfaces / Contracts

### API Endpoint Summary

| Method | URL | Delegates to | Notes |
|--------|-----|-------------|-------|
| GET | `/api/reglas` | `rule_service.list_rules()` | Filters: `?dominio=` `?estado=` `?activo=` |
| GET | `/api/reglas/<id>` | `rule_service.get_rule()` | Returns nested condition tree + exceptions |
| POST | `/api/reglas` | `rule_service.create_rule()` | Creates as draft, version=1 |
| PUT | `/api/reglas/<id>` | `rule_service.update_rule()` | Auto-versioning: deprecated old + create new |
| DELETE | `/api/reglas/<id>` | `rule_service.soft_delete()` | Sets estado=retired |
| GET | `/api/reglas/<id>/versiones` | `rule_service.list_versions()` | Ordered by version DESC |
| POST | `/api/reglas/<id>/versionar` | `rule_service.clone_as_draft()` | Original stays active |
| GET | `/api/reglas/<id>/excepciones` | `exception_service.list()` | |
| POST | `/api/reglas/<id>/excepciones` | `exception_service.create()` | |
| GET | `/api/evidencias` | `evidence_service.query()` | Paginated, filters via query params |
| GET | `/api/auditoria` | `audit_service.query()` | Paginated, filters via query params |
| POST | `/api/reglas/simular` | `simulator_service.simulate()` | Multipart: Excel + optional `rule_id` |

### Auto-Versioning Contract

```python
# rule_service.py
def update_rule(db: Session, regla_id: int, data: dict) -> dict:
    rule = db.query(Regla).filter(Regla.id == regla_id).first()
    if rule.estado != "active":
        raise ValueError("Cannot modify non-active rule")
    if _no_changes(rule, data):
        return {"old_rule_id": regla_id, "new_rule_id": regla_id,
                "old_version": rule.version, "new_version": rule.version}
    try:
        # 1. Deprecate current
        old_rule_id = rule.id
        old_version = rule.version
        rule.estado = "deprecated"
        db.flush()
        # 2. Clone as new version
        new_rule = Regla(rule_base_id=rule.rule_base_id, nombre=rule.nombre,
                         version=rule.version + 1, estado="active", ...)
        # Apply partial updates
        for k, v in data.items():
            setattr(new_rule, k, v)
        db.add(new_rule)
        db.flush()
        # 3. Clone conditions
        for cond in db.query(Condicion).filter(Condicion.regla_id == old_rule_id):
            new_cond = Condicion(regla_id=new_rule.id, ...)
            db.add(new_cond)
        db.commit()
        return {"old_rule_id": old_rule_id, "new_rule_id": new_rule.id,
                "old_version": old_version, "new_version": new_rule.version}
    except:
        db.rollback()
        raise
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `rule_service.update_rule()` | Mock DB session; assert deprecate + create called; assert rollback on failure |
| Unit | `simulator_service.simulate()` | Mock `RuleBasedDetector` + legacy detector; assert diff correctness |
| Unit | `evidence_service.query()` | Mock `EvidenceRepository`; assert pagination params passed through |
| Integration | All 12 endpoints | Flask test client with test DB; assert canonical envelope, status codes, DB state after mutations |
| Integration | Auto-versioning | Start with active rule v3, PUT changes → assert v3 deprecated, v4 active, conditions cloned |

Test modules: `tests/reglas/test_rule_service.py`, `tests/reglas/test_simulator.py`, `tests/reglas/test_api_routes.py`.

## Migration / Rollout

- **DB**: Add `rule_base_id` column to `reglas` (nullable, backfilled with `id` for existing rules).
- **Rollback**: Unregister blueprints in `app/__init__.py`, revert `vite.config.ts`, delete service files. Existing rules in DB remain untouched — engine continues working.

## Open Questions

- [ ] Does existing `nombre` unique constraint need to be dropped for auto-versioning (if not using `rule_base_id`)? Decision: add `rule_base_id` column — migration required.
- [ ] Confirm exact format of legacy detector return values for the simulator diff (comparing with `RuleBasedDetector.detect()` output).
