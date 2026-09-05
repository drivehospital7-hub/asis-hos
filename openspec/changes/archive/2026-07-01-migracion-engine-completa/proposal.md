# Proposal: SDD-003 — Migración completa al Rule Engine

**Change name**: `migracion-engine-completa`
**Created**: 2026-06-30
**Topic key**: `sdd/migracion-engine-completa/proposal`

---

## Problem statement

Hoy el codebase tiene **dos caminos de detección** que coexisten con un toggle global (`USE_RULE_ENGINE`):

- **Engine**: 18 evaluadores atómicos + 5 providers + group-by en `app/services/engine/`
- **Legacy**: detectores Python planos en `app/services/{area}/` + transversales

El toggle NO cubre todas las áreas. Solo 3/8 áreas (urgencias, odontología, equipos básicos) tienen
`if is_rule_engine_enabled()` en su `detect_all.py`. Las 5 restantes (hospitalización, intramural,
ambulatoria, farmacia, extramural) corren 100% legacy — ni siquiera tienen la bifurcación.
Los transversales (decimales, tipo_usuario, codigo_entidad...) se llaman legacy en esas 5 áreas
incluso cuando el engine ya tiene las reglas cargadas.

Esto produce:
- **Inconsistencia**: una regla como `decimales` corre por engine en odontología y por legacy en hospitalización
- **Deuda técnica**: 12 detectores Python planos (~2,800 líneas) que nadie toca por miedo a romper
- **Auditabilidad cero**: las 5 áreas sin toggle no dejan evidencia ni traza de auditoría
- **Mantenimiento dual**: cambiar lógica de negocio requiere tocar engine + detector legacy

---

## Intent

Migrar **TODOS los detectores legacy** al Rule Engine, independientemente de la complejidad,
para tener un solo camino de detección. Al finalizar:

- `is_rule_engine_enabled()` se vuelve redundante (siempre true)
- Detectores Python legacy se eliminan o quedan como dead code documentado
- Toda detección deja evidencia en `evidence` + `resultado_auditoria`
- Nuevas reglas se configuran en BD, no en código Python

---

## Scope

### In Scope

| # | Grupo | Detectores legacy | Áreas afectadas |
|---|-------|-------------------|-----------------|
| 1 | **Transversales** (fase 1) | `decimales`, `tipo_usuario`, `codigo_entidad_vs_entidad_afiliacion`, `tipo_documento_edad`, `tipo_identificacion_entidad`, `copago_entidad`, `cups_sin_contrato`, `doble_tipo_procedimiento`, `ruta_duplicada`, `cantidades_anomalas` | hospitalización, intramural, ambulatoria, farmacia, extramural |
| 2 | **Centro costo + IDE contrato** (fases 2-5) | `centro_costo_hospitalizacion`, `centro_costo_intramural`, `centro_costo_ambulatoria`, `ide_contrato_intramural`, `ide_contrato_rules` | hospitalización, intramural, ambulatoria |
| 3 | **Hospitalización** (fase 3) | `hospitalizacion_codes`, `cantidades_hospitalizacion`, `cantidades_soat_hospitalizacion` | hospitalización |
| 4 | **Intramural parte 1** (fase 4) | `centro_costo_intramural` (12 reglas), `ide_contrato_intramural`, `revision_cantidad_intramural` | intramural |
| 5 | **Intramural parte 2** (fase 5) | `bacteriologas_cronograma`, `duplicado_id_codigo` | intramural |
| 6 | **Farmacia** (fase 2) | `duplicados_farmacia_farmacia` | farmacia |
| 7 | **Post-filtros legacy** (fase 6) | prioridad CC, excepciones odontología 990203/PyP | todos |

### Out of Scope

- **UI/frontend**: no hay cambios en templates, rutas HTTP ni exportación
- **Tests existentes**: se conservan y extienden, no se reescriben
- **Post-procesamiento**: `build_normalized_rows()`, `responsable_cierra` mapping, `fecha_cierre_vacia` mapping
  — son lógica de presentación/post-detección, no reglas de validación
