# Tasks: Deduplicación errores de contrato por factura

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~72 (12 logic + ~60 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full change (dedup + tests + verify) | PR 1 | Main branch; single atomic change |

## Phase 1: Urgencias — Add invoice dedup

- [x] 1.1 `app/services/urgencias/ide_contrato_urgencias.py`: add `facturas_procesadas: set[str] = set()` after line 90 (`problemas_ide_contrato = []`)
- [x] 1.2 Add early-skip check after line 97 (`if not factura_str: continue`): `if factura_str in facturas_procesadas: continue`
- [x] 1.3 Add `facturas_procesadas.add(factura_str)` at end of loop body (before `if problemas_ide_contrato:`)

## Phase 2: Odontología — Add invoice dedup

- [x] 2.1 `app/services/odontologia/ide_contrato.py`: add `facturas_procesadas: set[str] = set()` after line 181 (`problemas = []`)
- [x] 2.2 Add early-skip check after line 187 (`if not factura_str: continue`): `if factura_str in facturas_procesadas: continue`
- [x] 2.3 Add `facturas_procesadas.add(factura_str)` inside the `if ide_str not in ide_esperado_set:` block, after the append (line 226)

## Phase 3: Tests — Cover spec scenarios

- [x] 3.1 Unit test (urgencias): same invoice 3 rows → 1 contract error. Assert `len(result) == 1`
- [x] 3.2 Unit test (odontología): same invoice 3 rows → 1 contract error. Assert `len(result) == 1`
- [x] 3.3 Unit test (urgencias): 2 different invoices → 2 contract errors. Assert `len(result) == 2`
- [x] 3.4 Unit test (odontología): no violations → 0 errors (regression). Assert `len(result) == 0`
- [x] 3.5 Integration test extension: additional edge case tests (empty invoice R3, mixed invoice contamination triangulation)

## Phase 4: Verification — Existing tests pass

- [x] 4.1 Run targeted tests: `python -m pytest -v tests/services/test_odontologia_ide_contrato.py tests/services/test_urgencias_normalized_rows.py tests/services/test_odontologia_normalized_rows.py` → All pass
- [x] 4.2 Run full suite: `python -m pytest -v` → 553/553 pass (12 pre-existing failures unrelated to change)
