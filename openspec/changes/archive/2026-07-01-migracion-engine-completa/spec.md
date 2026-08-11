# Spec: Migración completa al Rule Engine

**Change**: `migracion-engine-completa`
**Topic key**: `sdd/migracion-engine-completa/spec`
**Based on**: `openspec/specs/motor-reglas/spec.md` (engine spec)

---

## Fase 1: Transversales para áreas sin engine

Agregar toggle `if is_rule_engine_enabled()` en los 5 detect_all.py para los 10 detectores transversales que ya existen como reglas en BD.

### FR-1.1: Toggle en hospitalización

The system MUST route 10 transversal detectors to the Rule Engine when `USE_RULE_ENGINE=true` in `app/services/hospitalizacion/detect_all.py`:
`detect_decimales`, `detect_tipo_documento_edad`, `detect_tipo_identificacion_entidad`, `detect_codigo_entidad_vs_entidad_afiliacion`, `detect_tipo_usuario`, `detect_copago_entidad_urgencias`, `detect_cups_sin_contrato`, `detect_cantidades_hospitalizacion`, `detect_cantidades_soat_hospitalizacion`, `detect_hospitalizacion_codes`.

Engine rules to use: `valores_decimales`, `tipo_documento_edad_*`, `tipo_id_requiere_entidad_86000` + `entidad_86000_requiere_as_ms`, `codigo_entidad`, `tipo_usuario_valido`, `copago_entidad_valido`, `cups_contratado`.

### FR-1.2: Toggle en intramural

MUST add toggle for: `detect_decimales`, `detect_tipo_documento_edad`, `detect_tipo_identificacion_entidad`, `detect_codigo_entidad_vs_entidad_afiliacion`, `detect_tipo_usuario`, `detect_copago_entidad_urgencias`, `detect_cups_sin_contrato`.

### FR-1.3: Toggle en ambulatoria

MUST add toggle for: same 7 transversales as FR-1.2. No specific detectors.

### FR-1.4: Toggle en farmacia

MUST add toggle for: same 7 transversales + `detect_duplicados_farmacia_farmacia`.

### FR-1.5: Toggle en extramural

MUST add toggle for: same 7 transversales as FR-1.3. No specific detectors.

### NFR-1.1: Output identidad

Output from engine MUST be byte-identical to legacy output for the same input data. Each detector migration SHALL include snapshot comparison.

### Scenario 1.1: Hospitalización sin errores → output vacío

- GIVEN an Excel sheet with Hospitalización data that has NO decimal errors, NO tipo_doc/edad issues, NO entity mismatches
- WHEN `detect_all_problems_hospitalizacion` runs with `USE_RULE_ENGINE=true`
- THEN each transversal detector returns `[]`
- AND `resultado["problemas"]["decimales"]` is `[]`, same for `tipo_identificacion_edad`, `codigo_entidad_vs_afiliacion`, `tipo_usuario`

### Scenario 1.2: Hospitalización con decimales → mismos errores

- GIVEN an Excel with Hospitalización rows: valor_unitario=150.50, 200.75 (correct), and 300.456 (has 3 decimals)
- WHEN engine runs
- THEN `resultado["problemas"]["decimales"]` MUST contain 1 entry: `{"factura": "F001", "problema": "El valor 300.456 tiene más de 2 decimales"}`
- AND this MUST match legacy output exactly

### Scenario 1.3: Edad inválida en intramural

- GIVEN Intramural row: fecha_nacimiento="2015-06-30", fec_factura="2024-06-30" (age=9), rule expects tipo_documento="TI"
- WHEN engine runs
- THEN `resultado["problemas"]["tipo_identificacion_edad"]` MUST include entry for F001

### Scenario 1.4: Columna faltante → gracefully empty

- GIVEN an Excel sheet missing `Vlr. Copago` column entirely
- WHEN engine runs for ambulatoria
- THEN `copago_entidad_valido` engine rule SHALL return `[]` — NOT crash

### Scenario 1.5: Farmacia sin transversales toggle (regression guard)

- GIVEN `USE_RULE_ENGINE=true`
- AND same Excel processed with `USE_RULE_ENGINE=false`
- THEN `resultado["problemas"]["decimales"]` + `["tipo_identificacion_edad"]` + `["tipo_usuario"]` + `["copago_entidad"]` SHALL be identical in both runs

