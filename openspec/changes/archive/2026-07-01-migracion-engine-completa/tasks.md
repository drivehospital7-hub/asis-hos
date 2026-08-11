# Tasks: migracion-engine-completa

**Based on**: proposal.md → spec.md → design.md  
**Topic key**: `sdd/migracion-engine-completa/tasks`  
**Created**: 2026-06-30  
**Delivery strategy**: `ask-always`  
**Review budget**: 400 lines  
**Chained PRs recommended**: Yes  

---

## Resumen de fases y estimaciones

| Fase | Tareas | Líneas netas | Dependencias | Excede 400ln? |
|------|--------|--------------|--------------|---------------|
| F1 — Transversales sin engine | 7 | ~420 | Ninguna | **Sí** (~420) |
| F2 — Farmacia | 2 | ~70 | F1 (Farmacia toggle) | No |
| F3 — Hospitalización | 4 | ~190 | F1 (Hosp toggle) | No |
| F4 — Intramural parte 1 | 5 | ~290 | F1 (Intra toggle) | No |
| F5 — Intramural parte 2 | 5 | ~300 | F4 | No |
| F6 — Post-filtros + limpieza | 6 | ~85 | F1..F5 | No |
| **Total** | **29** | **~1,355** | — | **Sí** (~1,355) |

---

## Fase 1: Transversales para áreas sin engine

### T-F1.1: ✅ Agregar toggle en hospitalización/detect_all.py

- **Archivos**: `app/services/hospitalizacion/detect_all.py`
- **Descripción**: Agregado `if is_rule_engine_enabled():` para 7 detectores transversales (decimales, tipo_documento_edad x7, tipo_identificacion_entidad x2, codigo_entidad, tipo_usuario, copago_entidad, cups_sin_contrato). cantidades_hospitalizacion, cantidades_soat_hospitalizacion, hospitalizacion_codes quedan legacy (Fase 3). Patrón idéntico a urgencias/odontologia.
- **Reglas engine a usar** (ya existen en BD):
  - `detect_decimales` → `valores_decimales`
  - `detect_tipo_documento_edad` → `tipo_documento_edad_menor_7`, `tipo_documento_edad_mayor_18`, `tipo_documento_edad_7_17`, `tipo_documento_edad_as_menor`, `tipo_documento_edad_ms_mayor`, `tipo_documento_edad_cn_invalido`, `tipo_documento_edad_ce_invalido` (7 reglas)
  - `detect_tipo_identificacion_entidad` → `tipo_id_requiere_entidad_86000` + `entidad_86000_requiere_as_ms`
  - `detect_codigo_entidad_vs_entidad_afiliacion` → `codigo_entidad`
  - `detect_tipo_usuario` → `tipo_usuario_valido`
  - `detect_copago_entidad_urgencias` → `copago_entidad_valido`
  - `detect_cups_sin_contrato` → `cups_sin_contrato`
- **Nota**: `cantidades_hospitalizacion`, `cantidades_soat_hospitalizacion` y `hospitalizacion_codes` se agregan el toggle aquí, pero las reglas engine `cantidades_soat_hospitalizacion` y `hospitalizacion_codes_*` se crean en Fase 3. Por ahora el toggle para esos 3 detectores llama engine con reglas existentes (cantidad_consultas_anomalas etc.) o queda con else legacy hasta F3.
- **Dependencias**: Ninguna
- **Estimación**: ~100 líneas netas
- **Verificación**: `is_rule_engine_enabled()=True` produce output para transversales. Sin crash con columnas faltantes.
- **Tests**: T-F1.7 (snapshot tests)

### T-F1.2: ✅ Agregar toggle en intramural/detect_all.py

- **Archivos**: `app/services/intramural/detect_all.py`
- **Descripción**: Agregado toggle para 7 detectores transversales con mismas reglas engine que T-F1.1. Implementado.
- **Dependencias**: Ninguna
- **Estimación**: ~80 líneas netas
- **Verificación**: Mismos criterios que T-F1.1.
- **Tests**: T-F1.7

### T-F1.3: ✅ Agregar toggle en ambulatoria/detect_all.py

- **Archivos**: `app/services/ambulatoria/detect_all.py`
- **Descripción**: Agregado toggle para 7 transversales. Implementado.
- **Dependencias**: Ninguna
- **Estimación**: ~80 líneas netas
- **Verificación**: Mismos criterios.
- **Tests**: T-F1.7

### T-F1.4: ✅ Agregar toggle en extramural/detect_all.py

- **Archivos**: `app/services/extramural/detect_all.py`
- **Descripción**: Agregado toggle para 7 transversales. Implementado.
- **Dependencias**: Ninguna
- **Estimación**: ~80 líneas netas
- **Verificación**: Mismos criterios.
- **Tests**: T-F1.7

### T-F1.5: ✅ Agregar toggle en farmacia/detect_all.py

