# Apply Progress — Phase 1 + Phase 2

**Change**: reorganizacion-modulos
**Mode**: Strict TDD
**Batch**: Phase 1 (T-01 + T-02) + Phase 2 (T-04, T-05, T-06, T-07)
**Status**: ✅ Phase 1 ✅ Phase 2

---

## Phase 1: constants/ package

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| T-01 | `tests/services/test_constants_package.py` | Unit | ✅ 83/90 baseline | ✅ 6 failed (file not found) | ✅ 41/41 passed | ➖ Single (purely structural) | ✅ No changes needed |
| T-02 | `tests/services/test_constants_package.py` | Unit | ✅ 83/90 baseline | ✅ Same 6 (created same batch) | ✅ 41/41 passed | ➖ Single (purely structural) | ✅ No changes needed |

### Test Summary
- **Total tests written**: 41
- **Total tests passing**: 41
- **Layers used**: Unit (41)
- **Approval tests** (refactoring): 41
- **Pure functions created**: 0 (constants only)
- **Triangulation skipped**: Structural refactor — 1:1 constant extraction, no branching logic

### Completed Tasks

- [x] **T-01** — Created `app/constants/` package structure
- [x] **T-02** — Created domain modules with all constants migrated

### Files Created

| File | Action | Lines | What It Contains |
|------|--------|-------|------------------|
| `app/constants/__init__.py` | Created | 12 | Re-exports from all 5 domain modules |
| `app/constants/base.py` | Created | 58 | General purpose: sheets, suffixes, areas, thresholds, images |
| `app/constants/columnas.py` | Created | 73 | Column definitions, headers, centros de costo |
| `app/constants/colores.py` | Created | 32 | Color constants for conditional formatting |
| `app/constants/odontologia.py` | Created | 232 | CUPS PyP, profesionales (odonto + EB), IDE PyP, mal capitado |
| `app/constants/urgencias.py` | Created | 495 | IDE Contrato rules, SOAT, hospitalización, CAPITA, reverse rules |
| `tests/services/test_constants_package.py` | Created | 265 | Approval tests for all domain modules |

### Deviations from Design

1. **No `equipos_basicos.py`**: The original tasks.md suggested a separate module, but the user's instructions didn't include it. EB constants were merged into `odontologia.py` (professionals, thresholds) and `columnas.py` (headers/columns to maintain `is COLUMNS_TO_KEEP` object identity).

2. **Python resolves package, not file**: In Python 3.14, `app/constants/__init__.py` takes precedence over `app/constants.py` even though the file still exists. This means the re-exports are ALREADY active, not just for Phase 7.

3. **`EQUIPOS_BASICOS_COLUMNS_TO_KEEP` and `EQUIPOS_BASICOS_REVISION_HEADERS`** placed in `columnas.py` (not `odontologia.py`) to maintain object identity with `COLUMNS_TO_KEEP` without requiring cross-module imports (impossible while `constants.py` shadows the package).

### Verification
- ✅ `pytest tests/` — 124 pass, 7 fail (all pre-existing, same baseline)
- ✅ `pytest tests/services/test_constants_package.py` — 41/41 pass
- ✅ `python run_dev.py` — starts without errors
- ✅ `from app.constants import ALL_200+_CONSTANTS` — all importable
- ✅ `python -c "from app.constants import *"` — no errors
- ✅ `app/constants.py` still exists (not deleted — Phase 7)

---

## Phase 2: transversales/ nuevos

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| T-04 | `tests/services/test_column_indices.py` | Unit | ✅ 149/156 baseline | ✅ Written first (7 tests) | ✅ 7/7 passed | ✅ 6 cases (exact match, missing, urgencias, partial, empty, None) | ➖ None needed |
| T-05 | `tests/services/test_doble_tipo_procedimiento.py` | Unit | ✅ 149/156 baseline | ✅ Written first (5 tests) | ✅ 5/5 passed | ✅ 4 cases (multi-type, single-type, missing indices, None cells, 3+ types) | ➖ None needed |
| T-06 | `tests/services/test_ruta_duplicada.py` | Unit | ✅ 149/156 baseline | ✅ Written first (6 tests) | ✅ 6/6 passed | ✅ 5 cases (threshold=3, threshold=2, non-PyP, missing indices, default threshold, cantidad field) | ➖ None needed |
| T-07 | `tests/services/test_cantidades_anomalas.py` | Unit | ✅ 149/156 baseline | ✅ Written first (7 tests) | ✅ 7/7 passed | ✅ 6 cases (consultas, max general, PyP, custom params, missing indices, dedup, non-numeric) | ➖ None needed |

