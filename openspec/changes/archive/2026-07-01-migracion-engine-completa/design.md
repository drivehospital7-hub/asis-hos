# Design: Migración completa al Rule Engine

## 1. Technical Approach

Migrar **todos los detectores legacy** (12 archivos, ~2,800 líneas) de 5 áreas sin toggle (`hospitalizacion`, `intramural`, `ambulatoria`, `extramural`, `farmacia`) al engine existente en 6 fases secuenciales. Cada fase:
- Agrega toggle `if is_rule_engine_enabled()` en el `detect_all.py` del área
- Crea/migra reglas BD con evaluadores existentes o 1 nuevo (`CronogramaCheckEvaluator`)
- Incluye snapshot testing engine-vs-legacy antes de considerar la fase completa

El engine (18 evaluadores, 5 providers, GroupEvaluator, ExceptionHandler) **no necesita refactor** — solo se registra 1 evaluador nuevo. El cambio es 100% configuración BD + wiring en los detect_all.py.

---

## 2. Architecture Decisions

### Decision: Cada fase es autónoma y toggleable

**Choice**: Toggle `if is_rule_engine_enabled()` individual por detector en cada `detect_all.py`, no un toggle global por área.  
**Alternatives**: Toggle por área completo.  
**Rationale**: Permite rollback granular. Si `hospitalizacion_codes` falla, se desactiva solo ese detector. Además, es el patrón ya usado en odontología/urgencias.

### Decision: CentroCostoIntramuralEvaluator como clase separada (no herencia)

**Choice**: Nueva clase `CentroCostoIntramuralEvaluator` que copia las reglas 1-9 comunes y agrega las 5 reglas intramural.  
**Alternatives**: Herencia de `CentroCostoCheckEvaluator` + parámetros.  
**Rationale**: El evaluador común está hardcodeado con constantes de Urgencias (`CODIGOS_PYP_URGENCIAS`, `CC_PYP`). Una clase separada permite tener sus propias constantes sin acoplar. En Fase 7+ se podría refactorizar a un evaluador parametrizable vía BD.

### Decision: CronogramaCheckEvaluator como evaluador custom atómico

**Choice**: Implementar `cronograma_check` operator en `evaluators.py` (mismo archivo que los 18 existentes).  
**Alternatives**: Hook externo, mantenedor legacy, provider custom.  
**Rationale**: Mismo patrón que `CupsContratadoEvaluator` (DB lookups + lógica condicional). El evaluador usa `EvaluationContext.session` para llamar a `get_turno_del_dia()` con cache por sesión.

### Decision: hospitalizacion_codes como 2 rule configs con filter_value

**Choice**: Dos rule configs en `parametros` del engine:
1. `filter_value: ">24h"` → GroupEvaluator con `set_contains_all` para códigos obligatorios completos
2. `filter_value: "<=24h"` → GroupEvaluator con `set_contains_all` para set restringido

**Alternatives**: Un solo group-by con lógica condicional en el evaluador.  
**Rationale**: El engine ya soporta `filter_field`/`filter_value` en `build_groups()`. Dos configs evitan crear un evaluador nuevo.

### Decision: duplicado_id_codigo via GroupEvaluator extendido

**Choice**: Agregar agregación `collect_groups(fields)` al `GroupEvaluator` que retorne la lista de facturas/grupos.  
**Alternatives**: AllValuesMatchEvaluator con threshold.  
**Rationale**: `collect_group_keys` permite devolver las facturas individuales del grupo duplicado, no solo la factura del group-by. Requiere extender `_agg_*` en `GroupEvaluator`.

### Decision: Prioridad CC y post-procesamiento quedan como Python

**Choice**: El filtro de prioridad (quedarse con prioridad 1 cuando múltiples reglas CC coinciden) sigue siendo post-procesamiento Python.  
**Rationale**: Opera sobre el OUTPUT de detección, no sobre filas de entrada. Meterlo en el engine requeriría un post-evaluador que en este caso no aporta valor.

---

## 3. Fase 1: Transversales para áreas sin engine

### 3.1 Archivos a modificar