- **Archivos**: `app/services/farmacia/detect_all.py`
- **Descripción**: Agregado toggle para 7 transversales. `detect_duplicados_farmacia_farmacia` queda legacy (Fase 2). Implementado.
- **Dependencias**: Ninguna (el toggle se agrega, F2 completa la regla BD)
- **Estimación**: ~80 líneas netas
- **Verificación**: Mismos criterios.
- **Tests**: T-F1.7

### T-F1.6: ✅ Crear regla BD `cantidades_soat_hospitalizacion`

- **Archivos**: `seed/migracion-engine/01_cantidades_soat_hospitalizacion.sql`
- **Descripción**: Creado seed SQL con regla `cantidades_soat_hospitalizacion` (dominio: hospitalizacion, severidad: warning). Condiciones: AND padre → eq(tarifario, "SOAT") + gt(cantidad, 2). Implementado.
- **Dependencias**: Ninguna
- **Estimación**: ~20 líneas netas (archivo seed SQL)
- **Verificación**: SQL idempotente (INSERT WHERE NOT EXISTS + DELETE conditions + re-INSERT).

### T-F1.7: ✅ Snapshot tests F1

- **Archivos**: 
  - `tests/services/hospitalizacion/test_detect_all_transversales.py`
  - `tests/services/intramural/test_detect_all_transversales.py`
  - `tests/services/ambulatoria/test_detect_all_transversales.py`
  - `tests/services/extramural/test_detect_all_transversales.py`
  - `tests/services/farmacia/test_detect_all_transversales.py`
- **Descripción**: Creados 5 archivos de test snapshot que verifican que engine y legacy paths producen la misma estructura de output (mismas keys, resultados vacíos para datos limpios). Cada test compara engine vs legacy usando `os.environ["USE_RULE_ENGINE"]` para toggle. Implementado.
- **Dependencias**: T-F1.1 a T-F1.6
- **Estimación**: ~40 líneas por archivo = ~200 líneas netas total
- **Verificación**: `pytest tests/services/*/test_detect_all_transversales.py` pasa (15 tests). Output engine = output legacy en estructura.

---

## Fase 2: Farmacia

### T-F2.1: ✅ Toggle duplicados_farmacia_farmacia via GroupEvaluator

- **Archivos**: `app/services/farmacia/detect_all.py` (modificado), `seed/migracion-engine/02_duplicados_farmacia_farmacia.sql`
- **Descripción**: 
  1. ✅ Creada regla BD `duplicados_farmacia_farmacia` con dominio `farmacia`, evaluador `GroupEvaluator` + `all_values_match(threshold=2)`, parametros con `group_by=numero_factura`, `filter_field=tipo_factura_descripcion`, `filter_value=Farmacia`, `collect_value_counts` en (codigo, cantidad).
  2. ✅ Agregado toggle en `farmacia/detect_all.py`: cuando `is_rule_engine_enabled()`=True, llama `RuleBasedDetector("duplicados_farmacia_farmacia", session).detect(...)`; caso contrario usa legacy.
- **Dependencias**: T-F1.5
- **Estimación**: ~30 líneas netas (20 regla BD + 10 detect_all.py)
- **Verificación**: `pytest tests/services/farmacia/test_duplicados_farmacia_engine.py::test_engine_path_routes_duplicados` pasa — confirma que RuleBasedDetector recibe el nombre correcto de regla.
- **Tests**: T-F2.2

### T-F2.2: ✅ Snapshot tests F2

- **Archivos**: `tests/services/farmacia/test_duplicados_farmacia_engine.py`
- **Descripción**: 6 tests que cubren:
  - Engine path llama RuleBasedDetector con nombre de regla correcto
  - Legacy path detecta duplicidad total (todos los pares ≥2 en F001)
  - Legacy path NO detecta mezcla (algunos pares únicos)
  - Engine path (mocked) retorna vacío para datos sin duplicados
  - Ambos paths manejan columna `tipo_factura_descripcion` faltante sin crash
- **Dependencias**: T-F2.1
- **Estimación**: ~40 líneas netas
- **Verificación**: `pytest tests/services/farmacia/test_duplicados_farmacia_engine.py` pasa (6/6).

---

## Fase 3: Hospitalización

### T-F3.1: ✅ centro_costo_hospitalizacion → engine toggle

- **Archivos**: `app/services/hospitalizacion/detect_all.py` (modificado), `seed/migracion-engine/03_centro_costo_hospitalizacion_valido.sql` (nuevo)
- **Descripción**: 
  1. ✅ Creada regla BD `centro_costo_hospitalizacion_valido` con dominio `hospitalizacion`, evaluador `centro_costo_check`, condición atómica con centro_costo_check operator.
  2. ✅ Agregado toggle en detect_all.py: cuando `is_rule_engine_enabled()`=True, llama `RuleBasedDetector("centro_costo_hospitalizacion_valido", session).detect(...)`; caso contrario usa legacy.
  3. ✅ Cambiado `item["centro_actual"]` a `item.get("centro_actual", "")` y `item["centro_deberia"]` a `item.get("centro_deberia", "")` en el formato de `centros_de_costos` para manejar output del engine (que no tiene esos keys).
