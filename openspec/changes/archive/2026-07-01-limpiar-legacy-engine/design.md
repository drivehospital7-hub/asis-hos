# Design: Limpiar legacy restante en engine

## Technical Approach

Cerrar los 9 huecos legacy que aún bypassean el Rule Engine + los 6 `else` clauses faltantes. Tres fases: (1) dos evaluadores engine nuevos, (2) toggles + else, (3) reglas BD.

---

## Architecture Decisions

### 1: RevisionCantidadUrgenciasEvaluator — row-level, no group-by

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| GroupEvaluator (sum por factura) | Requiere group-by engine, no replica lógica de thresholds específicos por código | ❌ |
| Row-level AtomicEvaluator (como revision_cantidad_intramural) | Misma firma, mismo patrón, cascade de thresholds por código/tipo/lab | ✅ |
| Legacy: `detect_revision_cantidad_urgencias` | Ya existe, se reemplaza | ❌ |

**Rationale**: El patrón row-level es idéntico a `RevisionCantidadIntramuralEvaluator`. La lógica de cascade con `CODIGOS_LIMITE_ESPECIFICO`, `CODIGOS_REVISION_CANTIDAD_EXENTOS`, y reglas por `codigo_tipo_procedimiento + laboratorio` se replica exactamente. No hay agrupación por factura en el legacy — cada fila se evalúa independientemente.

### 2: CupsEquivalentesTransversalEvaluator — row-level con dict estático

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Condiciones estáticas en BD (como cups_equivalentes actual) | Escalaría mal — cada nuevo par requiere nueva condición OR | ❌ |
| Row-level AtomicEvaluator con `CODIGOS_CUPS_EQUIVALENTES` hardcodeado | Mismo patrón que otros evaluadores, el dict ya existe en `cups_equivalentes.py` | ✅ |
| DB-backed catalog | Overkill para 2 pares estáticos | ❌ |

**Rationale**: El mapeo `{"906317": "1906317", "906249": "906249PR"}` es estático y definido por normativa. Un evaluador row-level que hace `dict.get(codigo)` es 10x más simple que 2+ condiciones compuestas en BD. Se registra con `operator = "cups_equiv_transversal_check"`.

### 3: Toggle wrapping — patrón exacto

```
if is_rule_engine_enabled():
    from app.services.engine.rule_based_detector import RuleBasedDetector
    from app.database import get_session
    session = get_session()
    try:
        var = RuleBasedDetector("rule_name", session).detect(...)
        if _PERSIST:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()
```

**Rationale**: Es el patrón usado en los 35 detectores ya migrados. Consistencia total. No inventar nuevo patrón.

### 4: Else clauses — `else: var = []`

**Rationale**: Sin `else`, si `is_rule_engine_enabled()` retornara `False`, la variable quedaría sin asignar → `UnboundLocalError`. Agregar `else: var = []` previene el crash.

---

## Data Flow

```
unified_processor.py (antes)
  └─ detect_cups_equivalentes_transversal()  ← legacy puro, sin toggle

unified_processor.py (después)
  ├─ detect_cups_equivalentes_transversal()    ← legacy (fallback si engine off)
  └─ if is_rule_engine_enabled():
       RuleBasedDetector("cups_equivalentes_transversal", session)  ← engine path


urgencias/detect_all.py (antes)
  └─ revision_cantidad = detect_revision_cantidad_urgencias()  ← legacy puro

urgencias/detect_all.py (después)
  ├─ revision_cantidad = detect_revision_cantidad_urgencias()  ← legacy fallback
  └─ if is_rule_engine_enabled():
       RuleBasedDetector("revision_cantidad_urgencias_valido", session)  ← engine path
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/evaluators.py` | Modify | +2 evaluadores: `RevisionCantidadUrgenciasEvaluator`, `CupsEquivalentesTransversalEvaluator`. Registrar en `_register_builtins()`. |
| `app/services/urgencias/detect_all.py` | Modify | Toggle para `revision_cantidad` (line 289). |
| `app/services/equipos_basicos/detect_all.py` | Modify | Toggle para `decimales`, `ruta_duplicada`, `cantidades_anomalas`, `ide_contrato`. Else clause para `doble_tipo`, `centro_costo`. |
| `app/services/hospitalizacion/detect_all.py` | Modify | Toggle para `ide_contrato`, `profesionales`. Else clause para `decimales`, `tipo_identificacion_edad`, `cantidades_hospitalizacion`, `cantidades_soat_hospitalizacion`. |
| `app/services/unified_processor.py` | Modify | Toggle para `cups_equivalentes_transversal`. |

