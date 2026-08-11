# Archive Report — limpiar-legacy-engine

**Archived**: 2026-07-01
**Previous location**: `openspec/changes/limpiar-legacy-engine/`
**Archive location**: `openspec/changes/archive/2026-07-01-limpiar-legacy-engine/`

---

## Summary

Closed the last 9 legacy gaps in the Rule Engine migration. Two new engine evaluators, 9 toggle wrappers, and 6 else clauses — completing the transition so the engine is the **única fuente de verdad** for all detection.

| Phase | Description | Status |
|-------|-------------|--------|
| F1 | 2 new evaluators: RevisionCantidadUrgenciasEvaluator + CupsEquivalentesTransversalEvaluator | ✅ |
| F2 | 9 pure-legacy detector toggles + 6 else clauses | ✅ |
| F3 | 31 tests for new evaluators (492 total passing) | ✅ |

**Verdict**: PASS — all 19 tasks complete, 31/31 spec scenarios compliant, 492 tests passing, 0 issues.

---

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `motor-reglas` | Updated | R20, R21 ADDED; R6, R7 MODIFIED; acceptance criteria extended |

### Requirements Modified in Main Spec (`openspec/specs/motor-reglas/spec.md`)

- **R6**: Extended from "Legacy Pipeline Wrapper" to "Legacy Pipeline Wrapper — Pure-Legacy Toggle". Added table of 9 pure-legacy detectors with their engine rule mappings.
- **R7**: Extended from "Feature Flag Rollback" to "Feature Flag Rollback — Else Clauses". Added table of 6 variables requiring `else: var = []`.
- **R20 (NEW)**: `RevisionCantidadUrgenciasEvaluator` specification with 9 scenarios.
- **R21 (NEW)**: `CupsEquivalentesTransversalEvaluator` specification with 4 scenarios.
- **Acceptance Criteria**: Appended 5 new acceptance criteria items for the new requirements.

---

## Artifact Traceability

| Artifact | File | Key Content |
|----------|------|-------------|
| Proposal | `proposal.md` | 3-phase plan: F1 (evaluators) + F2 (toggles/else) + F3 (tests) |
| Design | `design.md` | Row-level evaluators, toggle pattern, 9-file change plan, SQL rules |
| Specs (delta) | `specs/motor-reglas/spec.md` | R20 (9 scenarios), R21 (4 scenarios), R6/R7 modifications |
| Verify Report | `verify-report.md` | 19/19 tasks ✅, 492 tests ✅, 31/31 scenarios compliant |

---

## Files Changed (from Verify Report)

| File | Action |
|------|--------|
| `app/services/engine/evaluators.py` | +2 evaluators (lines 1251-1374) |
| `app/services/urgencias/detect_all.py` | Toggle for decimales + revision_cantidad |
| `app/services/equipos_basicos/detect_all.py` | Toggles for decimales, ruta_duplicada, cantidades_anomalas, ide_contrato; Else for doble_tipo, centro_costo |
| `app/services/hospitalizacion/detect_all.py` | Toggles for ide_contrato, profesionales; Else for decimales, tipo_identificacion_edad, cantidades_hospitalizacion, cantidades_soat_hospitalizacion |
| `app/services/unified_processor.py` | Toggle for cups_equivalentes_transversal |
| Tests: `test_revision_cantidad_urgencias_evaluator.py` | 20 tests |
| Tests: `test_cups_equivalentes_transversal_evaluator.py` | 11 tests |

---

## Verification Results

- **Build**: ✅ Passed
- **Tests**: 492 passed / 0 failed / 0 skipped
- **Coverage**: Not configured
- **Critical Issues**: None
- **Spec Compliance**: 31/31 scenarios — all COMPLIANT
- **Design Coherence**: All 4 architecture decisions followed exactly

---

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived.
No remaining legacy gaps — the Rule Engine is now the **única fuente de verdad**.