- **Nota**: El filtro de prioridad (prioridad 1) se queda como post-procesamiento Python (no va al engine). El engine centro_costo_check no maneja la regla específica "Hospitalización + URGENCIAS → HOSPITALIZACION_ESTANCIA" que sí existe en legacy.
- **Dependencias**: T-F1.1
- **Estimación**: ~25 líneas netas (10 regla BD + 10 detect_all.py + 5 fix formato)
- **Verificación**: `pytest tests/services/hospitalizacion/test_hospitalizacion_engine_f3.py` pasa (4 tests en TestF3CentroCostoToggle).
- **Tests**: T-F3.4

### T-F3.2: ✅ cantidades_hospitalizacion + cantidades_soat_hospitalizacion → engine toggles

- **Archivos**: `app/services/hospitalizacion/detect_all.py` (modificado), `seed/migracion-engine/04_cantidades_hospitalizacion.sql` (nuevo)
- **Descripción**: 
  1. ✅ Creada regla BD `cantidades_hospitalizacion`: evaluador `gt(cantidad, 8)`, dominio `hospitalizacion`, severidad `warning`. Condición atómica gt(cantidad, 8).
  2. ✅ La regla `cantidades_soat_hospitalizacion` ya se creó en T-F1.6 — ahora agregado el toggle en detect_all.py que la usa: `RuleBasedDetector("cantidades_soat_hospitalizacion", session).detect(...)`.
  3. ✅ En detect_all.py: reemplazadas llamadas legacy por engine para ambas.
- **Dependencias**: T-F1.1, T-F1.6
- **Estimación**: ~25 líneas netas (15 regla BD + 10 detect_all.py)
- **Verificación**: `pytest tests/services/hospitalizacion/test_hospitalizacion_engine_f3.py::TestF3CantidadesToggle` pasa (5 tests).
- **Tests**: T-F3.4

### T-F3.3: ✅ hospitalizacion_codes → legacy toggle (engine no soporta computed filter)

- **Archivos**: `app/services/hospitalizacion/detect_all.py` (modificado)
- **Descripción**: 
  1. ✅ El engine actual no soporta `filter_function` por valor computado (`date.horas`). `GroupEvaluator.build_groups()` solo soporta `filter_field`/`filter_value` para columnas directas. No hay soporte para filtrar grupos por valor computado (estancia_horas derivada de fec_factura y fecha_cierre).
  2. ✅ Decisión: mantener `detect_hospitalizacion_codes` como legacy para ambos paths (engine y legacy). El `is_rule_engine_enabled()` no afecta este detector.
  3. ✅ Documentación agregada en el código explicando por qué no se migra.
- **Alternativa futura**: Cuando `GroupEvaluator.build_groups()` soporte `filter_function` o pre-cálculo de `date.horas`, crear 2 reglas BD:
  - `hospitalizacion_codes_estancia_mayor_24h`: GroupEvaluator + set_contains_all para códigos obligatorios completos
  - `hospitalizacion_codes_estancia_menor_24h`: GroupEvaluator + set_contains_all para set restringido {"890601H", "129B02"}
- **Riesgo**: Mitigado — no hay cambio de comportamiento. Legacy sigue funcionando.
- **Dependencias**: T-F1.1
- **Estimación**: ~5 líneas netas (solo documentación)
- **Verificación**: `pytest tests/services/hospitalizacion/test_hospitalizacion_engine_f3.py::TestF3HospitalizacionCodesToggle` pasa (4 tests).
- **Tests**: T-F3.4

### T-F3.4: ✅ Snapshot tests F3

- **Archivos**: `tests/services/hospitalizacion/test_hospitalizacion_engine_f3.py` (nuevo)
- **Descripción**: Creado archivo con 15 tests TDD cubriendo:
  - **T-F3.1 (centro_costo)**: 4 tests — engine path llama centro_costo_hospitalizacion_valido, legacy path produce estructura, formato resilient a engine output (sin centro_actual/centro_deberia), engine usa dominio correcto.
  - **T-F3.2 (cantidades)**: 5 tests — engine path llama cantidades_hospitalizacion, engine path llama cantidades_soat_hospitalizacion, missing cantidad column graceful, missing tarifario column graceful, legacy path produce estructura.
  - **T-F3.3 (codes)**: 4 tests — engine path llama legacy detect_hospitalizacion_codes, legacy produce cups_equivalentes, legacy cups_equivalentes es list, missing fecha_cierre no crash.
  - **Snapshot**: 2 tests — keys presentes en ambos paths, totales keys presentes.
- **Dependencias**: T-F3.1, T-F3.2, T-F3.3
- **Estimación**: ~120 líneas netas
- **Verificación**: `pytest tests/services/hospitalizacion/test_hospitalizacion_engine_f3.py` pasa (15/15). `pytest tests/services/hospitalizacion/` pasa (18/18).

