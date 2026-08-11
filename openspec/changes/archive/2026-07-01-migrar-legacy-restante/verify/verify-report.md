# Verification Report

**Change**: migrar-legacy-restante
**Version**: motor-reglas delta spec v1.0
**Mode**: Standard

## Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 25 |
| Tasks complete | 21 |
| Tasks incomplete | 4 |

### Incomplete Tasks (DB-dependent, documented)
| Task | Description | Reason |
|------|-------------|--------|
| T-2.5 | Snapshot test hospitalizacion codes | Requiere DB con data real |
| T-3.3 | DB migration: seed catalogos con IDE_SIMPLE_RULES | ~800 rows JSONB |
| T-3.6 | Snapshot test intramural evaluators | Requiere DB con data real |
| T-4.7 | Integration test: snapshot sala_observacion | Requiere DB con data real |

## Build & Tests Execution

**Build**: ✅ Passed (imports verificados: `_get_hospitalizacion_detectors`, `_get_intramural_detectors`)

**Tests**: ✅ 461 passed / ❌ 0 failed / ⚠️ 0 skipped
```
pytest tests/engine/ --tb=short -q
461 passed in 5.86s
```

**Coverage**: ➖ Not available (no coverage threshold in scope)

## Spec Compliance Matrix

### R12: Hours Diff Evaluator (Group-Level)
| Scenario | Test | Result |
|----------|------|--------|
| Mismo día (6.5h) | `test_group_evaluator.py > test_compute_horas_same_day` | ✅ COMPLIANT |
| Multi-day (48h) | `test_group_evaluator.py > test_compute_horas_multi_day` | ✅ COMPLIANT |
| Orden inverso | `test_group_evaluator.py > test_compute_horas_inverted_order` | ✅ COMPLIANT |
| Group agg | `test_group_evaluator.py > test_evaluate_compute_horas_gt_24h` | ✅ COMPLIANT |

### R13: Group-By Evaluator (Extended)
| Scenario | Test | Result |
|----------|------|--------|
| Distinct count | `test_group_evaluator.py > test_evaluate_detects_doble_tipo` | ✅ COMPLIANT |
| compute_horas | `test_group_evaluator.py > test_evaluate_compute_horas_gt_24h` | ✅ COMPLIANT |
| set_contains_all | `test_hospitalizacion_codes_rules.py > test_oblig_mayor24h_missing_code` | ✅ COMPLIANT |
| set_intersects | `test_hospitalizacion_codes_rules.py > test_prohibidos_detected` | ✅ COMPLIANT |

### R16: Hospitalización Codes — Group Rule
| Scenario | Test | Result |
|----------|------|--------|
| Obligatorio falta (>24h) | `test_hospitalizacion_codes_rules.py > test_oblig_mayor24h_missing_codes` | ✅ COMPLIANT |
| Prohibido presente | `test_hospitalizacion_codes_rules.py > test_prohibidos_detected` | ✅ COMPLIANT |
| Sin problemas | `test_hospitalizacion_codes_rules.py > test_no_problems_when_all_oblig_present` | ✅ COMPLIANT |
| SOAT variant | `test_hospitalizacion_codes_rules.py > test_prohibidos_soat_detected` | ✅ COMPLIANT |

### R17: IDE Contrato Intramural — Group Rules
| Scenario | Test | Result |
|----------|------|--------|
| IDE match | `test_ide_contrato_simple_evaluator.py > test_match_exact` | ✅ COMPLIANT |
| Solo lab (pre-scan) | `test_pym_rutas_dx_evaluator.py > test_pre_scan_laboratorio_envio_skip` | ✅ COMPLIANT |
| Sin mapping | `test_ide_contrato_simple_evaluator.py > test_no_rule_returns_true` | ✅ COMPLIANT |
| PYM_RUTAS + Dx | `test_pym_rutas_dx_evaluator.py > test_pym_rutas_dx_match` | ✅ COMPLIANT |

### R18: Sala Observación — Group Rules
| Scenario | Test | Result |
|----------|------|--------|
| Obligatorios faltan | `test_sala_observacion_rules.py > test_obligatorios_sin_oblig` | ✅ COMPLIANT |
| ESS prohibido (129B02) | `test_sala_observacion_rules.py > test_ess_129b02_detected` | ✅ COMPLIANT |
| 890601H falta | `test_sala_observacion_rules.py > test_890601h_prohibido` | ✅ COMPLIANT |
| Todo OK | `test_sala_observacion_rules.py > test_no_match_cuando_ok` | ✅ COMPLIANT |
| SOAT completo | `test_sala_observacion_rules.py > test_soat_completo_sin_oblig` | ✅ COMPLIANT |
| SOAT prohibido 39133 | `test_sala_observacion_rules.py > test_soat_prohibido_39133_detected` | ✅ COMPLIANT |
| 05DSB01 no-ESS | `test_sala_observacion_rules.py > test_05dsb01_no_ess_detected` | ✅ COMPLIANT |

