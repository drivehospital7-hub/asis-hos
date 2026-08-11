# Design: Migrar detectores legacy restantes

## Technical Approach

Migración de 3 detectores legacy + 1 agregación infra al RuleEngine existente. Patrón 2-pass (recolectar → validar) modelado con GroupEvaluator y nuevos evaluadores atómicos. La agregación `compute_horas` es el habilitador crítico — sin ella las reglas de estancia no pueden expresarse como group rules.

**Corrección vs proposal**: `IDE_SIMPLE_RULES` tiene **~800 mappings** (no ~80), lo que hace inviable `CatalogInEvaluator`. Se requiere un evaluador dedicado.

## Architecture Decisions

### F1: compute_horas como aggregation function

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Agregación en GroupEvaluator (`_build_group_data`) | + homogéneo con collect_set/distinct_count; + usable en condiciones group | ✅ Elegido |
| Provider date.horas existente | Es row-level, no group-level; el valor row-level no es el correcto para estancia invariante | ❌ Rechazado |
| Evaluador custom tipo `hours_check` | Duplica lógica, no reutilizable | ❌ Rechazado |

**Firma**: `compute_horas(field1_name, field2_name)` → float horas (|f2-f1| en horas, primera fila del grupo).
**Agregación invariante de invoice**: estancia es misma para todas las filas de una factura, se toma el primer par no-None.
**Uso en condiciones**: `gt(group.compute_horas_field1_field2, 24)`.

### F2: hospitalizacion_codes como group rules

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| 2 group rules con collect_set + set_contains_all/set_intersects | + homogéneo; + sin nuevo código evaluador | ✅ Elegido |
| Evaluador custom tipo `hosp_codes_check` | Duplica lógica existente de set_contains_all/set_intersects | ❌ Rechazado |

**Regla A** (>24h): obligatorios = {129B02, 890601H, 890601}. **Regla B** (≤24h): obligatorios = {890601H, 129B02}. Prohibidos (ambas): {05DSB01, 5DSB01, 890701}. SOAT añade su propio set.

### F3: ide_contrato_intramural como 3 reglas

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| IDE_SIMPLE_RULES → `ide_simple_check` evaluador (pre-load desde `catalogos`) | + DB-driven; + ~800 rules sin tocar código | ✅ Elegido |
| CatalogInEvaluator existente | No soporta lookup 2-key (codigo+entidad → expected) | ❌ Rechazado |
| Mantener en Python como constantes | +0 cambio; pierde beneficio de centralización | ❌ Rechazado |

**Aclaración**: `IDE_SIMPLE_RULES` contiene ~800 entradas no ~80. El evaluador `IdeContratoSimpleEvaluator` pre-load un `dict[(codigo_norm, entidad_norm), expected]` desde `catalogos[key="ide_simple_rules"]`.

**PYM_RUTAS + Dx + pre-scan laboratorio**: Combinados en evaluador `PymRutasDxEvaluator` que acepta `data_sheet` via EvaluationContext pre-poblado por el engine. Pre-scan de solo_laboratorio se cachea a nivel de instancia.

### F4: sala_observacion como group rules

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| 3 group rules + mantener SalaObservacionEvaluator existente | + separación clara; + reutiliza evaluador existente | ✅ Elegido |
| 1 mega-evaluador para las 8 reglas | Monolítico, difícil de mantener | ❌ Rechazado |

**Reglas**: (A) obligatorios 890701/890601, (B) ESS prohibido 129B02, (C) SOAT obligatorios + prohibido 39133. `SalaObservacionEvaluator` existente se mantiene para regla #1 (estancia correcta).

## Data Flow

```
Sheet rows
  │
  ├─ Row-by-row (F3 Rules 1-2): IdeContratoSimpleEvaluator, PymRutasDxEvaluator
  │   Evaluator.pre_load() → cache DB → evaluate(row) → MATCH/NO_MATCH
  │
  └─ Group-by (F1, F2, F4):
      build_groups(numero_factura, filter=tipo_factura)
        → _build_group_data(agg_configs)
            ├─ compute_horas(fec_factura, fecha_cierre) → estancia_horas
            ├─ collect_set(codigo) → collect_set_codigo
            └─ collect_set(tarifario) → collect_set_tarifario
        → evaluate(condition_tree)
            ├─ set_contains_all/Intersects (códigos)
            ├─ gt/lt estancia_horas
            └─ NOT(...) para complementos
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/group_evaluator.py` | Modify | + `_agg_compute_horas()`, registry entry en `_build_group_data()` |
| `app/services/engine/evaluators.py` | Modify | + `IdeContratoSimpleEvaluator`, + `PymRutasDxEvaluator` |
| `app/services/engine/providers.py` | Modify | Opcional: pasar `data_sheet` en EvaluationContext |
| `app/services/engine/context.py` | Modify | Opcional: + `data_sheet` field |
| `app/services/hospitalizacion/hospitalizacion_codes.py` | Keep (dead) | Marcar como legacy, no remover aún |
| `app/services/intramural/ide_contrato_intramural.py` | Keep (dead) | Marcar como legacy |
| `app/services/urgencias/sala_observacion.py` | Keep (dead) | Marcar como legacy (SalaObservacionEval en evaluators.py queda) |
| `app/services/hospitalizacion/detect_all.py` | Modify | Remover llamada legacy, agregar engine |
| `app/services/intramural/detect_all.py` | Modify | Remover llamada legacy, agregar engine |
| `app/services/urgencias/detect_all.py` | Modify | Remover llamada legacy, agregar engine |
| `tests/` | Modify | Tests por fase (ver abajo) |

