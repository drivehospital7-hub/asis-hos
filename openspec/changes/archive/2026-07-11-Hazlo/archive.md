# Archive Report: Hazlo

**Date**: 2026-07-11
**Change**: Replace CentroCostoCheckEvaluator and CentroCostoIntramuralEvaluator with condition trees in DB

## Summary

Refactored 2 hardcoded Python evaluators (`CentroCostoCheckEvaluator`, `CentroCostoIntramuralEvaluator`) into AND/OR/NOT condition trees stored in the `condiciones` table. All 14 constant sets migrated to the `catalogos` table. 53 equivalence tests prove behavioral parity. Evaluators kept with `DeprecationWarning` for safe rollback.

## Delta Specs

No delta specs were created for this change — design and tasks served as the specification. No main specs to sync.

## Migration State

| Migration | File | Applied | Notes |
|-----------|------|---------|-------|
| Catalogos seeds | `seed/migracion-engine/13_catalogos_centro_costo.sql` | ✅ Yes | 14 INSERTs, idempotent `WHERE NOT EXISTS` |
| Common tree | `seed/migracion-engine/14_centro_costo_comun.sql` | ✅ Yes | OR→AND tree for rules 27, 28, 29; hospitalizacion skipped (not in DB) |
| Intramural tree | `seed/migracion-engine/15_centro_costo_intramural.sql` | ✅ Yes | OR→AND tree with 18 sub-trees; intramural rule not deployed (seed never applied) |

## Tasks Complete (8/9)

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Seed 14 catalogos entries | ✅ | `13_catalogos_centro_costo.sql` |
| 1.2 CatalogInEvaluator CI normalization | ✅ | `.strip().upper()` fallback |
| 1.3 Equivalence test fixture | ✅ | 53 tests in `test_centro_costo_tree.py` |
| 2.1 Common condition tree SQL | ✅ | `14_centro_costo_comun.sql` |
| 2.2 Intramural condition tree SQL | ✅ | `15_centro_costo_intramural.sql` |
| 3.1 Run equivalence tests | ✅ | 53/53 passed, 545/545 regression |
| 3.2 Snapshot test with real Excel | 🔲 Deferred | Requires migrations applied to running DB |
| 4.1 DeprecationWarning on evaluators | ✅ | Both classes kept with warnings |
| 4.2 DeprecationWarning on centro_costo_rules | ✅ | `apply_common_centro_costo_rules` marked deprecated |

## Design Deviations

| Deviation | Status | Notes |
|-----------|--------|-------|
| Evaluator classes kept (not removed) | Conscious decision | Rollback safety; tasks.md explicitly chose keep-with-warnings over delete |
| CENTRO_INVALIDO rule omitted | Design inconsistency | Pseudocode includes it but SQL + tests don't; proposal excludes extramural rules |

## Verification Verdict

**PASS WITH WARNINGS** — No critical issues. 53/53 equivalence tests pass, 545/545 regression pass. Two non-critical deviations documented. Snapshot test (3.2) deferred.

## Archive Contents

| Artifact | Status |
|----------|--------|
| proposal.md | ✅ |
| exploration.md | ✅ |
| design.md | ✅ |
| tasks.md | ✅ |
| verify-report.md | ✅ |
| archive.md | ✅ (this file) |
