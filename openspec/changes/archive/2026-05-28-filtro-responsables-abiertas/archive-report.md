# Archive Report: Filtro por responsables en Abiertas Urgencias

**Change**: filtro-responsables-abiertas
**Archived**: 2026-05-28
**Artifact Store**: OpenSpec + Engram

---

## Change Summary

Pure frontend feature: added a native `<select>` dropdown to filter the Abiertas Urgencias results table by `responsable` (facturador de turno). Zero backend, API, or dependency changes. Implemented with `useState`+`useMemo` following the existing `control-novedades` pattern.

### Phases Completed

| Phase | Status | Artifact |
|-------|--------|----------|
| Proposal | ✅ | `proposal.md` |
| Spec | ✅ | `spec.md` — 7 requirements (R1-R7), 15 scenarios |
| Design | ✅ | `design.md` — 3 architecture decisions, data flow, 7 edge cases |
| Tasks | ✅ | `tasks.md` — 10 tasks across 3 phases |
| Apply | ✅ | `page.tsx` (~+35 lines), `utils.ts` (+2 pure functions), `utils.test.ts` (+8 tests) |
| Verify | ✅ | `verify-report.md` — PASS WITH WARNINGS, 44/44 tests passing, 0 critical issues |
| Archive | ✅ | This report |

### Files Changed

| File | Action | Lines |
|------|--------|-------|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modified | +~35 (state, useMemo, select, filter logic, reset) |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | Modified | +~20 (2 pure functions: `getUniqueResponsables`, `filterResultsByResponsable`) |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | Modified | +~30 (8 new test cases) |

### Files Not Changed (Confirmed)

| File | Reason |
|------|--------|
| `frontend/src/pages/abiertas-urgencias/utils.ts` → `copiarResultados` | Interface unchanged — accepts any `FacturaResult[]` subset |

---

## Spec Delta

All new — no existing main spec was modified. The spec describes page-level requirements for the filter feature:

| Domain | Action | Details |
|--------|--------|---------|
| `abiertas-urgencias` (page-level) | Created (new spec) | 7 requirements: R1 Selector Dinámico, R2 Filtro por Selección, R3 Valores Atípicos, R4 Opciones Únicas y Ordenadas, R5 Copiar Solo Filtrados, R6 Reactivo a Cambios, R7 Consistencia Visual |

---

## Design Delta

### Decisions Made & Implemented

| Decision | Status | Notes |
|----------|--------|-------|
| Copiar SOLO resultados filtrados | ✅ Implemented | `handleCopiarResultados` passes `filteredResults ?? results` |
| Resetear filtro al reprocesar | ✅ Implemented | `setFilterResponsable("")` after `setResults()` in `handleProcesarFacturas` |
| `useMemo` para responsables únicos | ✅ Implemented | `getUniqueResponsables()` with `Set` + `.sort()` |
| `useMemo` para filteredResults | ✅ Implemented | `filterResultsByResponsable()` dependent on `[results, filterResponsable]` |

### Deviation from Design

| Deviation | Details |
|-----------|---------|
| `utils.ts` modified despite design saying "No change" | ✅ Positive deviation: `getUniqueResponsables` and `filterResultsByResponsable` extracted as pure functions for testability (Extract-Before-Mock pattern) |

---

## Verification Results

| Metric | Value |
|--------|-------|
| Tasks total | 10 |
| Tasks complete | 10 |
| Tests total | 44 |
| Tests passed | 44 |
| Tests failed | 0 |
| Build | ✅ `tsc --noEmit` — zero errors |
| Verdict | **PASS WITH WARNINGS** |
| Critical issues | 0 |

### Spec Compliance

| Requirement | Scenarios | Status |
|-------------|-----------|--------|
| R1: Selector Dinámico | 3 | ✅ 1 compliant, 2 partial (static) |
| R2: Filtro por Selección | 3 | ✅ 2 compliant, 1 partial (static) |
| R3: Valores Atípicos | 2 | ✅ 2 compliant |
| R4: Opciones Únicas y Ordenadas | 2 | ✅ 2 compliant |
| R5: Copiar Solo Filtrados | 2 | ⚠️ 2 partial (static) |
| R6: Reactivo a Cambios | 2 | ⚠️ 2 partial (static) |
| R7: Consistencia Visual | 1 | ⚠️ 1 partial (static) |

**Note**: PARTIAL scenarios require component rendering to test (no jsdom/testing-library infra available). All extractable business logic IS unit tested (8 tests covering all 4 pure function behaviors).

---

## Lessons Learned

1. **Design deviations can be positive**: The design said "no change to utils.ts" but extracting pure functions (`getUniqueResponsables`, `filterResultsByResponsable`) enabled 8 unit tests that prove the logic without component mounting. The deviation was acknowledged in verify as a quality improvement.
2. **Testability extraction pattern**: Moving filter logic from inline `useMemo` (in component) to pure functions (in utils) followed the Extract-Before-Mock TDD pattern — business logic becomes testable without component infra.
3. **No jsdom = limited component testing**: The project lacks `@testing-library/react` / jsdom setup, so UI behaviors (select rendering, onChange firing, counter text) can only be verified statically or manually. Not a blocker, but worth addressing for future frontend work.
4. **Coverage gap**: `@vitest/coverage-v8` not installed — no coverage data available for changed files. Recommended for future changes.

---

## Archive Location

| Store | Location |
|-------|----------|
| **OpenSpec** | `openspec/changes/archive/2026-05-28-filtro-responsables-abiertas/` |
| **Engram** | `sdd/filtro-responsables-abiertas/archive-report` (topic_key) |

### Archive Contents

- `proposal.md` ✅
- `spec.md` ✅
- `design.md` ✅
- `tasks.md` ✅ (10/10 tasks complete)
- `verify-report.md` ✅
- `archive-report.md` ✅ (this file)

---

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.
