# Apply Progress — Deduplicación errores de contrato por factura

**Mode**: Strict TDD
**Date**: 2026-06-22
**Batch**: 1 (full change — all phases)

## Summary

Added invoice-level dedup to 2 contract-validation detectors using the established `set[str]` pattern. 10 dedup-specific tests written, all passing. All existing non-related tests pass (553/553 excluding 12 pre-existing failures).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1-1.3 (Urgencias) | `tests/services/test_urgencias_ide_contrato.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ 2 cases | ➖ None needed |
| 2.1-2.3 (Odontología) | `tests/services/test_odontologia_ide_contrato.py` | Unit | ✅ 6/6 | ✅ Written | ✅ Passed | ✅ 2 cases | ➖ None needed |
| 3.1-3.5 (Tests) | Both files | Unit | ✅ 6/6 | ✅ Written | ✅ Passed | ✅ 5 cases total | ➖ None needed |
| 4.1 (Targeted) | N/A (regression) | Regression | ✅ 6/6 | N/A | ✅ 20/20 pass | N/A | N/A |
| 4.2 (Full suite) | N/A (regression) | Regression | ✅ 6/6 | N/A | ✅ 553/553 pass (12 pre-existing failures unrelated) | N/A | N/A |

## Test Summary

- **Total tests written (new)**: 10
- **Total tests passing (new)**: 10
- **Total tests passing (regression)**: 553/553 (excluding 12 pre-existing failures)
- **Layers used**: Unit (10)
- **Approval tests**: 0 (no refactoring needed)
- **Pure functions**: 0 (maintained function signatures)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `app/services/urgencias/ide_contrato_urgencias.py` | Modified | Added `facturas_procesadas: set[str]` before loop, early skip check, and `add()` at end of loop body |
| `app/services/odontologia/ide_contrato.py` | Modified | Added `facturas_procesadas: set[str]` before loop, early skip check, and `add()` after append |
| `tests/services/test_urgencias_ide_contrato.py` | Created | 9 tests: 4 basic + 5 dedup (same invoice, multi invoice, no errors, mix contamination, empty invoice) |
| `tests/services/test_odontologia_ide_contrato.py` | Modified | Added 5 dedup tests to existing test file (same invoice, multi invoice, no errors, mix contamination, empty invoice) |

## Deviations from Design

**None** — implementation matches design exactly.

## Issues Found

1. **Urgencias "end of loop" vs "per append" tradeoff**: The design uses unconditional `facturas_procesadas.add(factura_str)` at end of loop body. If a row of an invoice doesn't trigger any rule (unrecognized code/entity), the invoice is still added to the set, causing subsequent rows of the same invoice to be skipped even if they WOULD trigger a rule. This is an accepted design trade-off (proposal risk states "first-error bias"). The odontología detector avoids this by adding inside the `if` block (only when error emitted). This difference is noted but not changed per design spec.
2. **Pre-existing test failures**: 12 failures across 3 test files are pre-existing and unrelated to this change.
3. **Spec R2 not testable at unit level**: "No cross-contamination with other error types" cannot be tested at the single-detector level since each detector handles only contract errors. Cross-contamination verification belongs at the `detect_all` integration level.

## Pre-existing Failures (unrelated to this change)

| Test File | Failure Count | Root Cause |
|-----------|--------------|------------|
| `tests/services/test_constants_package.py` | 1 (collection) | Import error: `PYP_CODES_ONLY_ODONTOLOGO` not found |
| `tests/services/test_duplicados_farmacia.py` | 5 | Farmacia detector returning 0 instead of 1 |
| `tests/services/test_react_frontend.py` | 1 | manifest.json has 12 HTML entries, test expects 11 |
| `tests/services/test_routes_fec_factura.py` | 6 | Missing "N° Reingreso" column in test fixture |

## Status
**8/8 tasks complete.** Ready for verify phase.