### AC-1.1: Snapshot matching

- [ ] 5 detect_all.py have toggle for transversales
- [ ] `python -c "from app.constants.base import is_rule_engine_enabled; print(is_rule_engine_enabled())"` returns True/False matching env var
- [ ] Snapshot test: pandas `assert_frame_equal` on output dicts from engine vs legacy for 3 representative Excels per area

---

## Fase 2: Farmacia específico + Ambulatoria/Extramural

### FR-2.1: duplicados_farmacia_farmacia → engine

The system MUST route `detect_duplicados_farmacia_farmacia` (Farmacia-only) to the Rule Engine when `USE_RULE_ENGINE=true`. This detector groups by factura within tipo_factura="Farmacia", then flags facturas where every (codigo, cantidad) pair appears ≥2 times.

**Engine mapping**: use `GroupEvaluator` with `group_by(factura, distinct_count((codigo, cantidad)), all_values_match(threshold=1))`.

### FR-2.2: Ambulatoria/Extramural — sin cambio funcional

Both areas have NO specific detectors. Fase 1 toggle already covers them. Fase 2 adds no new rules — just verifies the toggle is active and testable.

### Scenario 2.1: Farmacia con duplicidad total

- GIVEN Farmacia data: F001 has rows [(890201, 2), (890201, 2), (750101, 1), (750101, 1)]
- WHEN engine runs with `USE_RULE_ENGINE=true`
- THEN F001 flagged as "Duplicados Farmacia"
- AND output matches legacy

### Scenario 2.2: Farmacia con mezcla (duplicados + únicos)

- GIVEN Farmacia data: F002 has rows [(890201, 2), (890201, 2), (750101, 1)] — pair (750101,1) appears only once
- WHEN engine runs
- THEN F002 is NOT flagged
- AND output matches legacy

### Scenario 2.3: Missing tipo_factura_descripcion column

- GIVEN Excel without `tipo_factura_descripcion` column
- WHEN engine runs for Farmacia
- THEN `duplicados_farmacia` detector returns `[]` gracefully

### AC-2.1: Farmacia duplicados matching

- [ ] Farmacia toggle includes `duplicados_farmacia` → GroupEvaluator
- [ ] Snapshot test: 3 Excels with varied duplicados patterns produce identical engine vs legacy output
- [ ] Ambulatoria/Extramural snapshot: output identical to legacy (no new rules)

---

## Fase 3: Hospitalización específicos

### FR-3.1: centro_costo_hospitalizacion → engine

The system MUST route `detect_centro_costo_hospitalizacion` (Hospitalización area) to engine using `centro_costo_check` evaluator with Hospitalización-specific `centros_validos`.

**Engine mapping**: `centro_costo_check` evaluator already implements REGLA1-9 + REVERSE rules. The Hospitalización variant uses `HOSPITALIZACION_CENTROS_COSTO_VALIDOS` as valid centers parameter.

### FR-3.2: ide_contrato → ide_contrato_urgencias_valido

Reuse existing `ide_contrato_urgencias_valido` rule — Hospitalización already calls `detect_ide_contrato_urgencias`.

### FR-3.3: cantidades_hospitalizacion → engine

Simple threshold rule: if `Cantidad > 8` for Hospitalización, flag.

**Engine mapping**: `gt(Cantidad, 8)` condition.

### FR-3.4: cantidades_soat_hospitalizacion → engine

If tarifario=SOAT and `Cantidad > 2`, flag.

**Engine mapping**: `AND(eq(tarifario, "SOAT"), gt(Cantidad, 2))`.

### FR-3.5: hospitalizacion_codes → engine (COMPLEX)

**Lógica**: For each Hospitalización factura, calculate estancia (hours between fec_factura and fecha_cierre). Then:
- If tarifario = SOAT: verify SOAT mandatory codes present AND prohibited codes absent
- If estancia > 24h: verify mandatory codes (CODIGOS_HOSPITALIZACION_OBLIGATORIOS = full set)
- If estancia <= 24h: verify mandatory codes restricted set ({"890601H", "129B02"})
- Always: verify prohibited codes absent

**Engine mapping**: GroupEvaluator (group by factura) + `collect_set(codigo)` aggregation + `set_contains_all` evaluator for mandatory codes + `set_intersects` evaluator for prohibited codes. Conditional estancia branches modeled as 2 rule configs with different `filter_value` in group-by.

