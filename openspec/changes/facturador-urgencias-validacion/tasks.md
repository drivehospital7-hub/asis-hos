# Tasks: Facturador Urgencias — Validación contra Nota 27 para entidades no listadas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~180 (1 production + ~4 comment + ~175 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: single-pr
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Fix + tests | PR 1 | Single PR, well under 400 lines |

## Phase 1: Tests — RED (write failing tests)

- [x] 1.1 Add test `test_urgencias_facturador_entity_en_lista_cups_in_nota` — EPSS08 (en `_ENTIDADES_NOTA_URGENCIAS`) + urgencias biller + CUPS 965201 in nota_urgencias → sin error (regression guard)
- [x] 1.2 Add test `test_urgencias_facturador_entity_en_lista_cups_not_in_nota` — EPSS08 + urgencias biller + CUPS 999999 (ni nota_urgencias ni pares_validos) → error
- [x] 1.3 Add test `test_urgencias_entity_no_lista_cups_in_pares_validos` — ESS118 + urgencias biller + CUPS 878001 (in pares_validos) → no error (pares_validos fallback)
- [x] 1.4 Add test `test_urgencias_bug_scenario` — ESS118 + CUPS 903437 + MEZA FERNANDEZ CARLOS OMAR → no error (the original bug)
- [x] 1.5 Add test `test_non_urgencias_biller_unaffected` — ESS118 + CUPS 965201 + non-urgencias name → error (normal validation unchanged)
- [x] 1.6 Run tests to confirm new tests fail and existing ESS118 tests (14.x) fail — **RED confirmed: 4 failures (3 existing + 1 new)**

## Phase 2: Implementation — GREEN (make tests pass)

- [x] 2.1 Update comment (lines 207-210) to remove `_ENTIDADES_NOTA_URGENCIAS` restriction — state that ALL urgencias billers check `nota_urgencias_cups` first
- [x] 2.2 Remove `and cod_entidad in _ENTIDADES_NOTA_URGENCIAS` from line 215 — `resp_name in _FACTURADORES_URGENCIAS_NORM` is the sole gate

## Phase 3: Verification — REFACTOR

- [x] 3.1 Run `python -m pytest -v tests/services/test_detect_cups_sin_contrato.py` — **40/40 passed** (existing 14.x + new)
- [x] 3.2 Verify no regression: full suite — **896/901 passed** (5 pre-existing unrelated failures)
- [x] 3.3 Clean up any test imports or unused helpers if added — **No unused imports found, test file is clean**