## Interfaces / Contracts

### compute_horas aggregation

```python
# En _build_group_data():
elif func == "compute_horas":
    agg_data[target] = GroupEvaluator._agg_compute_horas(
        rows, data_sheet, indices, config.get("field1"), config.get("field2")
    )
```

```python
# Uso en parametros de regla:
{
    "aggregations": [
        {"function": "compute_horas", "field1": "fec_factura",
         "field2": "fecha_cierre", "target": "estancia_horas"}
    ]
}
```

### IdeContratoSimpleEvaluator

```python
class IdeContratoSimpleEvaluator(AtomicEvaluator):
    operator = "ide_simple_check"
    # Pre-load from catalogos WHERE key='ide_simple_rules'
    # Expected: {"(COD,ENT)": "IDE", ...}
    # evaluate: build key from row_value + context → lookup expected → eq check
```

Valor en `catalogos` para key `ide_simple_rules`: JSONB con `[["906340","EPSS41","957"],["906127","EPSS41","958"],...]`.

## Reglas engine (nuevas)

| Nombre | Dominio | Tipo | Condición clave |
|--------|---------|------|-----------------|
| `hosp_codigos_oblig_mayor24h` | hospitalizacion | group | `gt(estancia_horas, 24)` AND `NOT(set_contains_all(codigos, OBLIG_MAYOR_24))` |
| `hosp_codigos_oblig_menor24h` | hospitalizacion | group | `lte(estancia_horas, 24)` AND `NOT(set_contains_all(codigos, OBLIG_MENOR_24))` |
| `hosp_codigos_prohibidos` | hospitalizacion | group | `set_intersects(codigos, PROHIBIDOS)` |
| `ide_contrato_simple` | intramural | row | `ide_simple_check(codigo, entidad) != expected` |
| `pym_rutas_dx` | intramural | row | `pym_rutas_dx_check(codigo, entidad, dx)` `== VIOLATION` |
| `sala_obs_obligatorios` | urgencias | group | `set_intersects(codigos, SALA_ACTIV)` AND `NOT(set_contains_all(codigos, OBLIG_SALA))` |
| `sala_obs_ess_129b02` | urgencias | group | `entidad in ESS` AND `contains(codigos, 129B02)` |
| `sala_obs_soat_completo` | urgencias | group | `tarifario=SOAT` AND `set_intersects(codigos, SOAT_SALA)` AND `NOT(set_contains_all(codigos, SOAT_OBLIG))` |
| `sala_obs_soat_prohibido` | urgencias | group | `tarifario=SOAT` AND `contains(codigos, 39133)` |

## Testing Strategy

| Fase | Qué testear | Approach |
|------|-------------|----------|
| F1 | `_agg_compute_horas` con fechas en múltiples formatos | Unit test directo sobre GroupEvaluator |
| F1 | compute_horas en condition tree con gt/lt | Integration test GroupEvaluator.evaluate |
| F2 | Snapshot parity: engine output = legacy output para datos reales | Snapshot test con Workbook mock |
| F3 | IdeContratoSimpleEvaluator pre-load + match/mismatch | Unit test con monkeypatch DB session |
| F3 | PymRutasDxEvaluator pre-scan + PYM check | Unit test con data_sheet mock |
| F4 | Cada group rule con MATCH/NO_MATCH esperado | Integration test GroupEvaluator + conditions |

## Migration / Rollout

Feature flag `USE_RULE_ENGINE` por detector. Default: legacy path. Cada fase mueve un flag. DB migration para `catalogos` key `ide_simple_rules` con seed data de ~800 rows.

## Open Questions

- [ ] **Pasar `data_sheet` a evaluadores**: ¿Modificar EvaluationContext o usar inyección por constructor en evaluadores que lo necesiten (PymRutas)?
- [ ] **Prioridad vs SalaObservacionEvaluator existente**: ¿Las group rules nuevas compiten con el evaluador row-level o lo complementan?
- [ ] **IDE_SIMPLE_RULES en urgencias**: ide_contrato_urgencias.py también usa IDE_SIMPLE_RULES. ¿Migrar ambas en este change o dejar urgencias para otro PR?
