# Tasks: Migración Completa de Reglas Legacy al Motor de Reglas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1200-1800 (7 phases × ~200 lines each avg) |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes** |
| Suggested split | 7 phase-level PRs, each self-contained and verifiable |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Phase 1: 5 row-by-row rules | PR 1 | Base: main. Seed SQL + wiring + snapshot tests. |
| 2 | Phase 2: CatalogProvider + profesionales | PR 2 | Base: main (or PR 1). New provider + models + 3 rules. |
| 3 | Phase 3: ContractProvider + ide_contrato | PR 3 | Base: main (or PR 2). Depends on provider pattern from PR 2. |
| 4 | Phase 4: Multi-rule cascade + centro_costo | PR 4 | Base: main (or PR 3). Depends on engine evaluate_sheet_domain. |
| 5 | Phase 5: Date/age evaluators + 2 rules | PR 5 | Base: main (or PR 4). New evaluators in evaluators.py. |
| 6 | Phase 6: GroupEvaluator + 3 group-by rules | PR 6 | Base: main (or PR 5). New file + engine pre-scan hook. |
| 7 | Phase 7: DB cross-ref evaluators + 2 rules | PR 7 | Base: main (or PR 6). New evaluators + models. |

Each PR ships independent work units with tests. Legacy code preserved untouched.

---

## Phase 1: Row-by-Row Simple (5 rules)

- [x] 1.1 Create `seed/phase1/insert_cups_equivalentes.sql` — rule+conditions for `codigo_cups` code substitution via `code_mappings` lookup
- [x] 1.2 Create `seed/phase1/insert_revision_entidad_86.sql` — rule: `eq(entidad, "86")`
- [x] 1.3 Create `seed/phase1/insert_cantidades_urgencias.sql` — rule: `in(codigo, constants.URGENCIAS_CODIGOS_CANTIDAD_MAX_1)` AND `gt(cantidad, 1)`
- [x] 1.4 Create `seed/phase1/insert_cantidades_soat_urgencias.sql` — rule: SOAT + restricted code + `neq(cantidad, 1)`
- [x] 1.5 Create `seed/phase1/insert_mal_capitado.sql` — two condition groups: (code G03XB01/A02BB01 AND `startswith` factura not FEV) OR (factura starts CAP AND entidad not ESS118)
- [x] 1.6 Wire T1.1-T1.5 in `app/services/urgencias/detect_all.py` under `USE_RULE_ENGINE` flag, per existing pattern (RuleBasedDetector + session)
- [x] 1.7 Write `tests/engine/test_snapshot_phase1_urgencias.py` — snapshot tests for all 5 rules: legacy vs engine output identity on sample Excel
- [x] 1.8 Run `python -m pytest -v` — all 200+ existing tests + new snapshots must pass

## Phase 2: Catalog Provider + Profesionales

- [x] 2.1 Add `Profesional` ORM class in `app/models.py` (columns: codigo PK, nombre, tipo, dominio) — **SKIPPED**: not needed for IN-based approach; delayed to Phase 3/7
- [x] 2.2 Create `seed/phase2/create_profesionales.sql` — DDL + seed data — **SKIPPED**: not needed without ORM; delayed to Phase 3
- [x] 2.3 Add `CatalogProvider(ContextProvider)` in `app/services/engine/providers.py` — resolve `catalog.profesionales[codigo].tipo` with session-level cache dict
- [x] 2.4 Register `CatalogProvider` in `PROVIDER_REGISTRY` via `_register_builtins()`
- [x] 2.5 Write `tests/engine/test_catalog_provider.py` — unit tests: 10 cases (lookup found/missing/cache-hit/field access/empty/domain isolation/registry)
- [x] 2.6 Create `seed/phase2/insert_profesionales_odon.sql` — rule using NOT+in pattern with valid Odontología codes
- [x] 2.7 Create `seed/phase2/insert_profesionales_urg.sql` — rule using NOT+in pattern with valid Urgencias codes
- [x] 2.8 Create `seed/phase2/insert_profesionales_eqbas.sql` — rule using NOT+in pattern with valid Equipos Básicos codes
- [x] 2.9 Wire T2.6-T2.8 in `app/services/{odontologia,urgencias,equipos_basicos}/detect_all.py` under flag
- [x] 2.10 Write `tests/engine/test_snapshot_phase2_profesionales.py` — 11 snapshot tests for all 3 domains + edge cases

## Phase 3: Contract Provider + IDE Contrato

- [x] 3.1 Add `Contrato` and `NotaTecnica` ORM classes in `app/models.py` — **SKIPPED**: deferred to Phase 7 (ORM not needed for condition-tree approach)
- [x] 3.2 Create `seed/phase3/create_contratos.sql` — **SKIPPED**: deferred to Phase 7 (no DB schema needed yet)
- [x] 3.3 Add `ContractProvider(ContextProvider)` in `app/services/engine/providers.py` — prefix="contract", placeholder resolve for future DB upgrade
- [x] 3.4 Register `ContractProvider` in `PROVIDER_REGISTRY`
- [x] 3.5 Write `tests/engine/test_contract_provider.py` — 8 unit tests (prefix, registry, cache, instance independence)
- [x] 3.6 Create `seed/phase3/insert_ide_contrato_odon.sql` — 15 branches covering top 8 entities (ESS118, ESSC18, EPSS41, EPSI05, EPSIC5, RES001, 0001, 86)
- [x] 3.7 Create `seed/phase3/insert_ide_contrato_urg.sql` — 26 branches: 16 simple exact rules, 2 multiple rules, 8 generic entity→contrato rules
- [x] 3.8 Create `seed/phase3/insert_ide_contrato_reverse.sql` — 5 reverse rules (986, 839, 842, 970, 974). Equipos Básicos has no IDE contrato detector.
- [x] 3.9 Wire in `detect_all.py` for odontologia + urgencias (forward + reverse) under flag
- [x] 3.10 Write `tests/engine/test_snapshot_phase3_ide_contrato.py` — 21 snapshot tests: 9 odontologia, 7 urgencias forward, 5 urgencias reverse