---

## Interfaces / Contracts

```python
class RevisionCantidadUrgenciasEvaluator(AtomicEvaluator):
    """Row-level cascade threshold check for Urgencias quantity revisions.

    Operator: revision_cantidad_urgencias_check

    Returns True if cantidad exceeds the applicable threshold (detection).
    row_value: cantidad from invoice.
    context.invoice_data: full invoice row for cascade logic.

    Cascade (mirrors detect_revision_cantidad_urgencias):
    1. Check CODIGOS_REVISION_CANTIDAD_EXENTOS → continue (no detection)
    2. Check CODIGOS_LIMITE_ESPECIFICO → if cantidad <= limit, return False
    3. tipo=02 + Lab=No → Cant > 2 (codigo=903883: Cant > 5)
    4. tipo in 09/12 → Cant > 20 (codigo=V03AN0101: always allow)
    5. General → Cant > 1
    """
    operator = "revision_cantidad_urgencias_check"

    def evaluate(self, condition, row_value, expected, context=None) -> bool:
        ...


class CupsEquivalentesTransversalEvaluator(AtomicEvaluator):
    """Check if CUPS code has a known equivalent replacement.

    Operator: cups_equiv_transversal_check

    Returns True if codigo has an equivalent (detection = should replace).
    row_value: codigo from invoice.

    Uses CODIGOS_CUPS_EQUIVALENTES from cups_equivalentes.py.
    """
    operator = "cups_equiv_transversal_check"

    def evaluate(self, condition, row_value, expected, context=None) -> bool:
        ...
```

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `RevisionCantidadUrgenciasEvaluator.evaluate()` | Cascade thresholds: exentos, límites específicos, tipo 02+Lab, 09/12, general |
| Unit | `CupsEquivalentesTransversalEvaluator.evaluate()` | Códigos con/sin equivalente, códigos vacíos, case sensitivity |
| Unit | Registry | Ambos evaluadores registrados en `EVALUATOR_REGISTRY` |
| Snapshot | Engine vs legacy | Comparar output de engine path vs legacy path para ambos detectores |
| Integration | Toggle + else | Verificar que detect_all y unified_processor no crashean con engine disabled |

---

## Migration / Rollout

No migration required. `is_rule_engine_enabled()` retorna `True` siempre — la BD rules son el único path activo. Los nuevos evaluadores se registran en `_register_builtins()` y las reglas BD se insertan via script SQL/migration.

---

## Plan de reglas BD

```sql
-- Regla: revision_cantidad_urgencias_valido (dominio: urgencias)
INSERT INTO reglas (nombre, descripcion, dominio, estado, prioridad, severidad, activo, parametros)
VALUES (
  'revision_cantidad_urgencias_valido',
  'Detecta filas con cantidad anómala en Urgencias (thresholds por código/tipo/lab)',
  'urgencias', 'active', 100, 'warning', true,
  '[]'  -- sin group-by, row-level
);

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (currval('reglas_id_seq'), NULL, 'atomic', 'revision_cantidad_urgencias_check', 'invoice.cantidad', NULL, 0);


-- Regla: cups_equivalentes_transversal (dominio: transversal)
INSERT INTO reglas (nombre, descripcion, dominio, estado, prioridad, severidad, activo, parametros)
VALUES (
  'cups_equivalentes_transversal',
  'Detecta códigos CUPS con equivalente conocido (906317→1906317, 906249→906249PR)',
  'transversal', 'active', 100, 'warning', true,
  '[]'
);

INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (currval('reglas_id_seq'), NULL, 'atomic', 'cups_equiv_transversal_check', 'invoice.codigo', NULL, 0);
```

---

## Open Questions

- [ ] `revision_cantidad_urgencias` filtra por `tipo_factura_descripcion == "Urgencias"` — el dominio `urgencias` ya filtra en `RuleResolver`, ¿necesitamos el filtro extra en el evaluador o lo maneja el dominio?
  - **Respuesta**: El dominio `urgencias` en `RuleResolver` filtra qué reglas cargar, pero el evaluador NO recibe el tipo de factura — `invoice_data` sí lo tiene. Mejor mantener el filtro en el evaluador por si la regla se llama desde otro dominio. Si no, confirmar y remover.