- **Prioridad centro costo**: el filtro de prioridad (quedarse con la de prioridad 1 cuando hay
  múltiples reglas CC para mismo factura+código) se decide si va al engine como post-evaluator
  o se queda como post-procesamiento Python
- **Excepciones odontología 990203/PyP**: se evaluán si se modelan como excepciones en el engine
  (`ExceptionHandler`) o se quedan como post-filtro

---

## Approach

### Estrategia general

Cada detector legacy se mapea a una **regla en BD** (tabla `regla` + `condicion`) que el engine
ya sabe evaluar. No se toca el código del engine a menos que se requiera un evaluador nuevo.

Las 6 fases siguen orden de **complejidad ascendente**:

### Fase 1 — Transversales para áreas sin engine

**Qué**: Agregar toggle `if is_rule_engine_enabled()` en los `detect_all.py` de hospitalización,
intramural, ambulatoria, farmacia, extramural para los detectores transversales que ya existen
como reglas en BD.

**Cómo**: Patrón idéntico al de urgencias/odontología:
```python
if is_rule_engine_enabled():
    from app.services.engine.rule_based_detector import RuleBasedDetector
    from app.database import get_session
    session = get_session()
    try:
        decimales = RuleBasedDetector("valores_decimales", session).detect(...)
    finally:
        session.close()
else:
    decimales = detect_decimales(data_sheet, indices)
```

**Reglas ya existentes en BD** que aplican:
- `valores_decimales` — usado en odontología
- `tipo_documento_edad_*` (7 reglas) — usado en urgencias, odontología, equipos
- `tipo_id_requiere_entidad_86000`, `entidad_86000_requiere_as_ms`
- `codigo_entidad` — usado en urgencias
- `tipo_usuario_valido` — usado en urgencias
- `copago_entidad_valido` — usado en urgencias
- `cups_sin_contrato` — usado en urgencias
- `doble_tipo_procedimiento` — usado en odontología
- `ruta_duplicada` — usado en odontología
- `cantidad_consultas_anomalas`, `cantidad_general_anomalas`, `cantidad_pyp_anomalas` — usado en odontología

**Archivos a modificar**:
- `app/services/hospitalizacion/detect_all.py`
- `app/services/intramural/detect_all.py`
- `app/services/ambulatoria/detect_all.py`
- `app/services/farmacia/detect_all.py`
- `app/services/extramural/detect_all.py`

**Estimación**: ~50 líneas por archivo (5 archivos = ~250 líneas). Bajo riesgo.

### Fase 2 — Ambulatoria + Extramural + Farmacia

**Qué**: Agregar detectores específicos faltantes + verificar que Farmacia tenga su toggle
(`duplicados_farmacia_farmacia` → regla engine).

**Reglas necesarias**:
- `duplicados_farmacia` — ya existe en BD (usado en urgencias). Solo agregar toggle en farmacia.
- Ambulatoria y Extramural no tienen detectores específicos — solo transversales (Fase 1).

**Estimación**: ~50 líneas. Riesgo bajo.

### Fase 3 — Hospitalización

**Qué**: Migrar 4 detectores específicos + centro_costo + ide_contrato.

**Detectores**:
1. `centro_costo_hospitalizacion` — usa `apply_common_centro_costo_rules()` + reglas locales.
   Ya existe `centro_costo_check` evaluator. Requiere reglas específicas en BD.
2. `ide_contrato_urgencias` reutilizado — ya tiene regla en BD (`ide_contrato_urgencias_valido`).
3. `cantidades_hospitalizacion` — regla simple de cantidad vs umbral.
4. `cantidades_soat_hospitalizacion` — cantidad vs umbral SOAT.
5. `hospitalizacion_codes` — **complejidad**: requiere pre-scan multi-fila por factura
   (calcular estancia entre fec_factura y fecha_cierre, luego verificar códigos obligatorios/prohibidos).
   El engine soporta group-by con `DateProvider` para `date.horas`, pero la validación
   de conjuntos de códigos requiere configurar agregación `collect_set` + evaluador `set_contains_all`.