| Archivo | Acción | Líneas estimadas |
|---------|--------|------------------|
| `app/services/hospitalizacion/detect_all.py` | Agregar toggle para 10 detectores transversales | ~100 |
| `app/services/intramural/detect_all.py` | Agregar toggle para 7 detectores transversales | ~80 |
| `app/services/ambulatoria/detect_all.py` | Agregar toggle para 7 detectores transversales | ~80 |
| `app/services/extramural/detect_all.py` | Agregar toggle para 7 detectores transversales | ~80 |
| `app/services/farmacia/detect_all.py` | Agregar toggle para 7 detectores transversales | ~80 |

### 3.2 Reglas engine a usar (ya existen en BD)

| Detector legacy | Regla engine |
|----------------|--------------|
| `detect_decimales` | `valores_decimales` |
| `detect_tipo_documento_edad` | `tipo_documento_edad_*` (7 reglas) |
| `detect_tipo_identificacion_entidad` | `tipo_id_requiere_entidad_86000` + `entidad_86000_requiere_as_ms` |
| `detect_codigo_entidad_vs_entidad_afiliacion` | `codigo_entidad` |
| `detect_tipo_usuario` | `tipo_usuario_valido` |
| `detect_copago_entidad_urgencias` | `copago_entidad_valido` |
| `detect_cups_sin_contrato` | `cups_sin_contrato` |
| `detect_cantidades_hospitalizacion` | `cantidad_consultas_anomalas` + `cantidad_general_anomalas` + `cantidad_pyp_anomalas` (solo hosp) |
| `detect_cantidades_soat_hospitalizacion` | No existe aún → crear regla `cantidades_soat_hospitalizacion` |
| `detect_hospitalizacion_codes` | No existe aún → Fase 3 |

### 3.3 Toggle code pattern (idéntico a odontología/urgencias)

```python
if is_rule_engine_enabled():
    from app.services.engine.rule_based_detector import RuleBasedDetector
    from app.database import get_session
    session = get_session()
    try:
        decimales = RuleBasedDetector("valores_decimales", session).detect(data_sheet, indices, persist=_PERSIST)
        if _PERSIST:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()
else:
    decimales = detect_decimales(data_sheet, indices)
```

### 3.4 Tests

- `tests/services/hospitalizacion/test_detect_all_transversales.py` — snapshot engine vs legacy
- `tests/services/intramural/test_detect_all_transversales.py`
- `tests/services/ambulatoria/test_detect_all_transversales.py`
- `tests/services/extramural/test_detect_all_transversales.py`
- `tests/services/farmacia/test_detect_all_transversales.py`

---

## 4. Fase 2: Farmacia específico + Ambulatoria/Extramural

### 4.1 Archivos a modificar

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `app/services/farmacia/detect_all.py` | Agregar toggle para `detect_duplicados_farmacia_farmacia` | ~30 |
| `app/services/farmacia/duplicados_farmacia_farmacia.py` | Sin cambios (legacy se mantiene para rollback) | 0 |

### 4.2 Regla engine a crear

| Nombre | Domain | Evaluador | Params |
|--------|--------|-----------|--------|
| `duplicados_farmacia_farmacia` | `farmacia` | `GroupEvaluator` + `collect_value_counts` + `all_values_match(threshold=2)` | `group_by=numero_factura`, `filter_field=tipo_factura_descripcion`, `filter_value=Farmacia` |

### 4.3 Nota

Ambulatoria y Extramural **no** tienen detectores específicos — Fase 1 ya las cubre completamente.

---

## 5. Fase 3: Hospitalización

### 5.1 Archivos a modificar

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `app/services/hospitalizacion/detect_all.py` | Agregar toggle para 5 detectores específicos | ~80 |
| `app/services/engine/evaluators.py` | Sin cambios (usa evaluadores existentes) | 0 |

### 5.2 Reglas engine a crear

| Nombre | Evaluador | Condición |
|--------|-----------|-----------|
| `centro_costo_hospitalizacion_valido` | `centro_costo_check` | — |
| `ide_contrato_hospitalizacion_valido` | Reusa `ide_contrato_urgencias_valido` | — |
| `cantidades_hospitalizacion` | `gt(cantidad, 8)` | — |
| `cantidades_soat_hospitalizacion` | `AND(eq(tarifario, "SOAT"), gt(cantidad, 2))` | — |

### 5.3 hospitalizacion_codes como 2 rule configs