### Scenario 3.1: Hospitalización estancia >24h con códigos obligatorios

- GIVEN Hospitalización factura F001 with fec_factura="2024-03-01 08:00", fecha_cierre="2024-03-02 10:00" (estancia=26h)
- AND codes present: 890601H, 129B02, 5DSB01 (all mandatory present)
- WHEN engine runs
- THEN no error for F001 on missing codes

### Scenario 3.2: Hospitalización estancia >24h sin código obligatorio

- GIVEN same factura but 890601H missing from codes
- WHEN engine runs
- THEN error: "Hospitalización (>24h) debe tener: 890601H (faltan: 890601H)"
- AND legacy output matches exactly

### Scenario 3.3: Hospitalización estancia <=24h con códigos restringidos

- GIVEN F002 with fec_factura="2024-03-01 08:00", fecha_cierre="2024-03-01 14:00" (estancia=6h)
- AND codes present: 890601H, 129B02
- WHEN engine runs
- THEN no error for F002 (890601H is not mandatory for <=24h, only 890601H and 129B02 are)

### Scenario 3.4: Hospitalización SOAT con código prohibido

- GIVEN tarifario="SOAT", codes include a CODIGOS_SOAT_HOSPITALIZACION_PROHIBIDOS member
- WHEN engine runs
- THEN error: "SOAT Hospitalización no puede tener: {prohibidos}"

### Scenario 3.5: Hospitalización con código prohibido

- GIVEN codigo present in CODIGOS_HOSPITALIZACION_PROHIBIDOS set
- WHEN engine runs
- THEN error: "Hospitalización no puede tener: {prohibidos}"

### Scenario 3.6: Fechas inválidas → skip estancia validation

- GIVEN fec_factura or fecha_cierre is None / unparseable
- WHEN engine runs for that factura
- THEN the factura is excluded from code validation (NOT crash)
- AND engine handles gracefully via `hours_diff` provider returning None

### AC-3.1: Hospitalización específicos matching

- [ ] centro_costo_hospitalizacion → centro_costo_check evaluator with Hospitalización centers
- [ ] ide_contrato → ide_contrato_urgencias_valido rule
- [ ] cantidades_hospitalizacion (Cantidad > 8) → engine gt condition
- [ ] cantidades_soat_hospitalizacion (SOAT + Cantidad > 2) → AND condition
- [ ] hospitalizacion_codes → GroupEvaluator + set_contains_all/set_intersects with 2 rule configs (estancia >24h vs <=24h)
- [ ] Snapshot: all 5 detectors output identical engine vs legacy for 3 Excels

---

## Fase 4: Intramural parte 1 — centro_costo, IDE, revision_cantidad

### FR-4.1: centro_costo_intramural → engine (COMPLEX)

The system MUST route `detect_centro_costo_intramural` to engine. This requires 5 additional rule types beyond the common `centro_costo_check` evaluator:

| Rule | Condition | Value | Action |
|------|-----------|-------|--------|
| REGLA3-INTRAMURAL | codigo in CODIGOS_PYP_URGENCIAS | centro_costo not in CENTROS_COSTO_PYP_INTRAMURAL | Centro→SERVICIOS AMBULATORIOS- PyP |
| REGLA6 | tipo=05 + codigo not in CODIGOS_EXCLUIDOS_VACUNACION + not PyP | centro_costo != CENTRO_COSTO_SALUD_PUBLICA | Centro→SALUD PUBLICA |
| REVERSE6 | centro_costo == CENTRO_COSTO_SALUD_PUBLICA | tipo != 05 OR codigo in excluidos | Error: necesita tipo=05 |
| REGLA7 | tipo in {"03","04"} + codigo not in CODIGOS_EXCEPTUADOS_AMBULATORIO | centro_costo != CENTRO_COSTO_AMBULATORIO | Centro→SERVICIOS AMBULATORIOS |
| REVERSE7 | centro_costo == CENTRO_COSTO_AMBULATORIO | tipo not in {"03","04"} | Error: necesita tipo 03/04 |
| REGLA10 | tipo in {"02","05"} + lab="SI" | centro_costo not in CENTROS_COSTO_LABORATORIO_VALIDOS | Centro→LABORATORIO CLINICO |
| REVERSE10 | centro_costo in CENTROS_COSTO_LABORATORIO_VALIDOS | tipo not in {"02","05"} OR (not exceptuado AND lab!="SI") | Error: necesita tipo 02/05 + Lab=Si |
| REGLA_RESPONSABLE_URGENCIAS | responsable in FACTURADORES_URGENCIAS + tipo in {"01","04"} + codigo not in CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS | centro_costo not in {URGENCIAS, HOSPITALIZACION} | Centro→URGENCIAS o HOSPITALIZACIÓN |

