# Tasks: Hazlo — Replace centro_costo evaluators with condition trees

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~800–1200 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation + Migrations → PR 2: Tests + Cleanup |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Catalog seeds + CI fix + SQL migrations | PR 1 | base=main; additive only, no behavior change |
| 2 | Tests + evaluator removal + deprecation | PR 2 | base=main; depends on PR 1 for verification |

## Phase 1: Foundation

- [x] 1.1 Seed 14 `catalogos` entries with constant sets from evaluator code — file: `13_catalogos_centro_costo.sql` (renumbered from 12 because 12 already exists)
- [x] 1.2 Add `.strip().upper()` normalization to `CatalogInEvaluator.evaluate()` in `app/services/engine/evaluators.py`
- [x] 1.3 Create equivalence test fixture in `tests/engine/test_centro_costo_tree.py` — 53 equivalence tests covering all REGLAs, edge cases, and neutral baselines

## Phase 2: Deployment

- [x] 2.1 Create `seed/migracion-engine/14_centro_costo_comun.sql` — OR→AND/NOT/cat_in tree for 4 rules: hospitalizacion, equipos_basicos, odontologia, urgencias
- [x] 2.2 Create `seed/migracion-engine/15_centro_costo_intramural.sql` — OR tree with common (minus REGLA3) + 9 intramural-specific REGLAs

## Phase 3: Verification

- [x] 3.1 Run equivalence test: 53 tests pass — legacy evaluator and condition tree produce IDENTICAL output for all REGLAs across forward, reverse, and negative paths
- [ ] 3.2 Snapshot test with real Excel files — deferred: requires migrations applied to a running DB with real test data

## Phase 4: Cleanup

- [x] 4.1 Add `DeprecationWarning` to `CentroCostoCheckEvaluator` and `CentroCostoIntramuralEvaluator` in `evaluators.py` — kept code with warnings for backward compat during migration
- [x] 4.2 Add `DeprecationWarning` + docstring to `apply_common_centro_costo_rules` in `app/services/transversales/centro_costo_rules.py`