### Test Summary
- **Total tests written**: 25
- **Total tests passing**: 25
- **Layers used**: Unit (25)
- **Approval tests** (refactoring): 25 (behavior preserved from original inline functions)
- **Pure functions created**: 4 (`get_column_indices`, `detect_doble_tipo_procedimiento`, `detect_ruta_duplicada`, `detect_cantidades_anomalas`)
- **Triangulation skipped**: None — all tasks have multiple test cases

### Completed Tasks

- [x] **T-04** — Create `transversales/column_indices.py`
  - Extrajo `_get_column_indices` de `revision_sheet.py` a su propio módulo
  - Función parametrizada con `required_headers: dict[str, str]` — soporta cualquier área
  - `revision_sheet.py` delega: la original llama a `get_column_indices(headers, required_headers)`
  - 7 tests: mapeo exacto, faltantes, urgencias, parcial, vacío, None en headers

- [x] **T-05** — Create `transversales/doble_tipo_procedimiento.py`
  - Extrajo `_detect_doble_tipo_procedimiento` a módulo independiente
  - Función autónoma sin dependencia de área, usa `normalize_invoice` de transversales
  - 5 tests: multi-tipo, single-tipo, sin índices, valores None, 3+ tipos

- [x] **T-06** — Create `transversales/ruta_duplicada.py` (parametrizado)
  - Unificó `_detect_ruta_duplicada` y `_detect_ruta_duplicada_equipos_basicos`
  - Parámetro `threshold: int = 3` — odontología usa 3, equipos básicos usa 1
  - 6 tests: threshold=3, threshold=2, no-PyP, sin índices, default threshold, campo cantidad

- [x] **T-07** — Create `transversales/cantidades_anomalas.py` (parametrizado)
  - Unificó `_detect_cantidades_anomalas` y `_detect_cantidades_anomalas_equipos_basicos`
  - Parámetros: `cantidad_consultas_min`, `cantidad_max_general`, `cantidad_pyp_min`
  - Equipos básicos mantiene chequeo de columna `procedimiento` en el wrapper en `revision_sheet.py`
  - 7 tests: consultas, max general, PyP, params personalizados, sin índices, sin duplicados, no-numérico

### Files Created

| File | Action | Lines | What It Contains |
|------|--------|-------|------------------|
| `app/services/transversales/column_indices.py` | Created | 72 | `get_column_indices()` — mapea headers a índices, parametrizado |
| `app/services/transversales/doble_tipo_procedimiento.py` | Created | 60 | `detect_doble_tipo_procedimiento()` — detecta facturas con >1 tipo |
| `app/services/transversales/ruta_duplicada.py` | Created | 71 | `detect_ruta_duplicada()` — unifica threshold odonto/EB |
| `app/services/transversales/cantidades_anomalas.py` | Created | 91 | `detect_cantidades_anomalas()` — unifica reglas odonto/EB |
| `tests/services/test_column_indices.py` | Created | 132 | 7 tests para column_indices |
| `tests/services/test_doble_tipo_procedimiento.py` | Created | 124 | 5 tests para doble_tipo_procedimiento |
| `tests/services/test_ruta_duplicada.py` | Created | 172 | 6 tests para ruta_duplicada |
| `tests/services/test_cantidades_anomalas.py` | Created | 206 | 7 tests para cantidades_anomalas |

### Files Modified