**Engine mapping**: Extend `centro_costo_check` evaluator or create `CentroCostoIntramuralEvaluator` that inherits from it and adds the 5 intramural-specific rules. Each rule SHALL be parameterized via condition with `centros_validos` specific to Intramural.

### FR-4.2: ide_contrato_intramural → engine

Similar to `ide_contrato_urgencias` but with Intramural-specific entity→IDE mapping. Requires a new BD rule `ide_contrato_intramural_valido` with Intramural contract data.

### FR-4.3: revision_cantidad_intramural → engine

Cascade threshold rule:
- tipo=02 + Lab=No → Cantidad > 2 → flag
- tipo=03 or 04 → Cantidad > 12 → flag
- Any other → Cantidad > 1 → flag

**Engine mapping**: `AND(eq(tipo, "02"), eq(lab, "No"), gt(cantidad, 2))` and similar OR chain.

### Scenario 4.1: Intramural REGLA3-INTRAMURAL

- GIVEN Intramural row: codigo in CODIGOS_PYP_URGENCIAS, centro_costo="HOSPITALIZACION - ESTANCIA GENERAL"
- WHEN engine runs
- THEN error: centro_deberia should be one of CENTROS_COSTO_PYP_INTRAMURAL
- AND output matches legacy

### Scenario 4.2: Intramural REGLA6 — vacunación

- GIVEN tipo=05, codigo="906249" (not in excluded, not PyP), centro_costo="FARMACIA"
- WHEN engine runs
- THEN error: centro_deberia should be SALUD PUBLICA-VACUNACION

### Scenario 4.3: Intramural REGLA_RESPONSABLE_URGENCIAS

- GIVEN responsable_cierra in FACTURADORES_URGENCIAS, tipo="01", codigo not in exceptuados, centro_costo="FARMACIA"
- WHEN engine runs
- THEN error: centro_deberia should be "URGENCIAS o HOSPITALIZACION - ESTANCIA GENERAL"
- AND prioridad=2

### Scenario 4.4: Revision cantidad — tipo 02 + Lab=No

- GIVEN tipo_procedimiento="02", laboratorio="No", cantidad=5
- WHEN engine runs
- THEN row flagged as "⚠️ Revisión Necesaria"

### Scenario 4.5: Revision cantidad — bajo umbral

- GIVEN tipo_procedimiento="04", cantidad=8 (umbral=12)
- WHEN engine runs
- THEN row NOT flagged

### AC-4.1: Intramural parte 1 matching

- [ ] centro_costo_intramural → engine with 8 intramural-specific rule types
- [ ] ide_contrato_intramural → new BD rule `ide_contrato_intramural_valido`
- [ ] revision_cantidad_intramural → OR cascade of AND conditions
- [ ] Snapshot: all 3 detectors output identical engine vs legacy for 5 Excels (covering all 8 CC rules)
- [ ] Prioridad CC filter still runs as post-processing

---

## Fase 5: Intramural parte 2 — bacteriologas_cronograma, duplicado_id_codigo

### FR-5.1: duplicado_id_codigo → GroupEvaluator

The system MUST route `detect_duplicado_id_codigo` to engine using `GroupEvaluator`. Logic:
- Filter: tipo_procedimiento in ("02","05"), where tipo="02" requires laboratorio="SI"
- Exclude: responsable_cierra in FACTURADORES_URGENCIAS
- Group by: (identificacion, codigo, dx_principal)
- Threshold: tipo="05" → umbral=2, tipo="02"+Lab="Si" → umbral=4
- Exentos: código 993505 for tipo="05" is exempt

**Engine mapping**: `GroupEvaluator` with `group_by((identificacion, codigo, dx), count(*) >= umbral)` + filter conditions for tipo/lab + exception for FACTURADORES_URGENCIAS.