6. `copago_entidad_urgencias` reutilizado — ya tiene regla (`copago_entidad_valido`).

**Riesgo**: `hospitalizacion_codes` tiene lógica condicional (estancia >24h cambia el set de
códigos obligatorios). Esto se modela con condiciones AND/OR en el árbol.

**Esfuerzo**: ~200 líneas (reglas BD + toggle + verificación).

### Fase 4 — Intramural parte 1 (centro_costo, ide_contrato, revision_cantidad)

**Qué**: Migrar centro_costo_intramural, ide_contrato_intramural, revision_cantidad_intramural.

**centro_costo_intramural**: Es el más complejo de los centro_costo. Tiene:
- Reglas comunes 1-9 (ya existen en `centro_costo_check` evaluator)
- REGLA3-INTRAMURAL: codes PyP → centros PyP propios (distintos de Urgencias)
- REGLA6/REVERSE6: Tipo=05 + código vacunación → SALUD PUBLICA
- REGLA7/REVERSE7: Tipo=03/04 → SERVICIOS AMBULATORIOS
- REGLA10/REVERSE10: Tipo=02/05 + Lab=Si → LABORATORIO CLINICO
- REGLA_RESPONSABLE_URGENCIAS: Facturador Urgencias + Tipo 01/04 → URGENCIAS/HOSPITALIZACIÓN

Requiere **separar las reglas intramural en condiciones BD** porque el evaluador
`centro_costo_check` actual cubre solo las reglas comunes de Urgencias. Se necesitan
condiciones parametrizadas con `centros_validos` distintos.

**ide_contrato_intramural**: Similar a ide_contrato_urgencias pero con mapeo entidad→IDE
diferente. Requiere regla específica en BD.

**revision_cantidad_intramural**: Regla simple de umbral de cantidad.

**Esfuerzo**: ~350 líneas. Riesgo medio por la complejidad de las reglas de centro costo.

### Fase 5 — Intramural parte 2 (bacteriologas_cronograma, duplicado_id_codigo)

**Qué**: Migrar los dos detectores más complejos.

**bacteriologas_cronograma** (380 líneas):
- Dependencia externa: `get_turno_del_dia()` del servicio `cronograma_bacteriologas_service`
- Filtros: solo Intramural, Tipo=02/05, Lab=Si, código no en EXCEPCIONES_BACTERIOLOGA
- Lógica: parsear fecha, consultar cronograma del día, resolver nombres a códigos, verificar
  que el profesional esté en el turno
- Excepciones: PROFESIONALES_EXCEPTUADOS_CRONOGRAMA, FACTURADORES_URGENCIAS,
  responsables específicos (Chapuel→PYM, Tapia/Ordoñez→CE)

**Opción A (recomendada)**: Crear un **custom evaluator** `cronograma_check` que use
el contexto para llamar a `get_turno_del_dia()` internamente. El evaluador recibe como
`valor_esperado` los parámetros de configuración.

**Opción B**: Mantener como detector legacy e invocarlo desde el engine como
external detector hook. Contaminación arquitectónica.

**duplicado_id_codigo**: Detecta duplicados de (identificacion, codigo, fecha) → group-by
con distinct_count. El engine ya soporta esto via `GroupEvaluator`.

**Esfuerzo**: ~250 líneas (cronograma_check evaluador + regla BD para duplicado).
Riesgo medio-alto por `bacteriologas_cronograma`.

### Fase 6 — Post-filtros legacy y limpieza

**Qué**: Decidir el destino de 4 post-filtros que corren después de la detección.

| Post-filtro | Descripción | Decisión propuesta |
|------------|-------------|-------------------|
| Prioridad CC | Si múltiples reglas CC → quedarse con prioridad 1 | **Post-procesamiento** (no es regla de detección) |
| Sala observación | `detect_sala_observacion` siempre corre (sin toggle) | Ya tiene `SalaObservacionEvaluator` — revisar si el engine lo llama |
| Excepción 990203 | Odontología: código 990203 puede tener multi-tipo | **ExceptionHandler** del engine — modelar como excepción |
| Excepción PyP | Odontología: 3 facturas + código exempto | **ExceptionHandler** — modelar como excepción |
| Responsable mapping | `responsable_cierra` dict para enriquecer output | **Post-procesamiento** (no es detección) |

