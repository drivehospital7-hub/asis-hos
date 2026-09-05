# Tasks: CUPS Equivalentes — Intramural

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 200–270 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | New detector + constants + wiring + tests | Single PR | All additive, no existing behavior modified |

## Phase 1: Foundation / Constants

- [x] 1.1 Add `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL` dict to `app/constants/intramural.py` — `{"906317": "1906317", "906249": "906249PR"}`

## Phase 2: Core Implementation

- [x] 2.1 Create `app/services/intramural/cups_equivalentes.py` with function `detect_cups_equivalentes_intramural(data_sheet, indices) -> list[dict]` — iterate rows, lookup `codigo` against constant dict, emit `{factura, codigo, codigo_equiv, accion, procedimiento}`
- [x] 2.2 Import and register `detect_cups_equivalentes_intramural` in `_get_intramural_detectors()` inside `detect_all.py`
- [x] 2.3 Add call block (step 10, renumber old 10→11, 11→12) in `detect_all_problems_intramural()` and populate `resultado["problemas"]["cups_equivalentes"]` + `resultado["totales"]["cups_equivalentes"]`

## Phase 3: Testing

- [x] 3.1 Create `tests/services/intramural/test_cups_equivalentes_intramural.py` — unit tests: constant dict values, both codes detected, non-matching codes skipped, missing columns → `[]`, empty/non-string cells skipped
- [x] 3.2 Add integration test in `tests/services/test_intramural_detect_all.py` — verify `problemas["cups_equivalentes"]` populated after wiring (use existing helper patterns)
