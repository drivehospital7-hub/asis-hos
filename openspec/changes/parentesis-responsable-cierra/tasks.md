# Tasks: Excepción responsable-urgencias en CUPS sin contrato

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 95–115 (15 source + ~80–100 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Tests (RED) + Implementation (GREEN) + Verify | PR 1 | Single PR, ~95–115 lines, no split needed |

## Phase 1: Tests — RED (TDD: write failing tests first)

- [x] 1.1 Update `_make_mock_session` in `tests/services/test_detect_cups_sin_contrato.py` to support optional `nota1_cups` param (backward-compatible, default `None` → third `.all()` returns empty list)
- [x] 1.2 Add test: urgencias facturador + CUPS in `nota1_cups` → no error (Scenario 3 from spec)
- [x] 1.3 Add test: urgencias facturador + CUPS not in `nota1_cups` → error (Scenario 4)
- [x] 1.4 Add test: urgencias facturador + `codigo_equiv` in `nota1_cups` → no error
- [x] 1.5 Add test: urgencias facturador + `nota1_cups` empty set → error (fails closed)
- [x] 1.6 Add test: columna `responsable_cierra` ausente (`None` in indices) → normal validation
- [x] 1.7 Add test: `responsable_cierra` celda vacía → normal validation

## Phase 2: Implementation — GREEN (make tests pass)

- [x] 2.1 Add `from app.constants.urgencias import FACTURADORES_URGENCIAS` and module-level `_FACTURADORES_URGENCIAS_NORM: frozenset[str]` in `app/services/transversales/procedimiento_contratado.py`
- [x] 2.2 Add nota1 pre-load query inside existing `try` block (after `pares_validos` + `entidades_con_datos` construction): query `Procedimiento` → `NotasTecnicas` filtered by `id_nota_hoja == 1`, build `nota1_cups: set[str]`
- [x] 2.3 Add row-loop branch after `codigo_equiv` check (line 198) and before `entidades_con_datos` skip (line 201): read `responsable_cierra`, if normalized value in `_FACTURADORES_URGENCIAS_NORM`, validate `codigo` (then `codigo_equiv`) against `nota1_cups` — skip row if found, fall through to normal validation otherwise

## Phase 3: Verification

- [x] 3.1 Run `python -m pytest -v tests/services/test_detect_cups_sin_contrato.py` — all 28 tests pass (22 existing + 6 new)