### R19: Snapshot Testing Contract
| Scenario | Test | Result |
|----------|------|--------|
| Hospitalización 100+ | T-2.5 (incomplete, requires DB) | ❌ UNTESTED |
| IDE contrato 100+ | T-3.6 (incomplete, requires DB) | ❌ UNTESTED |
| Sala observación 100+ | T-4.7 (incomplete, requires DB) | ❌ UNTESTED |

**Compliance summary**: 20/23 scenarios compliant, 3 untested (DB-dependent)

## Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| compute_horas aggregation | ✅ Implemented | `_agg_compute_horas()` in group_evaluator.py, dispatched via `_build_group_data()` |
| hosp_codigos rules (3 rules) | ✅ Implemented | Toggled in hospitalizacion/detect_all.py via RuleBasedDetector |
| IdeContratoSimpleEvaluator | ✅ Implemented | operator `ide_simple_check`, registered in EVALUATOR_REGISTRY |
| PymRutasDxEvaluator | ✅ Implemented | operator `pym_rutas_dx_check`, registered in EVALUATOR_REGISTRY |
| Sala obs group rules (6 rules) | ✅ Implemented | 6 rules in urgencias/detect_all.py |
| IDE contrato urgencias toggle | ✅ Implemented | Reuses IdeContratoSimpleEvaluator with `ide_contrato_simple_urgencias` |
| Legacy files kept (dead) | ✅ As designed | `hospitalizacion_codes.py`, `ide_contrato_intramural.py`, `sala_observacion.py` remain importable |
| `is_rule_engine_enabled()` = True | ✅ Always-on | From prior SDD (Fase 6), engine permanently enabled |
| 4 incomplete tasks documented | ✅ Documented | In tasks.md and apply-progress |

## Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| compute_horas in GroupEvaluator | ✅ Yes | `_agg_compute_horas()` in `_build_group_data()` dispatch |
| hospitalizacion_codes as group rules | ✅ Yes | 3 rules using collect_set + set_contains_all/set_intersects |
| IdeContratoSimpleEvaluator (not CatalogIn) | ✅ Yes | Dedicated evaluator for 2-key lookup (~800 mappings) |
| PymRutasDxEvaluator with pre-scan | ✅ Yes | Instance-level cache, pre_scan_sheet() method |
| Sala obs as 6 group rules | ✅ Yes | 6 rules registered in detect_all.py loop |
| Legacy files kept (dead) | ✅ Yes | Importable but not called (engine always on) |
| data_sheet in EvaluationContext | ➖ Open | Not added; PymRutasDx does own pre_scan — acceptable |
| DB migration deferred | ✅ As planned | Documented as pending for all 4 incomplete tasks |

## Issues Found

**CRITICAL**: None

**WARNING**:
1. **Spec deviation — R17 incorrectly references CatalogInEvaluator**: The spec says `~80 mappings via CatalogInEvaluator`, but the actual has ~800 mappings requiring `IdeContratoSimpleEvaluator`. The design corrected this, the spec was not updated. This is a doc gap, not a code bug.
2. **AC-3 no longer achievable via toggle**: Spec AC-3 says `USE_RULE_ENGINE=false` restores legacy, but `is_rule_engine_enabled()` was permanently set to `return True` in a prior SDD. The code structure still supports the toggle pattern (else branches exist), but no env-var toggle is available. Minor scope conflict between SDDs.
3. **3 snapshot scenarios untested**: R19 scenarios (Hospitalización 100+, IDE contrato 100+, Sala observación 100+) have no covering tests — blocked on DB availability. These are documented incomplete tasks.

**SUGGESTION**:
1. Update spec `specs/motor-reglas/spec.md` R17: change `~80 mappings` → `~800 mappings`, `CatalogInEvaluator` → `IdeContratoSimpleEvaluator`.
2. Consider adding a `USE_RULE_ENGINE` env-var override in `is_rule_engine_enabled()` for testing/rollback scenarios, even if default remains True.
3. When DB is available, complete the 4 pending tasks (T-2.5, T-3.3, T-3.6, T-4.7) for full snapshot parity.

## Verdict
**PASS WITH WARNINGS**

21/25 tasks complete, 461/461 tests passing, 20/23 spec scenarios compliant. All code implementation matches the design. 3 untested scenarios and 4 incomplete tasks are documented DB-dependent blockers outside this change's scope.
