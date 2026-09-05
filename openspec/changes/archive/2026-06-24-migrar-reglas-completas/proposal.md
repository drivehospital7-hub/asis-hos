# Proposal: Migración Completa de Reglas Legacy al Motor de Reglas

## Intent

Migrate all 21 remaining legacy detectors to the DB-backed rule engine, eliminating the dual code path. Enables non-dev rule tuning, engine-native evidence audit, and single evaluation paradigm. `USE_RULE_ENGINE=false` preserves instant rollback at every phase.

## Scope

### In Scope
- 21 detectors across transversales, odontología, urgencias, equipos_basicos
- 7 incremental phases, each producing working rules with snapshot tests
- 8 new engine capabilities: lookup providers, date/string functions, group-by, pre-scan, multi-rule cascade, DB cross-reference, constants provider

### Out of Scope
- `create_revision_sheet` (orchestrator), new business rules, admin UI, perf beyond parity

## Capabilities

### Modified Capabilities
- **motor-reglas**: New evaluators (`startswith`, `regex_extract`, `age_from_dates`, `hours_diff`, `day_of_month`), new providers (`CatalogProvider`, `ContractProvider`, `CodeMappingProvider`, `DateProvider`), group-by evaluation mode, pre-scan hook, multi-rule cascade.

### New Capabilities
- **catalog-data**: DB tables and seed data for professionals, contract mappings, code substitutions, and domain constants — replacing hardcoded Python dictionaries.

## Approach

Each phase: (1) extend engine + unit tests, (2) create DB rules with condition trees, (3) wire into `detect_all.py` under flag, (4) simulator diff legacy vs engine — 100% match required, (5) all 200+ existing tests must pass. Phases ordered by risk: row-by-row (1-2) → catalog/constants (3-4) → date/string (5) → group-by (6) → DB cross-reference (7). Each phase is independently shippable.

## Affected Areas

| Area | Impact |
|------|--------|
| `app/services/engine/` | New evaluators, providers, group-by mode, pre-scan hook |
| `app/services/{transversales,odontologia,urgencias,equipos_basicos}/` | 21 detectors → engine delegation |
| `app/models/` | New: Profesional, CatalogoCodigo, ConstanteSistema tables |
| `app/constants/` → DB seed | Constants migrated to catalog-data tables |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Group-by changes evaluation paradigm | High | Parallel `GroupEvaluator`, zero `RowEvaluator` changes |
| Pre-scan adds complexity | Medium | Single-pass metadata cached in `EvaluationContext` |
| Snapshot diffs miss edge cases | Medium | Legacy detectors frozen as golden tests; real Excel samples |
| DB cross-reference JOIN perf | Medium | Pre-load valid pairs once, matching legacy approach |

## Rollback Plan

`USE_RULE_ENGINE=false` restores all legacy detectors instantly. Legacy code preserved untouched. No destructive data migrations.

## Dependencies

- Existing engine + PostgreSQL `reglas` schema
- Simulator service extended per phase

## Success Criteria

- [ ] Phases 1-7: all detectors produce identical output to legacy (simulator diff = 0)
- [ ] All 200+ existing tests pass after every phase
- [ ] `USE_RULE_ENGINE=false` fully restores legacy at any phase
- [ ] Per-phase detectors: P1=5 simple, P2=3 catalog, P3=3 IDE contract, P4=3 centro_costo, P5=2 date/age, P6=3 group-by, P7=2 DB cross-ref