**Limpieza final**: Una vez que todas las áreas tengan toggle y las reglas en BD estén validadas:
1. Cambiar `is_rule_engine_enabled()` a `return True` permanentemente
2. Marcar detectores legacy como `@deprecated` o moverlos a `archive/`
3. Remover ramas `else` legacy de los `detect_all.py`

---

## Risks

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| R1 | `bacteriologas_cronograma` requiere evaluador custom que no existe | Media | Alto | Crear `cronograma_check` evaluador. Alternativa: hook detector externo |
| R2 | `hospitalizacion_codes` requiere group-by con lógica condicional (estancia >24h cambia reglas) | Media | Medio | Modelar como 2 rule configs con `filter_value` diferente en group-by |
| R3 | Diferencia de output entre engine y legacy (regression silenciosa) | Alta | Alto | Fase de snapshot testing: comparar output engine vs legacy para cada detector en cada fase |
| R4 | Centro costo intramural tiene 12 reglas muy específicas, difíciles de modelar en BD | Media | Medio | Separar en múltiples reglas más pequeñas en BD, cada una con su condición atómica |
| R5 | Excepciones odontología 990203/PyP son post-engine → decidir si van a ExceptionHandler | Baja | Bajo | Consultar al usuario en Fase 6 |
| R6 | Filtro de prioridad CC (quedarse con prioridad 1) se puede perder si el engine no lo respeta | Baja | Medio | Documentar como post-procesamiento obligatorio |

---

## Dependencies

### Engine existente (ya disponible)

| Componente | Estado | Uso en migración |
|------------|--------|------------------|
| `RuleEvaluationEngine` | ✅ Listo | Orquestador de evaluación |
| `RuleBasedDetector` | ✅ Listo | Wrapper legacy-compatible para detect_all.py |
| `ConditionEvaluator` | ✅ Listo | Árbol AND/OR/NOT |
| `GroupEvaluator` | ✅ Listo | Para duplicado_id_codigo, hospitalizacion_codes |
| `ExceptionHandler` | ✅ Listo | Para excepciones odontología |
| `EvidenceCollector` | ✅ Listo | Auditoría |
| `InvoiceProvider` | ✅ Listo | Acceso a datos de fila |
| `DateProvider` | ✅ Listo | Cálculo de edad, horas de estancia |
| `CatalogProvider` | ✅ Listo | Lookups de profesionales |
| `GroupProvider` | ✅ Listo | Acceso a agregaciones |
| `CodigoEntidadCoincideEvaluator` | ✅ Listo | Entidad vs afiliación |
| `CentroCostoCheckEvaluator` | ✅ Listo | Reglas comunes CC (1-9) |
| `SalaObservacionEvaluator` | ✅ Listo | Sala observación |
| `CupsContratadoEvaluator` | ✅ Listo | CUPS contratado |
| `CatalogInEvaluator` | ✅ Listo | Catálogos en DB |

### Evaluadores NUEVOS necesarios

| Evaluador | Para | Prioridad |
|-----------|------|-----------|
| `CronogramaCheckEvaluator` | `bacteriologas_cronograma` | **Fase 5** — custom, integra con `get_turno_del_dia()` |
| `EstanciaCheckEvaluator` (o extender GroupEvaluator) | `hospitalizacion_codes` — validar códigos según estancia | **Fase 3** — opcional, se puede modelar con condiciones existentes |

### Dependencias externas

- `cronograma_bacteriologas_service.get_turno_del_dia()` — necesario para Fase 5
- Base de datos PostgreSQL con tablas `regla`, `condicion`, `evidence`, `resultado_auditoria`

---

## Acceptance criteria

### Por fase

