# Tasks: Duplicados Farmacia para tipo factura Farmacia (sin tarifario ni tipo procedimiento)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~200-250 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Implement base + refactor + new detector + tests | Single PR | All changes are tightly coupled; splitting would add overhead without benefit |

## Phase 1: Base Function (Foundation)

- [x] 1.1 Create `app/services/transversales/detect_duplicados_base.py` with `detect_duplicados_generico(data_sheet, indices, *, tipo_factura, tarifario_val=None, codigos_tipo_proc=None)` — extract algorithm from `duplicados_farmacia.py`
- [x] 1.2 Base handles two output modes: with `codigos_tipo_proc` → includes `codigo_tipo_procedimiento` in output + groups by `(factura, tipo_proc)`; without → omits it from output + groups by `(factura,)`

## Phase 2: Refactor Urgencias Detector

- [x] 2.1 Rewrite `app/services/urgencias/duplicados_farmacia.py` → `detect_duplicados_farmacia()` delegates to `detect_duplicados_generico(..., tipo_factura="Urgencias", tarifario_val=VALOR_TARIFARIO_FARMACIA, codigos_tipo_proc=CODIGOS_TIPO_PROC_09_12)`
- [x] 2.2 Remove hardcoded algorithm, keep only the thin wrapper + docstring + logger

## Phase 3: New Farmacia Detector + Registration

- [x] 3.1 Create `app/services/farmacia/duplicados_farmacia_farmacia.py` with `detect_duplicados_farmacia_farmacia(data_sheet, indices)` → calls `detect_duplicados_generico(..., tipo_factura="Farmacia")` (no tarifario, no codigos_tipo_proc)
- [x] 3.2 Add `duplicados_farmacia_farmacia` to `_get_farmacia_detectors()` in `app/services/farmacia/detect_all.py`
- [x] 3.3 Add error group `"Duplicados Farmacia"` to `error_groups` dict and `"duplicados_farmacia"` to `resultado["problemas"]` and `totales` in `detect_all_problems_farmacia()`

## Phase 4: Normalized Rows Handler

- [x] 4.1 Update `app/services/normalized_rows.py` "Duplicados Farmacia" handler (line ~310): when `codigo_tipo_procedimiento` is missing/empty, omit "Grupo " from description and set procedimiento to empty string

## Phase 5: Testing

- [x] 5.1 Update `tests/services/test_duplicados_farmacia.py` — all existing tests pass with refactored Urgencias detector (no import changes needed — same module path)
- [x] 5.2 Create `tests/services/test_duplicados_farmacia_farmacia.py` covering: duplicidad total, mezcla, sin duplicados, múltiples facturas independientes, missing columns, sin filas Farmacia, output no incluye `codigo_tipo_procedimiento`
- [x] 5.3 Add test for `normalized_rows.py`: "Duplicados Farmacia" handler renders correctly without `codigo_tipo_procedimiento` — no "Grupo " in description