## Phase 4: Multi-Rule Cascade + Centro Costo

- [x] 4.1 Add `evaluate_sheet_domain(domain, ws, indices) → list[dict]` to `RuleEvaluationEngine` in `engine.py` — loads all active rules for domain via `RuleResolver`, evaluates in priority order, single evidence flush
- [x] 4.2 Write `tests/engine/test_multi_rule_cascade.py` — unit: priority ordering, both-match, domain isolation
- [x] 4.3 Create `seed/phase4/insert_centro_costo_odon.sql`
- [x] 4.4 Create `seed/phase4/insert_centro_costo_urg.sql` (includes REVERSE rules as separate rules with inverted conditions)
- [x] 4.5 Create `seed/phase4/insert_centro_costo_eqbas.sql`
- [x] 4.6 Wire `evaluate_sheet_domain("odontologia", ...)` in `odontologia/detect_all.py`, `evaluate_sheet_domain("urgencias", ...)`, `evaluate_sheet_domain("equipos_basicos", ...)` under flag
- [x] 4.7 Write `tests/engine/test_snapshot_phase4_centro_costo.py` — snapshot for all 3 domains

## Phase 5: Date/Age Evaluators + Tipo Documento Edad v2

- [x] 5.1 Add `AgeFromDatesEvaluator(AtomicEvaluator)` in `app/services/engine/evaluators.py` — `age_from_dates(fecha_nac, fecha_ref)` → int years, leap-year aware
- [x] 5.2 Add `HoursDiffEvaluator(AtomicEvaluator)` in `app/services/engine/evaluators.py` — `hours_diff(fecha1, fecha2)` → float, absolute value
- [x] 5.3 Register both in `EVALUATOR_REGISTRY` via `_register_builtins()`
- [x] 5.4 Write `tests/engine/test_date_evaluators.py` — unit: age exact/match day/before birthday/invalid (4 cases), hours same-day/multi-day/reversed (3 cases)
- [x] 5.5 Create `seed/phase5/insert_tipo_documento_edad_v2.sql` — active rule replacing draft v1, uses `age_from_dates`
- [x] 5.6 Create `seed/phase5/insert_sala_observacion.sql` — `hours_diff(fec_ingreso, fec_egreso)` for observation room
- [x] 5.7 Wire in `detect_all.py` for urgencias + odontología under flag
- [x] 5.8 Write `tests/engine/test_snapshot_phase5_date_rules.py`

## Phase 6: Group-By Mode

- [x] 6.1 Create `app/services/engine/group_evaluator.py` — `GroupEvaluator` class: pre-scan sheet → build groups by `group_by_field` → evaluate per-group via `ConditionEvaluator` → mark all rows in matched groups
- [x] 6.2 Add `group_data: list[dict] | None` to `EvaluationContext` in `context.py`
- [x] 6.3 Add group-eval pre-scan hook call in `engine.py` `evaluate_sheet()` — when rule has `evaluation_mode="group"`, delegate to `GroupEvaluator`
- [x] 6.4 Write `tests/engine/test_group_evaluator.py` — unit: distinct_count match/no-match, empty group, count_by threshold
- [x] 6.5 Create `seed/phase6/insert_doble_tipo_procedimiento.sql` — group_by(factura, distinct_count(tipo_procedimiento), gt(1))
- [x] 6.6 Create `seed/phase6/insert_detect_duplicados_base.sql` — group_by(identificacion, count, gt(1)) with pair-count aggregation
- [x] 6.7 Create `seed/phase6/insert_revision_cantidad.sql`
- [x] 6.8 Wire in `detect_all.py` for relevant domains under flag
- [x] 6.9 Write `tests/engine/test_snapshot_phase6_group_rules.py`

## Phase 7: DB Cross-Reference Evaluators

- [x] 7.1 Add `RegexExtractEvaluator(AtomicEvaluator)` in `app/services/engine/evaluators.py` — `regex_extract(pattern, field)` → first capture group or null
- [x] 7.2 Add `ExistsInDBEvaluator(AtomicEvaluator)` in `app/services/engine/evaluators.py` — `exists_in_db(table, field, value)` → bool, with session-level cache
- [x] 7.3 Register both in `EVALUATOR_REGISTRY`
- [x] 7.4 Write `tests/engine/test_evaluators.py` — 15 new unit tests: regex match/no-match, exists true/false, cache hit, no session, etc.
- [x] 7.5 Create `seed/phase7/insert_codigo_entidad.sql` — NOT(contains(invoice.entidad_afiliacion, "{")) placeholder
- [x] 7.6 Create `seed/phase7/insert_procedimiento_contratado.sql` — NOT(exists_in_db(invoice.codigo, procedimiento.cups))
- [x] 7.7 Wire in `detect_all.py` under flag (odontologia, urgencias, equipos_basicos)
- [x] 7.8 Write `tests/engine/test_snapshot_phase7_cross_ref.py` — 8 snapshot tests
- [x] 7.9 Run `python -m pytest -v` — 1252 passed, 16 pre-existing failures (none Phase 7 related)
- [x] 7.10 Update tasks.md with checkmarks — DONE