| Fase | Criterio de aceptación |
|------|----------------------|
| **F1** | Transversales en áreas sin engine: `is_rule_engine_enabled()` toggle agregado en 5 detect_all.py. Output idéntico con USE_RULE_ENGINE=true/false. Tests de snapshot pasando. |
| **F2a** | Farmacia: toggle agregado para `duplicados_farmacia`. Output engine = output legacy. |
| **F2b** | Ambulatoria/Extramural: transversales con toggle. Sin cambio funcional. |
| **F3** | Hospitalización: 4 detectores + CC + IDE con toggle. `hospitalizacion_codes` validado con snapshot. |
| **F4** | Intramural parte 1: CC, IDE, revision_cantidad con toggle. Output CC validado contra legacy. |
| **F5a** | `duplicado_id_codigo` migrado via GroupEvaluator. Snapshot match. |
| **F5b** | `bacteriologas_cronograma` migrado con custom evaluador o hook. Output match. |
| **F6** | Post-filtros resueltos. `is_rule_engine_enabled()` → `return True`. Ramas `else` legacy removidas. Detector legacy marcado deprecated. |

### Criterios globales

- [ ] `USE_RULE_ENGINE=false` produce output idéntico a `USE_RULE_ENGINE=true` en TODAS las áreas
- [ ] Toda detección engine deja evidencia en `evidence` y `resultado_auditoria`
- [ ] Test suite completo pasa: `pytest tests/engine/ tests/services/`
- [ ] Sin regresión en exportación (hojas de cruce y revisión)
- [ ] Sin cambios en UI/rutas/formatos de output (solo cambia el motor de detección)

---

## Review Workload Forecast

| Fase | Archivos | Líneas estimadas (netas) | Riesgo review | PRs recomendados |
|------|----------|--------------------------|---------------|------------------|
| F1 — Transversales sin engine | 5 detect_all.py | ~250 | Bajo | 1 PR (~250 líneas) |
| F2 — Ambulatoria, Extramural, Farmacia | 3 detect_all.py + reglas BD | ~100 | Bajo | 1 PR (incluir con F1) |
| F3 — Hospitalización | 4 detectores + detect_all.py + reglas BD | ~200 | Medio | 1 PR (~200 líneas) |
| F4 — Intramural parte 1 | centro_costo + ide_contrato + detect_all.py + reglas BD | ~350 | **Medio-Alto** | 2 PRs encadenados: (a) CC rules ~200, (b) IDE + revisión ~150 |
| F5 — Intramural parte 2 | bacteriologas cronograma evaluador + duplicado group-by | ~250 | **Alto** | 2 PRs: (a) custom evaluador + tests ~150, (b) regla duplicado + snapshot ~100 |
| F6 — Post-filtros + limpieza | detect_all.py (todos), limpieza legacy | ~200 | Medio | 1 PR (~200 líneas) |
| **Total** | **~20 archivos** | **~1,350 líneas** | **Medio-Alto** | **~7 PRs** |

**Guard lines**:
- `Decision needed before apply: Yes` — para R1 (custom evaluador cronograma) y R6 (post-procesamiento CC)
- `Chained PRs recommended: Yes` — para Fase 4 y Fase 5
- `400-line budget risk: Medium` — F4 se acerca, F5 requiere custom evaluador

---

## Rollback Plan

1. **Por fase**: Cada fase es autónoma. Si una fase falla en producción, desactivar
   `USE_RULE_ENGINE` → todo vuelve a legacy automáticamente.
2. **Snapshot testing**: Antes de deployar cada fase, ejecutar comparación engine vs legacy
   y verificar que los outputs son idénticos. Si hay diferencias, no deployar.
3. **Fase 6 (limpieza)**: NO remover detectores legacy hasta que todas las fases anteriores
   hayan estado en producción al menos 1 semana sin issues.

---

## Success criteria (resumen)

- [ ] 8/8 áreas ejecutan detección 100% via engine (con toggle true)
- [ ] Output idéntico entre engine y legacy en todas las áreas
- [ ] Evidencia y auditoría para todas las reglas en todas las áreas
- [ ] Tests de snapshot engine-vs-legacy para cada detector migrado