| File | Action | What Changed |
|------|--------|-------------|
| `app/services/transversales/__init__.py` | Modified | Added re-exports for `get_column_indices`, `detect_doble_tipo_procedimiento`, `detect_ruta_duplicada`, `detect_cantidades_anomalas` |
| `app/services/revision_sheet.py` | Modified | Added imports from transversales modules; original functions delegate to new modules (will be removed in Phase 7) |

### Deviations from Design

1. **File naming**: `doble_tipo_procedimiento.py` (not `doble_tipo.py` as in original tasks.md) — keeps name aligned with function and original `_detect_doble_tipo_procedimiento`.

2. **Normalization dependency**: `doble_tipo_procedimiento.py` and `cantidades_anomalas.py` import `normalize_invoice` from `app.services.transversales.normalize` instead of using the inline `_normalize_invoice` from `revision_sheet.py` — this is correct because the transversales normalize module is the shared utility.

3. **Equipos Básicos wrapper**: The `_detect_cantidades_anomalas_equipos_basicos` wrapper in `revision_sheet.py` still checks `indices.get("procedimiento")` before delegating — this logic was NOT moved into the shared function because it's specific to EB calling context, not part of the detection logic itself.

### Verification
- ✅ `pytest tests/services/test_column_indices.py` — 7/7 pass
- ✅ `pytest tests/services/test_doble_tipo_procedimiento.py` — 5/5 pass
- ✅ `pytest tests/services/test_ruta_duplicada.py` — 6/6 pass
- ✅ `pytest tests/services/test_cantidades_anomalas.py` — 7/7 pass
- ✅ `pytest tests/` — 149 pass, 7 fail (all pre-existing, same baseline)
- ✅ `python run_dev.py` — app starts without errors
- ✅ `python -c "from app.services.revision_sheet import _get_column_indices"` — import works
- ✅ `revision_sheet.py` original functions still exist (not deleted — Phase 7)
- ✅ Original `.py` file still exists (will be deleted in Phase 7)

---

## Cumulative State

### Tasks Status (all phases)
| Task | Status |
|------|--------|
| T-01 — constants/ package structure | ✅ Complete |
| T-02 — domain modules | ✅ Complete |
| T-03 — delete constants.py | 🔲 Phase 7 |
| T-04 — column_indices.py | ✅ Complete |
| T-05 — doble_tipo_procedimiento.py | ✅ Complete |
| T-06 — ruta_duplicada.py (parametrizado) | ✅ Complete |
| T-07 — cantidades_anomalas.py (parametrizado) | ✅ Complete |
| T-08 — Merge decimales formats | 🔲 Phase 3 |
| T-09 — Adopt tipo_documento_edad | 🔲 Phase 3 |
| T-10 — odontologia/ modules | 🔲 Phase 4 |
| T-11 — odontologia/detect_all.py | 🔲 Phase 4 |
| T-12 — urgencias/ low-risk modules | 🔲 Phase 5 |
| T-13 — urgencias/ high-risk modules | 🔲 Phase 5 |
| T-14 — urgencias/detect_all.py | 🔲 Phase 5 |
| T-15 — equipos_basicos/ | 🔲 Phase 6 |
| T-16 — Cleanup (delete constants.py + revision_sheet.py) | 🔲 Phase 7 |

### Pre-existing Failures (unrelated to this change)
- `test_cruce_sheet.py::TestCreateCruceFacturasSheet::test_integra_get_or_create_y_apply_headers`
- `test_exporter.py::TestExportExcelWithCruceFacturas::test_crea_hoja_revision`
- `test_revision_sheet.py::TestBuildUrgenciasNormalizedRows::test_centros_de_costo`
- `test_revision_sheet.py::TestBuildUrgenciasNormalizedRows::test_ide_contrato`
- `test_revision_sheet.py::TestBuildUrgenciasNormalizedRows::test_cantidades_urgencias`
- `test_column_filter.py::TestHideNonRelevantColumns::test_usa_columns_to_keep_por_defecto`
- `test_formatting.py::TestApplyConditionalTipoIdentificacion::test_aplica_regla_cuando_columnas_existen`
