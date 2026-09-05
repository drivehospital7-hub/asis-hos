# Tasks: Migrate `cups_sin_contrato` to DB Rule Engine

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500 (170 evaluator + 50 SQL + 30 stub + 200 tests + 50 cleanup/registration) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Evaluator + Registration (220 LoC) → PR 2: Seed SQL + Legacy Stub (80 LoC) → PR 3: Tests + Cleanup (200 LoC) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | `CupsContratadoEvaluator` class + registration in `_register_builtins()` | PR 1 | base=main; +unit tests for evaluator internals |
| 2 | Seed SQL update + legacy stub | PR 2 | base=main or PR 1 branch; +integration test |
| 3 | Port 30+ test scenarios + remove legacy test file | PR 3 | base=main or PR 2 branch; snapshot comparison |

## Phase 1: Foundation — Pre-work

- [x] 1.1 Read `CentroCostoCheckEvaluator` and `SalaObservacionEvaluator` patterns in `evaluators.py` for internal structure reference
- [x] 1.2 Review the 5 DB tables (`eps_contratado`, `eps_nota`, `nota_hoja`, `notas_tecnicas`, `procedimiento`) and confirm the JOIN query returns correct data
- [x] 1.3 Create test harness for the new evaluator (fixtures, mock `EvaluationContext`, pre-loaded data helpers)

## Phase 2: CupsContratadoEvaluator — Core

- [x] 2.1 Implement `CupsContratadoEvaluator.__init__()` with cache attributes (`_pares_validos`, `_eps_map`, `_nota_urgencias_cups`, `_nota_cap_cups`, `_entidades_con_datos`) and `_loaded: bool = False`
- [x] 2.2 Implement `_preload_data(session)` — 5-table JOIN for `pares_validos` + 3 aux queries for `eps_map`, `nota_urgencias_cups`, `nota_cap_cups`
- [x] 2.3 Implement `evaluate()` with 6-branch exception chain: farmacia skip → urgencias nota_hoja → CAP+ESS118 → CAP+EPSS41 → normal check → codigo_equiv → FEV
- [x] 2.4 Register `"cups_contratado"` operator in `_register_builtins()`
- [x] 2.5 Unit tests: each exception branch in isolation with mocked context (6 test cases, 32 total tests)

## Phase 3: Seed SQL & Legacy — Wiring

- [x] 3.1 Update `seed/phase7/insert_procedimiento_contratado.sql` — replace current `NOT(exists_in_db(...))` tree with `NOT(cups_contratado(invoice.codigo, ...))`
- [x] 3.2 Stub `detect_cups_sin_contrato` in `procedimiento_contratado.py` to delegate to `RuleBasedDetector` when `USE_RULE_ENGINE=true`
- [x] 3.3 Integration test: snapshot comparison against legacy detector output for all 9 scenario types

## Phase 4: Cleanup

- [x] 4.1 Remove legacy test file `tests/services/test_detect_cups_sin_contrato.py`
- [x] 4.2 Final verification: `python -m pytest -v` passes (390 engine tests), seed SQL re-runs idempotent