---

## Fase 4: Intramural parte 1 — centro_costo, IDE, revision_cantidad

### T-F4.1: ✅ Implementar CentroCostoIntramuralEvaluator

- **Archivos**: `app/services/engine/evaluators.py` (agregar clase)
- **Descripción**: Crear nuevo evaluador `CentroCostoIntramuralEvaluator` (operator: `centro_costo_intramural`) que implementa:
  - Reglas comunes 1-9 (copiadas de `CentroCostoCheckEvaluator` pero sin REGLA3 original — usa REGLA3-INTRAMURAL)
  - REGLA3-INTRAMURAL: codigo in CODIGOS_PYP_URGENCIAS → CC in CENTROS_COSTO_PYP_INTRAMURAL
  - REGLA6/REVERSE6: tipo=05 + codigo not in excluidos vacunación → CC=SALUD PUBLICA. Reverse: CC=SALUD PUBLICA → tipo=05
  - REGLA7/REVERSE7: tipo=03/04 → CC=SERVICIOS AMBULATORIOS. Reverse: AMBULATORIO → tipo 03/04
  - REGLA10/REVERSE10: tipo=02/05 + Lab=Si → CC in CENTROS_COSTO_LABORATORIO_VALIDOS
  - REGLA_RESPONSABLE_URGENCIAS: responsable in FACTURADORES_URGENCIAS + tipo 01/04 → CC=URGENCIAS|HOSPITALIZACIÓN
- **Constantes requeridas**: Importar de `app.constants.intramural` (o crear si no existen): `CENTROS_COSTO_PYP_INTRAMURAL`, `CODIGOS_EXCLUIDOS_VACUNACION`, `CENTRO_COSTO_SALUD_PUBLICA`, `CENTRO_COSTO_AMBULATORIO`, `CENTROS_COSTO_LABORATORIO_VALIDOS`, `CODIGOS_EXCEPTUADOS_AMBULATORIO`, `CODIGOS_EXCEPTUADOS_RESPONSABLE_URGENCIAS`, `FACTURADORES_URGENCIAS` (ya existe en urgencias.py).
- **Registro**: Agregar `CentroCostoIntramuralEvaluator()` a la lista en `_register_builtins()`.
- **Dependencias**: Ninguna
- **Estimación**: ~130 líneas netas
- **Verificación**: Evaluador retorna True (violación) para casos que coinciden con las 8 reglas intramural, False para casos válidos.
- **Tests**: T-F4.5 (snapshot). Tests unitarios: instanciar evaluador con contexto simulado.

### T-F4.2: 📝 ide_contrato_intramural → legacy toggle (engine no soporta sheet-level pre-scan)

- **Archivos**: `app/services/intramural/detect_all.py` (documentación agregada)
- **Descripción**: La lógica de IDE Contrato Intramural requiere pre-scan de toda la hoja (detecta facturas donde TODOS los códigos son laboratorio de envío antes de procesar filas) y lógica de inserción (buscar factores en otras filas). El engine actual solo soporta evaluación row-by-row vía AtomicEvaluator. Decisión: mantener como legacy con documentación, mismo patrón que `hospitalizacion_codes` en F3.
- **Dependencias**: Ninguna
- **Estimación**: ~5 líneas (documentación + nota en detect_all.py)
- **Verificación**: detect_ide_contrato_intramural se sigue llamando en ambos paths (engine y legacy). Tests F4.4 verifican que legacy se invoca en engine path.

### T-F4.3: ✅ revision_cantidad_intramural → engine (nuevo evaluador RevisionCantidadIntramuralEvaluator)

- **Archivos**: `app/services/engine/evaluators.py` (nuevo evaluador `RevisionCantidadIntramuralEvaluator`), `seed/migracion-engine/06_revision_cantidad_intramural.sql` (regla BD con evaluador)
- **Descripción**: Creado evaluador `RevisionCantidadIntramuralEvaluator` (operator: `revision_cantidad_intramural`) que implementa la cascade con CODIGOS_LIMITE_ESPECIFICO_INTRAMURAL. Semilla SQL creada con regla BD que usa el evaluador.
  - Rule 1: AND(eq(tipo, "02"), eq(lab, "No"), gt(cantidad, 2))
  - Rule 2: AND(OR(eq(tipo, "03"), eq(tipo, "04")), gt(cantidad, 13))
  - Rule 3 (default): gt(cantidad, 1)
  - Pre-check: límites específicos por código (CODIGOS_LIMITE_ESPECIFICO_INTRAMURAL) se evalúan antes de cascade
- **Dependencias**: Ninguna
- **Estimación**: ~25 líneas netas (evaluador ~40ln + seed SQL ~15ln)
- **Verificación**: Tests unitarios con EvaluationContext cubren todas las ramas de cascade + specific limits.

### T-F4.4: ✅ Integrar toggles en intramural/detect_all.py (Fase 1 + Fase 4)

