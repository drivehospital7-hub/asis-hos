# Tasks: reglas-por-tipo-factura

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | PR 1: ~150-250; PR 2: ~1200-1800 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (filters, low risk) → PR 2 (reorg, high risk) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | tipo_factura filters + code smells | PR 1 | ~150-250 lines; fits budget; independent |
| 2 | Package reorganization + registry | PR 2 | ~1200-1800 lines; EXCEEDS budget; needs split or size:exception |

## PR 1: Internal Filters (~4h, low risk)

### Phase 1: Add tipo_factura filters
- [x] 1.1 Add `tipo_factura_descripcion` filter to `app/services/urgencias/profesionales_urgencias.py`
- [x] 1.2 Add `tipo_factura_descripcion` filter to `app/services/urgencias/ide_contrato_urgencias.py`
- [x] 1.3 Add `tipo_factura_descripcion` filter to `app/services/urgencias/ide_contrato_reverse.py`
- [x] 1.4 Add `tipo_factura_descripcion` filter to `app/services/urgencias/codigos_sin_db.py`
- [x] 1.5 Add `tipo_factura_descripcion` filter to `app/services/urgencias/revision_cantidad.py`

### Phase 2: Fix code smells
- [x] 2.1 Move `detect_copago_entidad` from `urgencias/` to `transversales/`; update imports in `urgencias/detect_all.py`, `urgencias/__init__.py`, `transversales/__init__.py`
- [x] 2.2 Remove duplicate `odontologia/mal_capitado.py` (urgencias copy already exists); update import in `transversales/create_revision_sheet.py`

### Phase 2b: Add missing tipo_factura filters to unfiltered detectors
- [x] 2.3 Add `tipo_factura_descripcion` filter to `app/services/urgencias/mal_capitado.py` (was not filtering)
- [x] 2.4 Add `tipo_factura_descripcion` filter to `app/services/urgencias/duplicados_farmacia.py` (was not filtering)
- [x] 2.5 Add `tipo_factura_descripcion` filter to `app/services/urgencias/revision_entidad_86.py` (was not filtering)

### Phase 3: Verdict
- [x] 3.1 Update test imports in `test_urgencias_detect_all.py`, `test_urgencias_copago_entidad.py`, odontologia test files
- [x] 3.2 Run `pytest -v` — all existing tests pass identically
- [x] 3.3 Commit PR 1

## PR 2: Structural Reorganization (~8-14h, medium risk)

### Phase 4: Foundation (shared infrastructure)
- [x] 4.1 Create `app/services/normalized_rows.py` — parametrized `build_normalized_rows(error_groups)` replacing `urgencias/normalized_rows.py`
- [x] 4.2 Create `app/services/transversales/centro_costo_rules.py` — shared helper `apply_common_centro_costo_rules()`
- [x] 4.3 Create `app/services/tipo_factura_registry.py` — `get_detectors(tipo_factura) -> list[Callable]` per design contract
- [x] 4.4 Add `AREA_HOSPITALIZACION`, `AREA_INTRAMURAL`, `AREA_AMBULATORIA` to `app/constants/base.py`

### Phase 5: Create per-tipo packages
- [x] 5.1 Create `hospitalizacion/` package: `__init__.py`, `cantidades_hospitalizacion.py`, `hospitalizacion_codes.py`, `centro_costo_hospitalizacion.py`, `detect_all.py`
- [x] 5.2 Create `intramural/` package: `__init__.py`, `centro_costo_intramural.py`, `detect_all.py`
- [x] 5.3 Create `ambulatoria/` package: `__init__.py`, `centro_costo_ambulatoria.py`, `detect_all.py`
- [x] 5.4 `git mv cantidades_soat_hospitalizacion.py` → `hospitalizacion/`; update imports

### Phase 6: Shrink urgencias/
- [x] 6.1 Shrink `urgencias/detect_all.py` to Urgencias-only detectors; use shared `normalized_rows.py`; update imports
- [x] 6.2 Shrink `urgencias/centro_costo_urgencias.py` to Urgencias-only rules; call shared `centro_costo_rules.py`
- [x] 6.3 Delete `urgencias/normalized_rows.py`, `urgencias/hospitalizacion.py`; `urgencias/detect_copago_entidad.py` (already deleted in PR 1)
- [x] 6.4 Update `urgencias/__init__.py` — re-export from hospitalizacion/ package

### Phase 7: Wire exporter
- [x] 7.1 Update `app/services/exporter.py` — import registry; dispatch by `tipo_factura_descripcion` via registry; add `area` + `tipo_factura` to response

### Phase 8: Tests
- [x] 8.1 Run `pytest -v --tb=short > baseline.txt` before changes
- [x] 8.2 Create 4 new test files: `test_tipo_factura_registry.py`, `test_hospitalizacion_detect_all.py`, `test_intramural_detect_all.py`, `test_ambulatoria_detect_all.py`
- [x] 8.3 Update test imports for moved detectors (test_revision_sheet, test_urgencias_hospitalizacion, test_urgencias_normalized_rows, test_urgencias_cantidades_soat_hospitalizacion, create_revision_sheet)
- [x] 8.4 Run full `pytest -v`; diff against baseline — 577 passed (baseline 531), same 3 pre-existing failures
- [ ] 8.5 Commit PR 2
