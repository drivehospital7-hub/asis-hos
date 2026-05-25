# Tasks: Separar Odontología de Equipos Básicos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 400–550 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation + Blueprint → PR 2: Decoupling + Integration → PR 3: Tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation + New Blueprint + React page | PR 1 | Base = feature/tracker branch. Constants, permiso, route, React page. Runnable without decoupling — new route works alongside old for parallel access. |
| 2 | Decoupling + Integration | PR 2 | Base = PR 1 branch. Remove checkbox, clean exporter, update nav, admin UI. Old odontología route now clean. |
| 3 | Tests | PR 3 | Base = PR 2 branch. All test scenarios from specs. |

## Phase 1: Foundation

- [x] 1.1 Add `odontologia_equipos_basicos` to `ALLOWED_PERMISOS` in `app/constants/base.py`
- [x] 1.2 Create `app/constants/equipos_basicos.py` — extract EB constants from `app/constants/odontologia.py` and `app/constants/columnas.py`
- [x] 1.3 Add `from app.constants.equipos_basicos import *` to `app/constants/__init__.py`
- [x] 1.4 Remove EB blocks from `app/constants/odontologia.py` (lines 202–280)
- [x] 1.5 Remove EB constants from `app/constants/columnas.py`

## Phase 2: Core

- [x] 2.1 Create `app/routes/odontologia_equipos_basicos.py` — Blueprint with GET (React shell) + POST (upload/process) with `area=AREA_EQUIPOS_BASICOS`
- [x] 2.2 Register blueprint in `app/__init__.py` factory with `url_prefix="/odontologia-equipos-basicos"`
- [x] 2.3 Create `frontend/src/pages/odontologia-equipos-basicos/page.tsx`, `main.tsx`, `index.html` — adapted from odontología page

## Phase 3: Decoupling + Integration

- [x] 3.1 Remove `equipos_basicos: bool` param from `detect_problems_only()` in `app/services/exporter.py`; callers pass `area=AREA_EQUIPOS_BASICOS`
- [x] 3.2 Remove `area_effective` and `or equipos_basicos` guard from `_do_detect_problems()` in `exporter.py`
- [x] 3.3 Remove `equipos_basicos = request.form.get(...)` from `app/routes/excel_headers.py` (~line 84)
- [x] 3.4 Remove checkbox EB (lines 89–95) + `actualizarReglasModal()` JS (lines 774–858) from `app/templates/excel_headers.html`
- [x] 3.5 Update `app/templates/base.html` — add EB endpoint to nav_items dict and endpoint_map
- [x] 3.6 Update `app/templates/home.html` — add EB card with `odontologia_equipos_basicos` permiso
- [x] 3.7 Update `frontend/src/components/app-sidebar.tsx` — add EB nav item with new permiso
- [x] 3.8 Update `app/templates/usuarios.html` — add checkbox `odontologia_equipos_basicos`; relabel `equipos_basicos` to "Ordenado y Facturado"
- [x] 3.9 Update `frontend/src/pages/usuarios/page.tsx` — add `odontologia_equipos_basicos` to `ALL_PERMISOS` with label "Equipos Básicos"

## Phase 4: Testing

Test-first per config.yaml (`testing.strict_tdd: true`). Write failing test first, then implement.

- [x] 4.1 Test: GET route returns 200 with permiso, 403 without, 401 unauthenticated (spec R1) — done in test_odontologia_equipos_basicos.py::TestGetRoute
- [x] 4.2 Test: POST processes EB Excel → calls `detect_problems_only(area=AREA_EQUIPOS_BASICOS)` (spec R2)
- [x] 4.3 Test: POST rejects missing file / invalid extension (spec R2) — done in TestPostRejectsInvalidInput
- [x] 4.4 Test: `exporter.py` raises `TypeError` if called with `equipos_basicos` kwarg (spec R3) — done in TestExporterRejectsEquiposBasicosKwarg
- [x] 4.5 Test: Constants importable: `from app.constants import PROFESIONALES_EQUIPOS_BASICOS` (spec R4) — done in TestConstantsImportable
- [x] 4.6 Test: Full roundtrip with real EB Excel → assert status + problem list (spec R3) — done in TestFullRoundtrip
- [x] 4.7 Test: Permission isolation — EB user blocked from `/odontologia/`, odontología user blocked from EB route (spec R5) — done in TestPermissionIsolation
- [x] 4.8 Run `pytest` — all existing tests pass without regression