- **Archivos**: `app/services/intramural/detect_all.py`
- **Descripción**: Agregados toggles engine para:
  - ✅ `detect_centro_costo_intramural` → `RuleBasedDetector("centro_costo_intramural_valido", session)`
  - 📝 `detect_ide_contrato_intramural` → **legacy toggle** (engine no soporta sheet-level pre-scan). Documentado con nota explicativa.
  - ✅ `detect_revision_cantidad_intramural` → `RuleBasedDetector("revision_cantidad_intramural", session)`
  - ✅ Formato centros_de_costos cambiado a `.get()` para compatibilidad con output engine (sin centro_actual/centro_deberia).
- **Nota**: Los toggles transversales (T-F1.2) ya cubren decimales, tipo_doc/edad, etc.
- **Dependencias**: T-F1.2, T-F4.1, T-F4.2, T-F4.3
- **Estimación**: ~50 líneas netas
- **Verificación**: `is_rule_engine_enabled()=True` produce estructura de output idéntica a legacy (con .get() para centros_de_costos). Tests F4.5 verifican keys presentes en ambos paths.
- **Tests**: T-F4.5

### T-F4.5: ✅ Snapshot tests F4

- **Archivos**: `tests/services/intramural/test_intramural_engine_f4.py`
- **Descripción**: Creado archivo con 57 tests TDD cubriendo:
  - **T-F4.1 (CentroCostoIntramuralEvaluator)**: 35 tests — todas las reglas comunes (REGLA1,2,4,8,9 + REVERSES) + 5 intramural-specific (REGLA3-INTRAMURAL, REGLA6/REVERSE6, REGLA7/REVERSE7, REGLA10/REVERSE10, REGLA_RESPONSABLE_URGENCIAS) + edge cases.
  - **T-F4.2 (ide_contrato legacy)**: 1 test — verifica legacy se llama en engine path.
  - **T-F4.3 (RevisionCantidadIntramuralEvaluator)**: 14 tests — cascade (rule1, rule2, rule3), specific code limit 901101, edge cases.
  - **T-F4.4 (detect_all integration)**: 6 tests — engine path llama centro_costo_intramural_valido, engine path llama revision_cantidad_intramural, ide_contrato stays legacy, keys presentes en ambos paths, totales keys, formatter resiliente.
  - **Registry**: 2 tests — ambos evaluadores registrados en EVALUATOR_REGISTRY.
- **Dependencias**: T-F4.1, T-F4.2, T-F4.3, T-F4.4
- **Estimación**: ~460 líneas netas (incluye docstrings y asserts detallados)
- **Verificación**: `pytest tests/services/intramural/test_intramural_engine_f4.py` pasa (57/57). `pytest tests/services/intramural/` pasa (114/114).

---

## Fase 5: Intramural parte 2 — CronogramaCheckEvaluator, duplicado_id_codigo

### T-F5.1: ✅ Implementar CronogramaCheckEvaluator

- **Archivos**: `app/services/engine/evaluators.py` (agregar clase), `tests/services/intramural/test_cronograma_check_evaluator.py` (tests)
- **Descripción**: Creado evaluador `CronogramaCheckEvaluator` (operator: `cronograma_check`) que implementa la lógica completa de `detect_bacteriologas_cronograma`:
  1. **Filtros de entrada**: solo Intramural, tipo in {"02","05"}, tipo=02 requiere lab="Si", código not in EXCEPCIONES_BACTERIOLOGA
  2. **Bypass**: responsable_cierra in FACTURADORES_URGENCIAS → no error
  3. **Bypass**: codigo_profesional in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA → no error
  4. **Parse fecha**: fec_factura → datetime, si inválido → skip
  5. **Siglas filter**: Chapuel→solo PYM, Tapia/Ordoñez→solo CE, default→CE|PYM
  6. **Cache de turnos**: por (month, year, day, siglas_filter) para evitar múltiples llamadas a `get_turno_del_dia()`
  7. **Resolve nombres a códigos**: usar `_NOMBRE_A_CODIGO` (module-level, pre-cargado desde constantes)
  8. **Evaluación**: si profesional no está en turno → True (MATCH = detección)
- **Cache**: Interno por instancia (`self._cronograma_cache`), session-scoped.
- **Registro**: Agregar `CronogramaCheckEvaluator()` a `_register_builtins()`.
- **Dependencias**: Ninguna
- **Estimación**: ~140 líneas netas (120 evaluador + 20 constantes de mapeo)
- **Verificación**: Tests unitarios mockeando `get_turno_del_dia()` (5 escenarios: en turno, fuera turno, exceptuado, Chapuel, Tapia, facturador). Ver diseño sección 7.2 para código de referencia.
- **Tests**: Unitarios inline + T-F5.5 (snapshot)

### T-F5.2: ✅ Extender GroupEvaluator con collect_group_keys

