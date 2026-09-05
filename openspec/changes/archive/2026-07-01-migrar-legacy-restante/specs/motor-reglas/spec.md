# Delta for motor-reglas

Extiende R12 (hours_diff como agregación group-level) y R13 (GroupEvaluator con `compute_horas`, `collect_set`, `set_contains_all`, `set_intersects`). Agrega 3 reemplazos engine para detectores legacy.

---

## MODIFIED Requirements

### R12: Hours Diff Evaluator (Group-Level)

MUST provide `hours_diff(f1,f2)` → float. Como group aggregation, opera sobre primera fila del grupo (estancia invariant por invoice). (Previo: standalone only)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Mismo día | f1="2024-01-15 08:00", f2="2024-01-15 14:30" | hours_diff | 6.5 |
| Multi-day | f1="2024-01-15", f2="2024-01-17" | hours_diff | 48.0 |
| Orden inverso | f1 > f2 | hours_diff | valor absoluto |
| **Group agg** | agg_configs target="estancia_horas" | compute_horas(primera fila) | diff correcta |

### R13: Group-By Evaluator (Extended)

SHALL provide `GroupEvaluator` que agrupa por key field y evalúa reglas por grupo. Soporta: `compute_horas(f1,f2)` → `\|f1-f2\|` en horas, `collect_set(field)` → set de valores, `set_contains_all(expr,vals)` y `set_intersects(expr,vals)`. (Previo: solo distinct_count)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Distinct count | F001 tipos=["02","03","02"] | distinct_count gt(1) | MATCH |
| compute_horas | fec_factura=A, fecha_cierre=A+24h | primera fila agg | 24.0 |
| set_contains_all | codigos=["A","B"], required=["A","B"] | evaluate | MATCH |
| set_intersects | codigos=["A","X"], prohibited=["X"] | evaluate | MATCH |

---

## ADDED Requirements

### R16: Hospitalización Codes — Group Rule

Reemplaza `detect_hospitalizacion_codes()`: (a) códigos obligatorios faltantes por estancia+tarifario, (b) códigos prohibidos. `group_by=numero_factura`, `filter=Hospitalización`, `collect_set` + set ops.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Obligatorio falta | factura >48h sin código quirúrgico | rule a | MATCH |
| Prohibido presente | código prohibido en grupo | rule b | MATCH |
| Sin problemas | todos los códigos OK | ambas reglas | NO_MATCH |

### R17: IDE Contrato Intramural — Row-Level Evaluators

Reemplaza `detect_ide_contrato_intramural()`: (a) ~800 mappings desde DB catalogos key `ide_simple_rules` via IdeContratoSimpleEvaluator, (b) pym_rutas_dx via PymRutasDxEvaluator, (c) solo_laboratorio_envio (pre-scan cacheado). Evaluadores row-level, no group.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| IDE match | entidad+regimen en catalogos | IdeContratoSimpleEvaluator | MATCH |
| Solo lab | solo códigos LAB sin clínicos | PymRutasDxEvaluator pre-scan | MATCH |
| Sin mapping | no existe en catalogos | check | NO_MATCH |

### R18: Sala Observación — Group Rules

Reemplaza `detect_sala_observacion()` con ~8 group rules: estancia, ESS prohibidos, 890601H, 05DSB01, obligatorios, SOAT. `group_by=numero_factura`, `filter=Hospitalización`. Row-level evaluator se mantiene para estancia (rule #1).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Estancia >48h | factura >48h | group rule | MATCH |
| ESS prohibido | código ESS presente | group rule | MATCH |
| 890601H falta | código obligatorio ausente | group rule | MATCH |
| Todo OK | todas las validaciones pasan | todas las reglas | NO_MATCH |

### R19: Snapshot Testing Contract

Each replacement MUST output idéntico al legacy en ≥100 facturas (variantes cubiertas). Comparación campo-a-campo. Diferencias → FAIL.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Hospitalización | 100+ facturas mixtas | engine vs legacy | output idéntico |
| IDE contrato | 100+ facturas | engine vs legacy | output idéntico |
| Sala observación | 100+ facturas | engine vs legacy | output idéntico |

---

## Acceptance Criteria

- [ ] `compute_horas` = `_format_estancia` legacy en 100+ facturas
- [ ] Cada reemplazo engine detecta mismos problemas que legacy (snapshot pass)
- [ ] Detector flags `USE_RULE_ENGINE=false` restauran legacy