### Scenario 5.1: Duplicado ID+Código básico

- GIVEN Intramural rows: 3 rows with same (identificacion="12345", codigo="890201", dx=""), tipo="02", lab="SI"
- WHEN engine runs
- THEN error: facturas list has the 3 facturas, cantidad_repeticiones=3, umbral=4 → NOT flagged (below threshold)

### Scenario 5.2: Duplicado ID+Código con umbral excedido

- GIVEN 5 rows with same (identificacion="12345", codigo="890201", dx=""), tipo="02", lab="SI"
- WHEN engine runs
- THEN error flagged with cantidad_repeticiones=5

### Scenario 5.3: Duplicado tipo 05 con código exento 993505

- GIVEN 3 rows with tipo="05", codigo="993505", same ident
- WHEN engine runs
- THEN NOT flagged (CODIGOS_EXENTOS_05 bypass)

### Scenario 5.4: Facturador Urgencias excluido

- GIVEN rows with responsable_cierra in FACTURADORES_URGENCIAS
- WHEN engine runs
- THEN those rows excluded from duplicate detection
- AND count matches legacy (total_excluidas logged)

### FR-5.2: bacteriologas_cronograma → NEW CronogramaCheckEvaluator

The system MUST create a **new custom evaluator** `CronogramaCheckEvaluator` (operator: `"cronograma_check"`) that:
1. Receives `row_value`: codigo_profesional
2. Uses context to access: tipo_procedimiento, laboratorio, codigo, responsable_cierra, fec_factura
3. Calls `get_turno_del_dia()` from `cronograma_bacteriologas_service` internally
4. Implements all exception logic: PROFESIONALES_EXCEPTUADOS_CRONOGRAMA, FACTURADORES_URGENCIAS bypass, Chapuel→PYM, Tapia/Ordoñez→CE
5. Returns True if valid (professional is scheduled), False if error

### Scenario 5.5: Bacterióloga en cronograma → OK

- GIVEN Intramural row: tipo="02", lab="SI", codigo_profesional="03374" (MOLINA, BACTERIOLOGA)
- AND cronograma has her scheduled for the day with sigla "CE/PYM"
- AND default responsable (CE/PYM filter)
- WHEN CronogramaCheckEvaluator runs
- THEN no error

### Scenario 5.6: Bacterióloga NO en cronograma → error

- GIVEN same as 5.5 but cronograma does NOT have her scheduled
- WHEN evaluator runs
- THEN error: "no está en el cronograma del día"

### Scenario 5.7: MADROÑERO (02217) bypassa cronograma

- GIVEN codigo_profesional="02217" (in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA)
- AND not in cronograma del día
- WHEN evaluator runs
- THEN no error (bypasses cronograma validation)

### Scenario 5.8: Chapuel → solo PYM

- GIVEN responsable_cierra="CHAPUEL CASANOVA ANGIE TATIANA"
- AND cronograma has bacterióloga with sigla="CE" only
- WHEN evaluator runs
- THEN error: "no está en el cronograma del día"
- (Should have been PYM)

### Scenario 5.9: Tapia → solo CE

- GIVEN responsable_cierra="TAPIA PERDOMO ANYI CATALEYA"
- AND cronograma has bacterióloga with sigla="PYM" only
- WHEN evaluator runs
- THEN error: "no está en el cronograma del día"

### Scenario 5.10: Facturador Urgencias bypass

- GIVEN responsable_cierra in FACTURADORES_URGENCIAS
- AND codigo_profesional in PROFESIONALES_URGENCIAS with tipo="BACTERIOLOGA"
- WHEN evaluator runs
- THEN no error (bypasses cronograma entirely)

### AC-5.1: Intramural parte 2 matching

- [ ] `duplicado_id_codigo` → GroupEvaluator with filters for tipo/lab + exception for FACTURADORES_URGENCIAS + CODIGOS_EXENTOS_05
- [ ] CronogramaCheckEvaluator created with operator="cronograma_check"
- [ ] All 5 exception branches implemented (excepted profs, facturadores, Chapuel, Tapia/Ordoñez, default)
- [ ] Snapshot: both detectors output identical engine vs legacy for 5 Excels covering all branches
- [ ] Decision: Opción A (custom evaluador) confirmed before apply