- **Archivos**: `app/services/engine/group_evaluator.py` (modificado), `tests/services/intramural/test_duplicado_id_codigo_engine.py` (tests)
- **Descripción**: Agregada agregación `collect_group_keys` que retorna las claves de las filas del grupo (números de factura).
  - En `_agg_*`: agregado `_agg_collect_group_keys(rows, data_sheet, indices, field)` que retorna lista de valores únicos del `field` en las filas del grupo.
  - En `_build_group_data`: agregado case `elif func == "collect_group_keys"` que llama a `_agg_collect_group_keys`.
  - `build_groups()` extendido para soportar `group_by` como lista de campos (composite key para duplicado_id_codigo).
- **Dependencias**: Ninguna
- **Estimación**: ~35 líneas netas
- **Verificación**: `collect_group_keys` retorna lista de valores únicos de un field para un grupo (5 tests).

### T-F5.3: ✅ duplicado_id_codigo → engine via GroupEvaluator (2 rule configs)

- **Archivos**: `seed/migracion-engine/07_duplicado_id_codigo_05.sql` (nuevo), `seed/migracion-engine/08_duplicado_id_codigo_02_lab.sql` (nuevo), `app/services/intramural/detect_all.py` (modificado)
- **Descripción**: Creadas 2 reglas BD con composite group_by (identificacion, codigo, codigo_dx_principal) y post-processing en detect_all.py:
  1. `duplicado_id_codigo_05`: GroupEvaluator, filter `codigo_tipo_procedimiento=05`, composite group_by, aggregation `collect_group_keys(numero_factura)` + `group_size`, condition `gte(count, 2)`. Post-filter: CODIGOS_EXENTOS_05 + FACTURADORES_URGENCIAS.
  2. `duplicado_id_codigo_02_lab`: GroupEvaluator, filter `codigo_tipo_procedimiento=02`, aggregation `collect_group_keys(numero_factura)` + `group_size`, condition `gte(count, 4)`. Post-filter: FACTURADORES_URGENCIAS.
- **Nota**: La exclusión de FACTURADORES_URGENCIAS es post-group-by, implementada como filtro post-engine. CODIGOS_EXENTOS_05 filtrado post-engine.
- **Dependencias**: T-F5.2 (collect_group_keys + composite group_by)
- **Estimación**: ~80 líneas netas (30 seed SQL + 50 detect_all.py)
- **Verificación**: Engine routing tests: llama ambas reglas. Post-processing tests: FACTURADORES_URGENCIAS y CODIGOS_EXENTOS_05 filtrados correctamente.
- **Tests**: T-F5.5

### T-F5.4: ✅ Integrar toggle bacteriologas_cronograma + duplicado_id_codigo en detect_all.py

- **Archivos**: `app/services/intramural/detect_all.py` (modificado), `seed/migracion-engine/09_bacteriologas_cronograma.sql` (nuevo)
- **Descripción**: 
  - ✅ Bacteriologas: toggle con `RuleBasedDetector("bacteriologas_cronograma", session).detect(...)`. Regla BD usa evaluador `cronograma_check`. Legacy recibe `responsable_cierra` como parámetro extra (ignorado en engine — el evaluador lo obtiene del contexto).
  - ✅ Duplicado ID: toggle con ambas reglas `duplicado_id_codigo_05` + `duplicado_id_codigo_02_lab` + post-processing para FACTURADORES_URGENCIAS y CODIGOS_EXENTOS_05.
- **Dependencias**: T-F5.1 (CronogramaCheckEvaluator), T-F5.3 (seed SQL)
- **Estimación**: ~75 líneas netas (15 seed SQL + 60 detect_all.py)
- **Verificación**: Engine path llama bacteriologas_cronograma + duplicado_id_codigo reglas. Legacy path funciona sin cambios.

### T-F5.5: ✅ Snapshot tests F5 (30 tests TDD)

- **Archivos**: 
  - `tests/services/intramural/test_cronograma_check_evaluator.py` (20 tests)
  - `tests/services/intramural/test_duplicado_id_codigo_engine.py` (10 tests)
- **Descripción**: 
  - **T-F5.1**: 20 tests TDD para CronogramaCheckEvaluator: en turno, fuera turno, bypass exceptuado, Chapuel filter, Tapia/Ordoñez filter, facturador urgencias bypass, cache, filtros entrada, registro.
  - **T-F5.2**: 5 tests para collect_group_keys: unique, dedup, missing field, via _build_group_data, registry.
  - **T-F5.3**: 2 tests engine routing: duplicado_05 + duplicado_02_lab llamados, legacy path.
  - **T-F5.4**: 1 test engine routing: bacteriologas_cronograma llamado.
  - **T-F5.5**: 2 snapshot tests: keys presentes, vacío engine vs legacy.
- **Dependencias**: T-F5.1, T-F5.2, T-F5.3, T-F5.4
- **Estimación**: ~200 líneas netas (120 unit + 80 snapshot)
- **Verificación**: `pytest tests/services/intramural/` pasa (214 tests). `pytest tests/engine/test_evaluators.py` pasa (70 tests).

---