```python
# Rule config 1: estancia > 24h
parametros = [
    {
        "group_by": "numero_factura",
        "filter_field": "estancia_horas",
        "filter_value": ">24",
        "aggregations": [
            {"function": "collect_set", "field": "codigo", "target": "codigos_presentes"}
        ]
    }
]
# Condition tree: NOT(set_contains_all(codigos_presentes, CODIGOS_HOSPITALIZACION_OBLIGATORIOS))

# Rule config 2: estancia <= 24h  
parametros = [
    {
        "group_by": "numero_factura",
        "filter_field": "estancia_horas",
        "filter_value": "<=24",
        "aggregations": [
            {"function": "collect_set", "field": "codigo", "target": "codigos_presentes"}
        ]
    }
]
# Condition tree: NOT(set_contains_all(codigos_presentes, {"890601H", "129B02"}))
```

**Problema**: El engine actual filtra por valor de columna directa, no por `date.horas` computado.  
**Solución**: Extender `build_groups()` para aceptar `filter_function` opcional que permita filtrar por valor computado. O, más simple: **pre-calcular `date.horas` y almacenarlo en `invoice_data`** antes del group-by, igual que se hace con `date.edad` en la línea 118-123 de `engine.py`. Esto ya está implementado para row-by-row, solo falta extenderlo a group-by.

---

## 6. Fase 4: Intramural parte 1 — centro_costo, IDE, revision_cantidad

### 6.1 Archivos a modificar/crear

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `app/services/engine/evaluators.py` | Agregar `CentroCostoIntramuralEvaluator` | ~120 |
| `app/services/intramural/detect_all.py` | Agregar toggle para centro_costo, IDE, revision_cantidad | ~60 |
| BD | Crear reglas `centro_costo_intramural_valido`, `ide_contrato_intramural_valido`, `revision_cantidad_intramural` | — |

### 6.2 CentroCostoIntramuralEvaluator

```python
class CentroCostoIntramuralEvaluator(AtomicEvaluator):
    """Centro de costo rules for Intramural: common (1-9 except 3) + 5 specific."""
    operator = "centro_costo_intramural"

    def evaluate(self, condition, row_value, expected, context=None):
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}
        centro = str(inv.get("centro_costo", "")).strip().upper()
        codigo = str(inv.get("codigo", "")).strip().upper()
        cod_tipo = str(inv.get("codigo_tipo_procedimiento", "")).strip().upper()
        lab = str(inv.get("laboratorio", "")).strip().upper()
        tarif = str(inv.get("tarifario", "")).strip().upper()
        responsable = str(inv.get("responsable_cierra", "")).strip().upper()
        
        if not centro:
            return False
        
        # ── Common rules (same as CentroCostoCheckEvaluator except REGLA3) ──
        # REGLA9: Tarifario farmacia → centro=FARMACIA
        # REGLA1: Cod=diagnostico + Lab=NO → centro=APOYO_DIAG
        # REVERSE1: centro=APOYO_DIAG → cod=diag + lab=NO
        # REGLA2: Cod=traslados → centro=TRASLADOS
        # REVERSE2: centro=TRASLADOS → cod=traslados
        # REGLA4: Cod quirofano → centro=QUIROFANO
        # REVERSE4: centro=QUIROFANO → cod quirofano
        # REGLA9REVERSE: centro=FARMACIA → tarifario farmacia
        # REGLA8: Cod hospitalizacion → centro=HOSPITALIZACION
        
        # ── Intramural-specific rules ──
        # REGLA3-INTRAMURAL: codigo in CODIGOS_PYP_URGENCIAS → CC in CENTROS_COSTO_PYP_INTRAMURAL
        # REGLA6: tipo=05 + codigo not in CODIGOS_EXCLUIDOS_VACUNACION → CC=SALUD PUBLICA
        # REVERSE6: CC=SALUD PUBLICA → tipo=05
        # REGLA7: tipo=03/04 → CC=SERVICIOS AMBULATORIOS
        # REVERSE7: CC=SERVICIOS AMBULATORIOS → tipo=03/04
        # REGLA10: tipo=02/05 + Lab=Si → CC in CENTROS_COSTO_LABORATORIO_VALIDOS
        # REVERSE10: CC in CENTROS_LAB → tipo=02/05 + Lab=Si
        # REGLA_RESPONSABLE_URGENCIAS: responsable in FACTURADORES_URGENCIAS + tipo=01/04 → CC=URGENCIAS|HOSP
        
        return False
```