---

## Fase 6: Post-filtros legacy y limpieza

### FR-6.1: Prioridad CC — post-procesamiento

The priority filter (when multiple CC rules match same factura+codigo, keep only priority=1) SHALL remain as post-processing Python. It is NOT a detection rule — it's a deduplication filter on detection results.

**Criteria for decision**: The filter operates on the OUTPUT of detection (list of problems), not on input rows. Engine rules produce results with priorities. The filter selects the lowest priority number. This is classic post-processing.

### FR-6.2: Excepción 990203 — ExceptionHandler

The odontología exception for código 990203 (allows multi-tipo) SHALL be modeled as an `Exception` entity in the engine. The exception SHALL be scoped to domain="odontología" and rule="doble_tipo_procedimiento", with `tipo_excepcion="suspension"`.

### FR-6.3: Excepción PyP — ExceptionHandler

The odontología exception for 3 facturas + código exempto SHALL be modeled as an `Exception` entity. The exception SHALL be scoped to domain="odontología" and rule="ruta_duplicada", with `tipo_excepcion="modification"` that overrides the threshold.

### FR-6.4: is_rule_engine_enabled() → return True

After all 5 phases verified in production for at least 1 week:
1. Change `is_rule_engine_enabled()` to `return True` unconditionally
2. Mark legacy detector files as `@deprecated` via docstring
3. Remove `else` branches from all `detect_all.py` files
4. Legacy detector files moved to `archive/` or left as dead code with deprecation warning

### FR-6.5: Sala observación — revisión

`detect_sala_observacion` already has `SalaObservacionEvaluator`. Verify it's registered in the engine and called when engine is enabled. If not, add it.

### Scenario 6.1: engine always true

- GIVEN all previous phases verified
- WHEN `is_rule_engine_enabled()` is changed to `return True`
- THEN all detect_all.py run engine path exclusively
- AND `USE_RULE_ENGINE=false` env var is ignored (no rollback possible — legacy code removed)
- AND the rollback documented in proposal becomes "deploy previous version"

### Scenario 6.2: Legacy code deprecated

- GIVEN Fase 6 completed
- WHEN developer runs legacy detector file
- THEN first line of docstring reads `@deprecated — use engine rule {rule_name} instead`

### AC-6.1: Post-filtros + limpieza

- [ ] Prioridad CC stays as post-processing Python (documented decision)
- [ ] Excepción 990203 → ExceptionHandler entity in BD
- [ ] Excepción PyP → ExceptionHandler entity in BD
- [ ] `is_rule_engine_enabled()` → `return True`
- [ ] All `else` legacy branches removed from detect_all.py
- [ ] All legacy detector files marked `@deprecated`
- [ ] Sala observación evaluator verified in engine (registered or added)
- [ ] Test suite passes: `pytest tests/engine/ tests/services/`

---

## Matriz de trazabilidad: Detector legacy → Regla engine → Fase → AC

