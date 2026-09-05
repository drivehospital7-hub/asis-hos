# Tasks: Migrar detectores legacy restantes

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1050 (320+ add, 730− del) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 3 stacked PRs: infra (F1) → reglas hosp+intramural (F2+F3) → reglas urgencias (F4+F5) |
| Delivery strategy | exception-ok (size:exception aprobado) |
| Chain strategy | size:exception — single PR aceptado |

## Fase 1: Infra — compute_horas aggregation

- [x] 1.1 Agregar `_agg_compute_horas(rows, sheet, indices, field1, field2)` en GroupEvaluator
- [x] 1.2 Registrar `compute_horas` en el dispatch `_build_group_data()`
- [x] 1.3 Unit test `test_agg_compute_horas`
- [x] 1.4 Integration test: GroupEvaluator.evaluate con `gt(estancia_horas,24)`

## Fase 2: Hospitalización — group rules

- [x] 2.1 Crear rule config `hosp_codigos_oblig_mayor24h` — tests + condition tree verificados
- [x] 2.2 Crear rule config `hosp_codigos_oblig_menor24h` — tests + condition tree verificados
- [x] 2.3 Crear rule config `hosp_codigos_prohibidos` — tests + condition tree verificados (+ SOAT variants)
- [x] 2.4 Agregar toggle engine en `hospitalizacion/detect_all.py` con las 3 reglas
- [ ] 2.5 Snapshot test: requiere DB con data real para engine == legacy (pendiente DB migration)

## Fase 3: Intramural — IdeContratoSimple + PymRutasDx + pre-scan

- [x] 3.1 Crear `IdeContratoSimpleEvaluator` (operator: `ide_simple_check`) — pre-load desde dict o DB catalogos
- [x] 3.2 Crear `PymRutasDxEvaluator` (operator: `pym_rutas_dx_check`) — PYM_RUTAS + Dx + pre-scan cache
- [ ] 3.3 DB migration: seed `catalogos` con `key=ide_simple_rules` (~800 rows JSONB) — pendiente
- [x] 3.4 Registrar evaluadores en `EVALUATOR_REGISTRY`, agregar toggle en `intramural/detect_all.py`
- [x] 3.5 Unit test: IdeContratoSimpleEvaluator (13 tests) + PymRutasDxEvaluator (15 tests)
- [ ] 3.6 Snapshot test: requiere DB con data real (pendiente)

## Fase 4: Urgencias — sala_observación group rules

- [x] 4.1 Crear rule config `sala_obs_obligatorios` — tests + condition tree verificados
- [x] 4.2 Crear rule config `sala_obs_ess_129b02` — tests + condition tree verificados
- [x] 4.3 Crear rule config `sala_obs_soat_completo` — tests + condition tree verificados
- [x] 4.4 Crear rule config `sala_obs_soat_prohibido` — tests + condition tree verificados
- [x] 4.5 Crear reglas para 890601H prohibido + 05DSB01 prohibido en entidades no-ESS
- [x] 4.6 Agregar toggle engine en `urgencias/detect_all.py` con 6 group rules
- [ ] 4.7 Integration test: snapshot vs legacy `detect_sala_observacion` (pendiente DB)

## Fase 5: Urgencias — ide_contrato_urgencias con evaluador reutilizado

- [x] 5.1 Reusar `IdeContratoSimpleEvaluator` con mappings de urgencias (key `ide_simple_rules_urgencias`)
- [x] 5.2 Agregar toggle en `urgencias/detect_all.py`
- [x] 5.3 Unit test (9 tests) + evaluador listo para snapshot (pendiente DB)

### Notas
- **DB migration** (T-3.3): pendiente — crear endpoint o script para seed `catalogos` con `IDE_SIMPLE_RULES` como JSONB
- **Snapshot tests** (T-2.5, T-3.6, T-4.7, T-5.3): require DB con data real y archivos Excel de prueba
- **Evaluadores nuevos**: IdeContratoSimpleEvaluator `ide_simple_check`, PymRutasDxEvaluator `pym_rutas_dx_check`
- **Group rules validadas**: 12 condition trees (3 hosp + 6 sala + 3 SOAT variants)
- **Total tests nuevos**: 62 tests (todos verdes)