### 6.3 Reglas engine

| Nombre | Evaluador | Params |
|--------|-----------|--------|
| `centro_costo_intramural_valido` | `centro_costo_intramural` | — |
| `ide_contrato_intramural_valido` | `eq` + `in` | Mapeo entidad→IDE intramural |
| `revision_cantidad_intramural` | `AND/OR` cascade | 3 thresholds: tipo02+lab=No→>2, tipo03/04→>12, default→>1 |

---

## 7. Fase 5: Intramural parte 2 — CronogramaCheckEvaluator, duplicado_id_codigo

### 7.1 Archivos a modificar/crear

| Archivo | Acción | Líneas |
|---------|--------|--------|
| `app/services/engine/evaluators.py` | Agregar `CronogramaCheckEvaluator` | ~120 |
| `app/services/engine/group_evaluator.py` | Agregar agregación `collect_group_keys` | ~20 |
| `app/services/intramural/detect_all.py` | Agregar toggle para cronograma + duplicado_id | ~50 |

### 7.2 CronogramaCheckEvaluator — diseño completo

```python
class CronogramaCheckEvaluator(AtomicEvaluator):
    """Valida profesional contra cronograma del día para Intramural.
    
    Operator: cronograma_check
    row_value: codigo_profesional from sheet
    expected: dict with filter params or None
    """
    operator = "cronograma_check"
    
    def __init__(self):
        self._cronograma_cache: dict[tuple[int, int, int, str | None], list[dict]] = {}
    
    def evaluate(self, condition, row_value, expected, context=None):
        if context is None:
            return False
        inv = getattr(context, "invoice_data", {}) or {}
        codigo_prof = str(row_value).strip() if row_value else ""
        if not codigo_prof:
            return False
        
        # 1. Filter: solo Intramural, tipo in {"02","05"}
        tipo_factura = str(inv.get("tipo_factura_descripcion", "")).strip()
        if tipo_factura != "Intramural":
            return False
        tipo_proc = str(inv.get("codigo_tipo_procedimiento", "")).strip()
        if tipo_proc not in ("02", "05"):
            return False
        # tipo="02" requiere lab="Si"
        if tipo_proc == "02":
            lab = str(inv.get("laboratorio", "")).strip().upper()
            if lab not in ("SI", "SÍ"):
                return False
        
        # 2. Filter: codigo not in EXCEPCIONES_BACTERIOLOGA
        codigo = str(inv.get("codigo", "")).strip()
        if codigo in EXCEPCIONES_BACTERIOLOGA:
            return False
        
        # 3. Bypass: responsable in FACTURADORES_URGENCIAS → normal
        responsable = str(inv.get("responsable_cierra", "")).strip()
        responsable_norm = " ".join(responsable.upper().split())
        if responsable_norm in _FACTURADORES_URGENCIAS_NORM:
            return False  # bypass total
        
        # 4. Bypass: codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA
        if codigo_prof in PROFESIONALES_EXCEPTUADOS_CRONOGRAMA:
            return False
        
        # 5. Parse fec_factura
        fec_raw = inv.get("fec_factura")
        fecha = self._parse_fecha(fec_raw)
        if fecha is None:
            return False
        
        # 6. Determine siglas_filter
        responsable_full = " ".join((responsable or "").upper().split())
        siglas_filter = None  # default: CE|PYM
        if "CHAPUEL" in responsable_full:
            siglas_filter = {"PYM"}
        elif "TAPIA" in responsable_full or "ORDOÑEZ" in responsable_full:
            siglas_filter = {"CE"}
        
        # 7. Get turnos with session-level cache
        cache_key = (fecha.month, fecha.year, fecha.day, 
                     tuple(sorted(siglas_filter)) if siglas_filter else None)
        if cache_key not in self._cronograma_cache:
            from app.services.cronograma_bacteriologas_service import get_turno_del_dia
            turnos = get_turno_del_dia(
                fecha.month, fecha.year, fecha.day,
                siglas_filter=siglas_filter
            )
            self._cronograma_cache[cache_key] = turnos
        
        turnos = self._cronograma_cache[cache_key]
        if not turnos:
            return False  # no hay cronograma → skip sin error
        
        # 8. Resolve cronograma names to codes via CatalogProvider
        codigos_en_turno = set()
        for t in turnos:
            nombre = t.get("nombre", "").strip().upper()
            if nombre:
                # Use existing reverse lookup from legacy
                cod = _NOMBRE_A_CODIGO.get(nombre)
                if cod:
                    codigos_en_turno.add(cod)
        
        # 9. Verify professional is in turno
        if codigo_prof not in codigos_en_turno:
            return True  # MATCH = detection (problema encontrado)
        
        return False  # en turno → no detection
```

