# Archive Report — migrar-legacy-restante

**Archived**: 2026-07-01
**Source of Truth**: `openspec/specs/motor-reglas/spec.md`

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| motor-reglas | Modified | R12 extended (group-level), R13 extended (collect_set, set_contains_all, set_intersects, compute_horas) |
| motor-reglas | Added | R16 (Hospitalización Codes), R17 (IDE Contrato Intramural), R18 (Sala Observación), R19 (Snapshot Testing Contract) |

## Archive Contents

- `proposal.md` ✅ — Intent, scope, approach for 4-phase migration
- `specs/motor-reglas/spec.md` ✅ — Delta spec (fixed R17 inaccuracy per verify report)
- `design.md` ✅ — Architecture decisions with corrected ~800 mappings for IDE_SIMPLE_RULES
- `tasks.md` ✅ — 25 tasks across 5 phases, 21/25 complete (4 DB-dependent pending)
- `verify/verify-report.md` ✅ — PASS WITH WARNINGS, 461/461 tests, 20/23 scenarios compliant

## Engram Observation IDs

| Artifact | Engram ID |
|----------|-----------|
| proposal | #813 |
| spec | #814 |
| design | #815 |
| tasks | #816 |
| apply-progress | #817 |
| verify-report | #820 |
| archive-report | (current) |

## Delta Spec Corrections Applied

Per verify report suggestion:
- **R17**: Corrected `CatalogInEvaluator` → `IdeContratoSimpleEvaluator`, `~80 mappings` → `~800 mappings`, reclassified from "Group Rules" to "Row-Level Evaluators"

## Known Gaps (Documented)

1. **AC-3 toggle**: `USE_RULE_ENGINE=false` cannot restore legacy because `is_rule_engine_enabled()` returns hardcoded `True` (from prior SDD). Not a regression of this change.
2. **Snapshot tests (R19)**: 3 scenarios untested — blocked on DB availability. Tasks T-2.5, T-3.3, T-3.6, T-4.7 remain pending.

## Verdict

**SDD cycle complete** — change fully planned, implemented (21/25 tasks), verified (PASS WITH WARNINGS), and archived. 4 pending tasks are DB-dependent and documented for follow-up.
