# Delta para motor-reglas — limpiar-legacy-engine

## ADDED Requirements

### R20: RevisionCantidadUrgenciasEvaluator

The engine MUST provide `RevisionCantidadUrgenciasEvaluator` (operator: `revision_cantidad_urgencias_check`) matching `detect_revision_cantidad_urgencias` legacy logic. Row-level check: cantidad exceeds threshold based on code type cascade. Rule DB entry: `revision_cantidad_urgencias_valido`.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| General excess | tipo_factura="Urgencias", cantidad=3, no exceptions | evaluate row | MATCH |
| Exempt code | codigo in `CODIGOS_REVISION_CANTIDAD_EXENTOS` | evaluate | NO_MATCH |
| Specific limit OK | codigo in `CODIGOS_LIMITE_ESPECIFICO` with cantidad <= limit | evaluate | NO_MATCH |
| 02+Lab=No excess | codigo_tipo_proc="02", laboratorio="No", cantidad=3 | evaluate | MATCH |
| 02+Lab=No OK | same, cantidad=2 | evaluate | NO_MATCH |
| 09/12 excess | codigo_tipo_proc in `CODIGOS_TIPO_PROC_09_12`, cantidad=21 | evaluate | MATCH |
| 09/12 OK | same, cantidad=20 | evaluate | NO_MATCH |
| V03AN0101 exempt | codigo=V03AN0101, any cantidad | evaluate | NO_MATCH |
| Non-Urgencias | tipo_factura="Consultas" | evaluate | SKIP |

### R21: CupsEquivalentesTransversalEvaluator

The engine MUST provide `CupsEquivalentesTransversalEvaluator` (operator: `cups_equiv_transversal_check`). Returns the equivalent CUPS code when row's `codigo` matches `CODIGOS_CUPS_EQUIVALENTES` mapping. Rule DB entry: `cups_equivalentes_transversal`.

| Scenario | GIVEN | WHEN | THEN |
|----------|-------|------|------|
| Equivalent found | codigo="906317" | evaluate | MATCH, returns "1906317" |
| Equivalent found (VIH) | codigo="906249" | evaluate | MATCH, returns "906249PR" |
| No equivalent | codigo="890201" | evaluate | NO_MATCH |
| Missing column | indices["codigo"] is None | evaluate | NO_MATCH (logged) |

## MODIFIED Requirements

### R6: Legacy Pipeline Wrapper — Pure-Legacy Toggle

(Previously: 35 migrated detectors use engine toggle; 9 remain pure legacy)
The `RuleBasedDetector` wrapper SHALL NOT cover the 9 pure-legacy detectors. Instead, the `detect_all.py` orchestrators MUST wrap each of the 9 with `if is_rule_engine_enabled():` — same pattern as already-migrated detectors. When the flag is `true`, the engine variant runs; when `false`, the legacy function runs unconditionally.

| Domain | File | Detector | Current | Required |
|--------|------|----------|---------|----------|
| urgencias | `urgencias/detect_all.py:122` | `decimales` | No toggle | Add `if is_rule_engine_enabled()` |
| equipos_basicos | `equipos_basicos/detect_all.py:72` | `decimales` | No toggle | Add `if is_rule_engine_enabled()` |
| equipos_basicos | `equipos_basicos/detect_all.py:87-89` | `ruta_duplicada` | No toggle | Add `if is_rule_engine_enabled()` |
| equipos_basicos | `equipos_basicos/detect_all.py:128-137` | `cantidades_anomalas` | No toggle | Add `if is_rule_engine_enabled()` |
| equipos_basicos | `equipos_basicos/detect_all.py:169-171` | `ide_contrato` | No toggle | Add `if is_rule_engine_enabled()` |
| hospitalizacion | `hospitalizacion/detect_all.py:113` | `ide_contrato` | No toggle | Add `if is_rule_engine_enabled()` |
| hospitalizacion | `hospitalizacion/detect_all.py:255` | `profesionales` | No toggle | Add `if is_rule_engine_enabled()` |
| urgencias | `urgencias/detect_all.py:289` | `revision_cantidad` | No toggle | Add `if is_rule_engine_enabled()` |
| unified_processor | `unified_processor.py:269` | `cups_equivalentes_transversal` | No toggle | Add `if is_rule_engine_enabled()` |

### R7: Feature Flag Rollback — Else Clauses

(Previously: migrated variables lack `else: var = []` fallback)

Six variables that receive engine results in `detect_all.py` MUST have an `else: var = []` clause. When `is_rule_engine_enabled()` is `False`, the variable SHALL be initialized to an empty list to avoid `NameError`.

| Domain | Variable | File |
|--------|----------|------|
| equipos_basicos | `doble_tipo` | `equipos_basicos/detect_all.py:78` |
| equipos_basicos | `centro_costo` | `equipos_basicos/detect_all.py:193` |
| hospitalizacion | `decimales` | `hospitalizacion/detect_all.py` (variable after `if`) |
| hospitalizacion | `tipo_identificacion_edad` | `hospitalizacion/detect_all.py` |
| hospitalizacion | `cantidades_hospitalizacion` | `hospitalizacion/detect_all.py` |
| hospitalizacion | `cantidades_soat_hospitalizacion` | `hospitalizacion/detect_all.py` |

## REMOVED Requirements

None.

---

## Acceptance Criteria

- [ ] `RevisionCantidadUrgenciasEvaluator` output matches `detect_revision_cantidad_urgencias` for all 9 scenarios
- [ ] `CupsEquivalentesTransversalEvaluator` output matches `detect_cups_equivalentes_transversal` for all 4 scenarios
- [ ] 9 pure-legacy detectors wrapped with `if is_rule_engine_enabled():` — snapshot identical when flag=true
- [ ] 6 `else: var = []` clauses added — no NameError when `is_rule_engine_enabled()` returns false
- [ ] `USE_RULE_ENGINE=false` → all 9 detectors run legacy code; `true` → engine path