#### Mapeo de constantes legacy

| Constante legacy | Origen | En engine |
|-----------------|--------|-----------|
| `EXCEPCIONES_BACTERIOLOGA` | `constants/urgencias.py` | Constante Python importada |
| `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` | `constants/intramural.py` | Constante Python importada |
| `FACTURADORES_URGENCIAS` | `constants/urgencias.py` | Constante Python importada (normalizada) |
| `PROFESIONALES_URGENCIAS` | `constants/urgencias.py` | Cargado via `_build_nombre_a_codigo()` (module-level) |
| `RESPONSABLE_CHAPUEL`, `RESPONSABLE_TAPIA`, `RESPONSABLE_ORDONEZ` | `constants/intramural.py` | Check via `contains` en nombre normalizado |

**Cache**: El evaluador tiene un cache interno de `turnos` por `(mes, año, día, siglas_filter)` para evitar múltiples llamadas a `get_turno_del_dia()` por cada fila del mismo día.

### 7.3 duplicado_id_codigo via GroupEvaluator

**Necesita extensión menor en GroupEvaluator**: agregar `collect_group_keys()` que retorne las claves del grupo (facturas) para poder listar facturas duplicadas en el output.

```python
# Rule config
parametros = [{
    "group_by": "(identificacion, codigo, dx_principal)",
    "filter_field": "codigo_tipo_procedimiento",
    "filter_value": "02 OR 05",  # necesita soporte OR o 2 rule configs
    "aggregations": [
        {"function": "group_size", "target": "count"},
        {"function": "collect_group_keys", "field": "numero_factura", "target": "facturas"}
    ]
}]
# Condition: gte(count, threshold)
# threshold dinámico: tipo=05 → 2, tipo=02+Lab=Si → 4
```

**Problema**: El filtro OR (`02 OR 05`) no está soportado por `build_groups()`.  
**Solución**: Crear 2 rule configs, una para tipo=02-LAB=Si con threshold=4, otra para tipo=05 con threshold=2.

---

## 8. Fase 6: Post-filtros legacy y limpieza

### 8.1 Decisiones

| Post-filtro | Decisión | Justificación |
|------------|----------|---------------|
| Prioridad CC (prioridad=1 wins) | **Queda como post-procesamiento Python** | Opera sobre output de detección, no sobre filas |
| Excepción 990203 (odontología) | **ExceptionHandler** | Crear Excepcion en BD: `rule=doble_tipo_procedimiento`, `tipo_efecto=suspension` |
| Excepción PyP (odontología ruta_duplicada) | **ExceptionHandler** | Crear Excepcion en BD: `rule=ruta_duplicada`, `tipo_efecto=override` con threshold=4 |
| Sala observación | **Verificar** que `SalaObservacionEvaluator` está registrado y se llama en engine path |
| Responsable/fecha mapping | **Queda como post-procesamiento** | No es detección |

### 8.2 Limpieza final

```python
# app/constants/base.py
def is_rule_engine_enabled() -> bool:
    return True  # WAS: os.getenv("USE_RULE_ENGINE", "false").lower() == "true"
```

- Remover ramas `else` de todos los `detect_all.py`
- Marcar detectores legacy como `@deprecated`
- Mover detectores legacy a `archive/` (opcional)

---

## 9. Plan de reglas BD (tabla completa)