## Fase 6: Post-filtros legacy y limpieza

### T-F6.1: ✅ Modelar excepción 990203 como ExceptionHandler

- **Archivos**: BD (crear Excepcion en BD)
- **Descripción**: Insertar registro en tabla `excepcion`:
  - `rule=doble_tipo_procedimiento`
  - `domain=odontologia`
  - `tipo_efecto=suspension` (suspende la regla cuando código=990203)
  - `condiciones`: `{"codigo": "990203"}`
  - Ver diseño sección 8.1.
- **Dependencias**: Ninguna
- **Estimación**: ~10 líneas netas
- **Verificación**: Engine skips `doble_tipo_procedimiento` rule para facturas con código 990203.

### T-F6.2: ✅ Modelar excepción PyP como ExceptionHandler

- **Archivos**: BD (crear Excepcion en BD)
- **Descripción**: Insertar registro en tabla `excepcion`:
  - `rule=ruta_duplicada`
  - `domain=odontologia`
  - `tipo_efecto=override` (cambia threshold)
  - `overrides`: `{"umbral": 4}` (en lugar de 3)
  - `condiciones`: `{"convenio": "PyP"}`
  - Ver diseño sección 8.1.
- **Dependencias**: Ninguna
- **Estimación**: ~10 líneas netas
- **Verificación**: Engine aplica threshold=4 para facturas PyP en `ruta_duplicada`.

### T-F6.3: ✅ Verificar SalaObservacionEvaluator registrado

- **Archivos**: `app/services/engine/evaluators.py` (verificar), `app/services/urgencias/detect_all.py` (verificar)
- **Descripción**: 
  1. Verificar que `SalaObservacionEvaluator` está en `EVALUATOR_REGISTRY` (ya está, línea 834 en evaluators.py — confirmar).
  2. Verificar que `detect_sala_observacion` corre SIEMPRE (sin toggle) — debe seguir corriendo legacy O engine. Como el evaluador ya existe, no hay cambio necesario. Solo documentar.
- **Dependencias**: Ninguna
- **Estimación**: ~0 líneas (solo verificación/documentación)
- **Verificación**: SalaObservacionEvaluator está registrado y llamado desde el engine cuando `USE_RULE_ENGINE=true`.

### T-F6.4: ✅ Cambiar is_rule_engine_enabled() → return True

- **Archivos**: `app/constants/base.py`
- **Descripción**: Cambiar `is_rule_engine_enabled()` de leer env var a retornar `True` unconditionalmente:
  ```python
  def is_rule_engine_enabled() -> bool:
      return True  # Engine always on — legacy removed
  ```
- **Dependencias**: T-F1 a T-F5 completas y validadas en producción ≥1 semana
- **Estimación**: ~5 líneas netas
- **Verificación**: `is_rule_engine_enabled()` retorna True sin importar env var.

### T-F6.5: ✅ Remover ramas else legacy de detect_all.py

- **Archivos**: 
  - `app/services/hospitalizacion/detect_all.py`
  - `app/services/intramural/detect_all.py`
  - `app/services/ambulatoria/detect_all.py`
  - `app/services/extramural/detect_all.py`
  - `app/services/farmacia/detect_all.py`
- **Descripción**: Remover todas las ramas `else:` que llaman detectores legacy. Mantener SOLO el bloque `if is_rule_engine_enabled():` (que ahora siempre es True). Las llamadas legacy se eliminan — el orquestador solo corre engine.
- **Dependencias**: T-F6.4
- **Estimación**: ~30 líneas netas (6 líneas por archivo promedio)
- **Verificación**: No hay referencias a detectores legacy en detect_all.py. `pytest` suite passes.

### T-F6.6: ✅ Marcar detectores legacy como @deprecated

- **Archivos**: Todos los detectores legacy en `app/services/hospitalizacion/`, `app/services/intramural/`, `app/services/ambulatoria/`, `app/services/extramural/`, `app/services/farmacia/`
- **Descripción**: Agregar docstring `@deprecated — use engine rule {rule_name} instead` al inicio de cada archivo detector legacy. Ejemplo:
  ```python
  """@deprecated — use engine rule centro_costo_hospitalizacion_valido instead.
  
  Legacy detector — kept for reference. All new development must use the engine.
  """
  ```
- **Dependencias**: T-F6.5
- **Estimación**: ~15 líneas netas (5 archivos × 3 líneas)
- **Verificación**: Cada detector legacy tiene docstring con `@deprecated`.

---

## Matriz de trazabilidad: Tarea → Detector legacy → Regla engine

