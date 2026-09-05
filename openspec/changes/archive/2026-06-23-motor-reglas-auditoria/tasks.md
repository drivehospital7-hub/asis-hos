# Tasks: Motor de Reglas con Auditoría

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1500 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

**Work Units**: PR 1 → Foundation (models, seeds, constants) | PR 2 → Engine Core (evaluators, providers, resolver, tree, exceptions, evidence, orchestrator) | PR 3 → Wrapper + Integration | PR 4 → Tests

---

## Phase 1: Foundation

- [x] 1.1 Add `Regla`, `Condicion`, `Excepcion`, `ResultadoAuditoria`, `Evidencia` models to `app/models.py` per design DB Schema — all columns, relationships, `to_dict()`
- [x] 1.2 Create `app/services/engine/__init__.py`
- [x] 1.3 Create `app/services/engine/context.py`: `EvaluationContext` dataclass — `invoice_data`, `patient_data`, `reference_data`, `indices`, `session`
- [x] 1.4 Add to `app/constants/base.py`: `ENGINE_DOMAIN_TRANSVERSAL`, `RULE_STATES` frozenset, `DEFAULT_SEVERITY`, `is_rule_engine_enabled()`
- [x] 1.5 Create `seeds/motor_reglas_seed.sql` with INSERTs for 3 PoC rules: `valores_decimales`, `ruta_duplicada`, `tipo_documento_edad` with condition trees per design Migration Strategy
- [ ] 1.6 Run seeds; verify `SELECT * FROM reglas WHERE dominio='odontologia'` returns 3 rules

## Phase 2: Engine Core

- [x] 2.1 Create `app/services/engine/evaluators.py`: `AtomicEvaluator` ABC + registry + built-ins (Eq, Gt, Gte, Lt, Lte, In, Contains). Unknown operator → log + ERROR
- [x] 2.2 Create `app/services/engine/providers.py`: `ContextProvider` ABC + `InvoiceProvider` (prefix=`invoice` resolving `invoice.vlr_subsidiado` etc.) + registry
- [x] 2.3 Create `app/services/engine/rule_resolver.py`: `RuleResolver.resolve(domain, session)` — loads active rules matching domain, ordered by priority
- [x] 2.4 Create `app/services/engine/condition_evaluator.py`: `ConditionEvaluator` — builds tree from `condiciones` rows, recursive AND/OR/NOT with short-circuit, collects per-node trace
- [x] 2.5 Create `app/services/engine/exception_handler.py`: `ExceptionHandler.apply_exceptions(rule, context)` — queries matching excepciones, returns skip flag or param overrides
- [x] 2.6 Create `app/services/engine/evidence_collector.py`: `EvidenceCollector` — `record()` builds tree trace, `flush_batch()` uses `session.add_all()` + `flush()`. No UPDATE/DELETE paths
- [x] 2.7 Create `app/services/engine/engine.py`: `RuleEvaluationEngine.evaluate_sheet(rule_name, data_sheet, indices)` — load rule → check exceptions → iterate rows → evaluate → collect evidence → return `list[dict]`

## Phase 3: Wrapper + Integration

- [x] 3.1 Create `app/services/engine/rule_based_detector.py`: `RuleBasedDetector(rule_name, session).detect(data_sheet, indices) → list[dict]` matching legacy interface
- [x] 3.2 Modify `app/services/odontologia/detect_all.py`: add `USE_RULE_ENGINE` env flag; when true, delegate `decimales` and `ruta_dup` to `RuleBasedDetector`
- [x] 3.3 Add migration note docstrings to `app/services/transversales/decimales.py` and `ruta_duplicada.py`

## Phase 4: Testing

- [x] 4.1 Create `tests/engine/test_evaluators.py`: parametrized truth tables per evaluator (33 tests, ≥3 cases each)
- [x] 4.2 Create `tests/engine/test_condition_evaluator.py`: AND/OR/NOT truth tables with short-circuit assertions; unknown operator → ERROR (20 tests)
- [x] 4.3 Create `tests/engine/test_rule_resolver.py`: mock session → `resolve('odontologia')` → assert filtering/sorting (6 tests)
- [x] 4.4 Create `tests/engine/test_exception_handler.py`: skip, override, no-op scenarios (6 tests)
- [x] 4.5 Create `tests/engine/test_engine_integration.py`: `evaluate_sheet()` with crafted Excel rows → assert detections + evidence immutability (4 tests)
- [x] 4.6 Create `tests/engine/test_snapshot_legacy_vs_engine.py`: legacy output format validation vs engine output (3 tests)

---

> `decimales` → rule `valores_decimales`, `ruta_duplicada` → rule `ruta_duplicada`. `tipo_documento_edad` deferred due to DB-lookup complexity.