| Nombre regla | Dominio | Severidad | Evaluador | Condiciones clave |
|-------------|---------|-----------|-----------|-------------------|
| `valores_decimales` | transversal | error | regex | `regex("\.\d{3,}")` en `vlr_unitario`, `vlr_procedimiento` |
| `tipo_documento_edad_menor_7` | transversal | error | AND | edad<7 AND tipo_doc!="RC" |
| `tipo_documento_edad_mayor_18` | transversal | error | AND | edad>18 AND tipo_doc not in ("CC","CE","MS","AS") |
| `tipo_documento_edad_7_17` | transversal | error | AND | edad>=7 AND edad<=17 AND tipo_doc!="TI" |
| `tipo_documento_edad_as_menor` | transversal | error | AND | tipo_doc="AS" AND edad>=18 |
| `tipo_documento_edad_ms_mayor` | transversal | error | AND | tipo_doc="MS" AND edad>60 |
| `tipo_documento_edad_cn_invalido` | transversal | error | AND | tipo_doc="CN" AND ... |
| `tipo_documento_edad_ce_invalido` | transversal | error | AND | tipo_doc="CE" AND edad>18 |
| `tipo_id_requiere_entidad_86000` | transversal | error | AND | tipo_id=... AND ... |
| `entidad_86000_requiere_as_ms` | transversal | error | AND | ... |
| `codigo_entidad` | transversal | error | `ent_code_match` | código extraído de entidad_afiliacion != codigo_entidad_cobrar |
| `tipo_usuario_valido` | transversal | error | `in` | tipo_usuario in TIPO_USUARIO_VALORES |
| `copago_entidad_valido` | transversal | error | centro_costo_check | copago vs entidad |
| `cups_sin_contrato` | transversal | error | `cups_contratado` | CUPS no contratado |
| `cantidad_consultas_anomalas` | transversal | warning | `gte` | cantidad >= 2 |
| `cantidad_general_anomalas` | transversal | warning | `gt` | cantidad > 10 |
| `cantidad_pyp_anomalas` | transversal | warning | `gte` | cantidad >= 3 (PyP) |
| `duplicados_farmacia_farmacia` | farmacia | error | GroupEvaluator | `all_values_match(count>=2)` |
| `centro_costo_hospitalizacion_valido` | hospitalizacion | error | `centro_costo_check` | centros hospitalización |
| `ide_contrato_hospitalizacion_valido` | hospitalizacion | error | eq | mapeo entidad→IDE hosp |
| `cantidades_hospitalizacion` | hospitalizacion | warning | `gt(cantidad, 8)` | — |
| `cantidades_soat_hospitalizacion` | hospitalizacion | warning | AND | tarifario=SOAT AND cantidad>2 |
| `hospitalizacion_codes_estancia_mayor_24h` | hospitalizacion | error | GroupEvaluator + `set_contains_all` | estancia>24h, mandatory codes |
| `hospitalizacion_codes_estancia_menor_24h` | hospitalizacion | error | GroupEvaluator + `set_contains_all` | estancia<=24h, restringed set |
| `centro_costo_intramural_valido` | intramural | error | `centro_costo_intramural` | 5 reglas intramural |
| `ide_contrato_intramural_valido` | intramural | error | eq | mapeo entidad→IDE intramural |
| `revision_cantidad_intramural` | intramural | warning | AND/OR cascade | 3 thresholds |
| `bacteriologas_cronograma` | intramural | error | **`cronograma_check`** | Validación vs cronograma |
| `duplicado_id_codigo_05` | intramural | error | GroupEvaluator | tipo=05, threshold=2, excluye CODIGOS_EXENTOS_05 |
| `duplicado_id_codigo_02_lab` | intramural | error | GroupEvaluator | tipo=02+Lab=Si, threshold=4 |

---

## 10. Estrategia de testing

### 10.1 Tests de snapshot por fase

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

### 10.2 Tests unitarios para CronogramaCheckEvaluator