| Task ID | Detector legacy | Regla engine / Evaluador |
|---------|----------------|--------------------------|
| T-F1.1 | `detect_decimales` | `valores_decimales` |
| T-F1.1 | `detect_tipo_documento_edad` | `tipo_documento_edad_*` (7 reglas) |
| T-F1.1 | `detect_tipo_identificacion_entidad` | `tipo_id_requiere_entidad_86000` + `entidad_86000_requiere_as_ms` |
| T-F1.1 | `detect_codigo_entidad_vs_entidad_afiliacion` | `codigo_entidad` |
| T-F1.1 | `detect_tipo_usuario` | `tipo_usuario_valido` |
| T-F1.1 | `detect_copago_entidad_urgencias` | `copago_entidad_valido` |
| T-F1.1 | `detect_cups_sin_contrato` | `cups_sin_contrato` |
| T-F1.6 | `detect_cantidades_soat_hospitalizacion` | `cantidades_soat_hospitalizacion` (nueva) |
| T-F2.1 | `detect_duplicados_farmacia_farmacia` | `duplicados_farmacia_farmacia` (nueva, GroupEvaluator) |
| T-F3.1 | `detect_centro_costo_hospitalizacion` | `centro_costo_hospitalizacion_valido` (nueva) |
| T-F3.2 | `detect_cantidades_hospitalizacion` | `cantidades_hospitalizacion` (nueva) |
| T-F3.3 | `detect_hospitalizacion_codes` | `hospitalizacion_codes_estancia_mayor_24h` + `menor_24h` (2 nuevas) |
| T-F4.1 | `detect_centro_costo_intramural` | `centro_costo_intramural_valido` (nueva, evaluador nuevo) |
| T-F4.2 | `detect_ide_contrato_intramural` | `ide_contrato_intramural_valido` (nueva) |
| T-F4.3 | `detect_revision_cantidad_intramural` | `revision_cantidad_intramural` (nueva) |
| T-F5.1 | `detect_bacteriologas_cronograma` | `bacteriologas_cronograma` (nueva, evaluador nuevo) |
| T-F5.3 | `detect_duplicado_id_codigo` | `duplicado_id_codigo_05` + `duplicado_id_codigo_02_lab` (2 nuevas) |
| T-F6.1 | Excepción 990203 | ExceptionHandler (suspensión) |
| T-F6.2 | Excepción PyP | ExceptionHandler (override threshold) |

---

## Review Workload Forecast

| Fase | Tareas | Líneas netas | Excede 400ln? | PRs recomendados |
|------|--------|--------------|---------------|------------------|
| F1 — Transversales sin engine | 7 | ~420 | **SÍ** | 2 PRs: (a) detect_all.py toggles ~250ln, (b) snapshot tests + regla BD ~170ln |
| F2 — Farmacia | 2 | ~70 | No | 1 PR (incluir con F1b o independiente) |
| F3 — Hospitalización | 4 | ~190 | No | 1 PR |
| F4 — Intramural parte 1 | 5 | ~290 | No | 2 PRs: (a) evaluador ~130ln, (b) reglas BD + toggle + tests ~160ln |
| F5 — Intramural parte 2 | 5 | ~300 | No | 2 PRs: (a) CronogramaCheckEvaluator + tests ~200ln, (b) duplicado + snapshot ~100ln |
| F6 — Post-filtros + limpieza | 6 | ~85 | No | 1 PR |
| **Total** | **29** | **~1,355** | **SÍ** | **~8 PRs** |

### Resumen

| Métrica | Valor |
|---------|-------|
| Líneas totales estimadas | ~1,355 |
| Archivos modificados/creados | ~30 |
| Reglas BD nuevas | 11 |
| Evaluadores nuevos | 2 (`CentroCostoIntramuralEvaluator`, `CronogramaCheckEvaluator`) |
| Extensiones a engine existente | 1 (`collect_group_keys` en GroupEvaluator) |
| Chained PRs recommended | **Yes** (F1 excede 400ln, F4 y F5 se benefician de split) |
| Delivery strategy | `ask-always` — F1 es el que más riesgo tiene de exceder el budget. Preguntar antes de apply. |

### Recomendación de orden de PRs

1. **PR-1**: T-F1.1 a T-F1.5 (toggle en 5 detect_all.py, ~420ln → chained: PR-1a detect_all.py ~250ln, PR-1b tests + regla F1.6 ~170ln)
2. **PR-2**: T-F2.1 + T-F2.2 (farmacia duplicados + tests, ~70ln)
3. **PR-3**: T-F3.1 + T-F3.2 + T-F3.3 + T-F3.4 (hospitalización específicos, ~190ln)
4. **PR-4**: T-F4.1 + T-F4.2 + T-F4.3 + T-F4.4 + T-F4.5 (intramural parte 1, ~290ln → chained: PR-4a evaluador ~130ln, PR-4b reglas + toggle + tests ~160ln)
5. **PR-5**: T-F5.1 + T-F5.2 + T-F5.3 + T-F5.4 + T-F5.5 (intramural parte 2, ~300ln → chained: PR-5a cronograma evaluador + tests ~200ln, PR-5b duplicado + tests ~100ln)
6. **PR-6**: T-F6.1 a T-F6.6 (post-filtros + limpieza, ~85ln)

**Total**: ~8 PRs encadenados. 3 fases (F1, F4, F5) recomiendan chained PRs.
