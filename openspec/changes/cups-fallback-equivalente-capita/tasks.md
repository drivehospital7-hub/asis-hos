# Tasks: CUPS Fallback — Cód. Equivalente CUPS en Cápita

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~70-90 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Core Implementation

- [x] 1.1 Insert fallback guard clause in `detect_capita_cups_invalidos()` (`app/services/urgencias/valida_capita.py`) — after line 81 (`continue`) and before line 83 (`procedimiento = ""`), add logic to read `codigo_equiv` from `indices`, normalize via `.strip().upper()`, and `continue` if the equivalent is in `URGENCIAS_CAPITA_CUPS_CODES`

## Phase 2: Testing

- [x] 2.1 Create `tests/services/test_urgencias_capita.py` — Unit tests for `detect_capita_cups_invalidos()` with scenarios:
  - CUPS no listado + Cód. Equivalente CUPS válido → 0 errores
  - CUPS no listado + Cód. Equivalente CUPS vacío → 1 error
  - CUPS no listado + Cód. Equivalente CUPS no listado → 1 error
  - CUPS no listado + columna `codigo_equiv` ausente → 1 error
  - CUPS directamente en listado → 0 errores (regresión)
  - Tipo Procedimiento 09 excluido → 0 errores (regresión)
  - Normalización con espacios → 0 errores
  - CUPS no listado + código equiv vacío (string vacío) → 1 error

## Phase 3: Verification

- [x] 3.1 Run `python -m pytest tests/services/test_urgencias_capita.py -v` — new tests pass (8/8)
- [x] 3.2 Run `python -m pytest` — full suite confirms no regressions (533 passed, pre-existing failures unchanged)