```python
@pytest.fixture
def mock_get_turno_del_dia(mocker):
    return mocker.patch(
        "app.services.cronograma_bacteriologas_service.get_turno_del_dia"
    )

def test_cronograma_profesional_en_turno(mock_get_turno_del_dia):
    mock_get_turno_del_dia.return_value = [
        {"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE/PYM"}
    ]
    context = EvaluationContext(invoice_data={
        "tipo_factura_descripcion": "Intramural",
        "codigo_tipo_procedimiento": "02",
        "laboratorio": "Si",
        "codigo": "901210",
        "responsable_cierra": "",
        "fec_factura": "2024-06-01",
    })
    evaluator = CronogramaCheckEvaluator()
    result = evaluator.evaluate({}, "03374", None, context=context)
    assert result is False  # No detection = professional in turno

def test_cronograma_profesional_fuera_turno(mock_get_turno_del_dia):
    mock_get_turno_del_dia.return_value = []
    context = EvaluationContext(invoice_data={
        "tipo_factura_descripcion": "Intramural",
        "codigo_tipo_procedimiento": "02",
        "laboratorio": "Si",
        "codigo": "901210", 
        "responsable_cierra": "",
        "fec_factura": "2024-06-01",
    })
    evaluator = CronogramaCheckEvaluator()
    result = evaluator.evaluate({}, "03374", None, context=context)
    assert result is True  # Detection = not in turno

def test_cronograma_bypass_exceptuado(mock_get_turno_del_dia):
    """02217 (MADROÑERO) bypassa cronograma."""
    # No se llama a get_turno_del_dia
    context = EvaluationContext(invoice_data={
        "tipo_factura_descripcion": "Intramural",
        "codigo_tipo_procedimiento": "02",
        "laboratorio": "Si",
        "codigo": "901210",
        "responsable_cierra": "",
        "fec_factura": "2024-06-01",
    })
    evaluator = CronogramaCheckEvaluator()
    result = evaluator.evaluate({}, "02217", None, context=context)
    assert result is False  # bypass = no detection

def test_cronograma_chapuel_solo_pym(mock_get_turno_del_dia):
    """Chapuel filtra solo sigla PYM."""
    # El mock devuelve solo CE → detection
    mock_get_turno_del_dia.return_value = [
        {"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE"}
    ]
    context = EvaluationContext(invoice_data={
        "tipo_factura_descripcion": "Intramural",
        "codigo_tipo_procedimiento": "02",
        "laboratorio": "Si",
        "codigo": "901210",
        "responsable_cierra": "CHAPUEL CASANOVA ANGIE TATIANA",
        "fec_factura": "2024-06-01",
    })
    evaluator = CronogramaCheckEvaluator()
    result = evaluator.evaluate({}, "03374", None, context=context)
    assert result is True  # Detection = solo PYM filter, pero solo CE
```

### 10.3 Validación output idéntico

Para CADA fase, antes de dar por completa la migración:

1. Preparar 3-5 Excels de prueba por área (normal, errores mixtos, casos borde)
2. Ejecutar con `USE_RULE_ENGINE=false` → guardar output legacy
3. Ejecutar con `USE_RULE_ENGINE=true` → guardar output engine
4. Comparar `resultado["problemas"][detector]` para cada detector migrado
5. Diferencia = fase no lista para deploy

### 10.4 Excels de prueba necesarios

| Escenario | Descripción |
|-----------|-------------|
| hospitalizacion_normal.xlsx | 50 facturas correctas |
| hospitalizacion_errores.xlsx | Errores mixtos: decimales, códigos, cantidades |
| hospitalizacion_estancias.xlsx | 15 facturas: 0-72h, combinaciones de códigos |
| intramural_normal.xlsx | 50 facturas correctas |
| intramural_cc_complejo.xlsx | 30 facturas cubriendo 12 reglas CC |
| intramural_cronograma.xlsx | 20 facturas con combinaciones responsable×sigla |
| intramural_duplicados.xlsx | Duplicados variados cross-tipo |
| farmacia_normal.xlsx | 30 facturas farmacia |
| ambulatoria_normal.xlsx | 30 facturas ambulatoria |
| extramural_normal.xlsx | 30 facturas extramural |

---

## 11. Resumen de líneas por fase

| Fase | Archivos | Líneas netas estimadas | Riesgo |
|------|----------|------------------------|--------|
| F1 — Transversales | 5 detect_all.py | ~420 | Bajo |
| F2 — Farmacia | 1 detect_all.py + 1 regla BD | ~30 | Bajo |
| F3 — Hospitalización | 1 detect_all.py + 6 reglas BD + engine.py (menor) | ~120 | Medio |
| F4 — Intramural CC+IDE | 1 evaluador + 1 detect_all.py + 3 reglas BD | ~250 | Medio-Alto |
| F5a — Cronograma | 1 evaluador (120ln) + tests (80ln) + detect_all.py | ~250 | Alto |
| F5b — Duplicado ID | 1 GroupEvaluator extension + detect_all.py | ~80 | Medio |
| F6 — Post-filtros+limpieza | constants/base.py + detect_all.py | ~50 | Bajo |
| **Total** | ~18 archivos | ~1,200 | **Medio-Alto** |
