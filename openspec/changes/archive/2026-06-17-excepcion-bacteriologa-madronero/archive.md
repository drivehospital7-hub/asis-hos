# SDD Archive Report — Excepción bacterióloga MADROÑERO (02217)

**Archived**: 2026-06-17
**Change**: Agregar excepción para MADROÑERO BURBANO KAREN LIZETH (02217) en el detector de bacteriólogas vs cronograma

---

## Summary

Se implementó una excepción para que la bacterióloga MADROÑERO BURBANO KAREN LIZETH (código 02217) pueda facturar cualquier día sin validación de cronograma, mediante un nuevo `frozenset` `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` en `app/constants/urgencias.py`.

---

## Artifacts

| Artifact | Location |
|----------|----------|
| Delta spec | `openspec/changes/archive/2026-06-17-excepcion-bacteriologa-madronero/specs/intramural-bacteriologas-cronograma/spec.md` |
| Design | `openspec/changes/archive/2026-06-17-excepcion-bacteriologa-madronero/designs/intramural-bacteriologas-cronograma/design.md` |
| Tasks | `openspec/changes/archive/2026-06-17-excepcion-bacteriologa-madronero/tasks/intramural-bacteriologas-cronograma/tasks.md` |
| Archive report | `openspec/changes/archive/2026-06-17-excepcion-bacteriologa-madronero/archive.md` |

## Engram Traceability

| Artifact | Observation ID |
|----------|---------------|
| Apply progress | #646 — `sdd/excepcion-bacteriologa-madronero/apply-progress` |
| Verify report | #647 — `sdd/excepcion-bacteriologa-madronero/verify-report` |
| Archive report | — `sdd/excepcion-bacteriologa-madronero/archive-report` |

---

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| intramural-bacteriologas-cronograma | Updated | 1 ADDED requirement (PROFESIONALES_EXCEPTUADOS_CRONOGRAMA), 5 scenarios, 1 acceptance criterion |

**Merge details**:
- Appended `Requirement: PROFESIONALES_EXCEPTUADOS_CRONOGRAMA SHALL skip cronograma validation` to the ADDED Requirements section
- Added `Acceptance Criteria 7` for PROFESIONALES_EXCEPTUADOS_CRONOGRAMA bypass

---

## Implementation Verified (from verify report)

- **Verdict**: PASS
- **Tasks**: 4/4 complete
- **Tests**: 50/50 pass (including 3 new tests in `TestProfesionalesExceptuados`)
- **Spec scenarios**: 5/5 compliant
- **Files changed**: 3

### Files implemented

| File | Change |
|------|--------|
| `app/constants/urgencias.py` L49-50 | `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA = frozenset({"02217"})` |
| `app/services/intramural/bacteriologas_cronograma.py` L23 | Import `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` |
| `app/services/intramural/bacteriologas_cronograma.py` L309-311 | Bypass check: `if codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA: continue` |
| `tests/services/test_intramural_bacteriologas_cronograma.py` L1255-1332 | `TestProfesionalesExceptuados` class (3 tests) |

---

## Key Technical Decisions

1. **Check placement**: After BACTERIOLOGA type gate, before `responsable_cierra`/`siglas_filter`/`get_turno_del_dia` — earliest possible exit after confirming the professional is a BACTERIOLOGA
2. **Data structure**: `frozenset` (same pattern as `EXCEPCIONES_BACTERIOLOGA`, `FACTURADORES_URGENCIAS`) — immutable, O(1) lookup
3. **No existing tests modified**: The check is inserted at a point that doesn't change behavior for non-excepted professionals; all existing tests pass unchanged

---

## Source of Truth Updated

The main spec at `openspec/specs/intramural-bacteriologas-cronograma/spec.md` now reflects the new PROFESIONALES_EXCEPTUADOS_CRONOGRAMA behavior.

---

## SDD Cycle Complete

This change has been fully planned, specified, designed, implemented, verified, and archived. Ready for the next change.