| Detector legacy | Regla engine / Evaluador | Fase | AC |
|---|---|---|---|
| `detect_decimales` | `valores_decimales` | F1 | AC-1.1 |
| `detect_tipo_documento_edad` | `tipo_documento_edad_*` (7 reglas) | F1 | AC-1.1 |
| `detect_tipo_identificacion_entidad` | `tipo_id_requiere_entidad_86000` + `entidad_86000_requiere_as_ms` | F1 | AC-1.1 |
| `detect_codigo_entidad_vs_entidad_afiliacion` | `codigo_entidad` + `CodigoEntidadCoincideEvaluator` | F1 | AC-1.1 |
| `detect_tipo_usuario` | `tipo_usuario_valido` | F1 | AC-1.1 |
| `detect_copago_entidad_urgencias` | `copago_entidad_valido` | F1, F3 | AC-1.1, AC-3.1 |
| `detect_cups_sin_contrato` | `cups_contratado` (CupsContratadoEvaluator) | F1 | AC-1.1 |
| `detect_duplicados_farmacia_farmacia` | `GroupEvaluator` + `all_values_match` | F2 | AC-2.1 |
| `detect_centro_costo_hospitalizacion` | `centro_costo_check` (Hospitalización centros válidos) | F3 | AC-3.1 |
| `detect_ide_contrato_urgencias` (en Hosp) | `ide_contrato_urgencias_valido` | F3 | AC-3.1 |
| `detect_cantidades_hospitalizacion` | `gt(Cantidad, 8)` | F3 | AC-3.1 |
| `detect_cantidades_soat_hospitalizacion` | `AND(eq(tarifario, "SOAT"), gt(Cantidad, 2))` | F3 | AC-3.1 |
| `detect_hospitalizacion_codes` | `GroupEvaluator` + `set_contains_all` + `set_intersects` (2 configs estancia) | F3 | AC-3.1 |
| `detect_centro_costo_intramural` | `CentroCostoCheckEvaluator` extendido (REGLA3-INTRAMURAL + 6/7/10/REVERSE + RESPONSABLE) | F4 | AC-4.1 |
| `detect_ide_contrato_intramural` | `ide_contrato_intramural_valido` (nueva regla BD) | F4 | AC-4.1 |
| `detect_revision_cantidad_intramural` | OR cascade de AND conditions (3 thresholds) | F4 | AC-4.1 |
| `detect_duplicado_id_codigo` | `GroupEvaluator` + count + exception | F5 | AC-5.1 |
| `detect_bacteriologas_cronograma` | **Nuevo** `CronogramaCheckEvaluator` | F5 | AC-5.1 |
| Post-filtro prioridad CC | Post-procesamiento Python | F6 | AC-6.1 |
| Excepción 990203 | `ExceptionHandler` (suspensión) | F6 | AC-6.1 |
| Excepción PyP | `ExceptionHandler` (modificación threshold) | F6 | AC-6.1 |

---

## Detección de regresión — plan de snapshot testing

### Metodología

Cada fase SHALL ejecutar el mismo Excel de entrada con `USE_RULE_ENGINE=true` y `USE_RULE_ENGINE=false`, y comparar los outputs de los detectores migrados.

```python
def assert_snapshot_match(excel_path: str, area: str, detectors: list[str]):
    """Compare engine vs legacy output for given area and detectors."""
    with use_rule_engine(True):
        engine_result = process_excel(excel_path, area)
    with use_rule_engine(False):
        legacy_result = process_excel(excel_path, area)
    
    for detector in detectors:
        assert engine_result["problemas"][detector] == legacy_result["problemas"][detector], \
            f"Detector mismatch: {detector}"
```

### Excels de prueba requeridos

| Escenario | Contenido |
|-----------|-----------|
| Normal sin errores | 50-100 facturas, todas correctas |
| Con errores mixtos | 20-50 facturas con 2-5 errores de cada tipo |
| Casos borde | 5-10 facturas con valores límite, fechas inválidas, nulos |
| Todos los tipos de área | 1 Excel por cada área (8 archivos) |
| Intramural complejo | 30 facturas cubriendo todas las 12 reglas de CC |
| Bacteriólogas cronograma | 20 facturas con combinaciones de responsable×sigla |
| Hospitalización códigos | 15 facturas con estancias variadas (0-72h) y combinaciones de códigos |

### Criterio de aprobación

- `assert_snapshot_match()` pasa para 100% de los detectores migrados en la fase
- Cada Excel de prueba produce outputs idénticos entre engine y legacy
- Cualquier diferencia detiene el deploy de la fase

---

## Non-Functional Requirements (globales)

### NFR-G1: Performance parity

The engine SHALL NOT be slower than legacy for the same detector on the same data. Acceptable: ≤20% overhead for the first run (DB cache cold). Subsequent runs with warm cache SHALL be ≤5% overhead.

**Verification**: `timeit` comparison for each detector on a 1000-row Excel, averaged over 5 runs.

### NFR-G2: Auditabilidad

Every engine detection SHALL write to `evidence` and `resultado_auditoria` tables when `_PERSIST=True`. This must already be handled by `RuleBasedDetector.detect()` — verify it's working for all migrated detectors.

### NFR-G3: Rollback at phase level

Each phase SHALL be independently toggle-able via `USE_RULE_ENGINE`. If a phase deployed with engine=true causes issues, setting USE_RULE_ENGINE=false MUST revert ALL detectors to legacy.

### NFR-G4: No regression on UI/export

Engine migration SHALL NOT change:
- Excel output format (sheets, columns, formatting)
- HTTP response format (`{"status", "data", "errors"}`)
- Error group names in `resultado["problemas"]`
