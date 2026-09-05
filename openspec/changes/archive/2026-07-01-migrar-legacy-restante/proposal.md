# Proposal: Migrar detectores legacy restantes

## Intent

Completar la migración al Rule Engine de los 3 detectores legacy que quedaron fuera de "migracion-engine-completa": hospitalizacion_codes, ide_contrato_intramural y detect_sala_observacion. Los tres requieren un patrón 2-pass (recolectar por invoice → validar) y dependen de estancia_horas calculada de fec_factura − fecha_cierre — agregación que no existe en GroupEvaluator.

## Scope

### In Scope
- F1: Extender `GroupEvaluator._build_group_data()` con `compute_horas` aggregation (date_diff puro, ~30 ln)
- F2: `hospitalizacion_codes` → reglas group engine (códigos obligatorios/prohibidos por estancia y tarifario)
- F3: `ide_contrato_intramural` → 3 reglas engine: (a) ~80 mapping rows a DB tabla catalogos + CatalogInEvaluator, (b) PYM_RUTAS + Dx como group rule, (c) pre-scan "solo laboratorio" como group rule
- F4: `detect_sala_observacion` → reglas group engine (~8 reglas: estancia, ESS prohibidos, 890601H, 05DSB01, obligatorios, SOAT)

### Out of Scope
- UI, rutas HTTP, exportación, frontend
- Cambios a detectores ya migrados
- Refactor de ide_contrato_rules.py (se mueve a DB catalogos)

## Capabilities

### New Capabilities
None — los 3 detectores existen y se reemplazan con engine rules.

### Modified Capabilities
- `motor-reglas`: se extiende R12 (hours_diff) para operar como agregación group-level; R13 (GroupEvaluator) gana `compute_horas` aggregation function

## Approach

4 fases secuenciales, cada una con legacy-detector-equivalent test:

1. **F1**: Agregar `compute_horas` a `GroupEvaluator`. Toma `(fecha1_field, fecha2_field)` como parámetros, computa `|f2 - f1|` en horas sobre la primera fila del grupo (estancia es invariante por invoice). Incluir en `agg_configs` con `target="estancia_horas"`.

2. **F2**: Crear 2 reglas engine para hospitalización: (a) códigos obligatorios por estancia + tarifario, (b) códigos prohibidos. Usar `group_by=numero_factura` + `filter_field=tipo_factura_descripcion, filter_value=Hospitalización`. Condiciones con `set_contains_all`/`set_intersects` sobre `collect_set(codigo)`. Remover legacy `detect_hospitalizacion_codes()` del orquestador hospitalización.

3. **F3**: Mover ~80 mappings `IDE_SIMPLE_RULES` a `catalogos` DB table como `key=` `ide_simple_rules`. Crear regla `ide_contrato_simple` con `CatalogInEvaluator`. `PYM_RUTAS+Dx` y pre-scan "solo laboratorio" como group rules independientes. Remover legacy.

4. **F4**: Crear ~8 group rules para sala_observación reemplazando las 8 reglas legacy. Usar `compute_horas` para estancia + `collect_set` para códigos. SalaObservacionEvaluator row-level se mantiene para rule #1 (estancia correcta). Remover legacy `detect_sala_observacion()`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/group_evaluator.py` | Modified | + `compute_horas` aggregation function |
| `app/services/engine/evaluators.py` | Modified | + nuevo evaluador si CatalogInEvaluator no cubre |
| `app/services/hospitalizacion/hospitalizacion_codes.py` | Removed | Replaced by engine rules (keep file, mark dead) |
| `app/services/intramural/ide_contrato_intramural.py` | Removed | Replaced by engine rules |
| `app/services/urgencias/sala_observacion.py` | Removed | Replaced by engine rules |
| `app/services/hospitalizacion/detect_all.py` | Modified | Remove legacy call, add engine call |
| `app/services/intramural/detect_all.py` | Modified | Remove legacy call, add engine call |
| `app/services/urgencias/detect_all.py` | Modified | Remove legacy call, add engine call |
| `tests/` | Modified | New tests for each phase |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| compute_horas diff type mismatch (string date vs datetime) | Med | Test con todos los formatos del legacy antes de removerlo |
| ~80 mappings IDE → errores de migración | Med | Test en staging con datos reales; mantener legacy como fallback con feature flag |
| Pre-scan "solo laboratorio envío" difícil de modelar como group rule | Low | Usar `filter_field` + `collect_set(codigo)` + `set_intersects(CODIGOS_LABORATORIO_ENVIO)` |

## Rollback Plan

Por detector via feature flag `USE_RULE_ENGINE`. Si falla un detector, desactivar su flag individual — el legacy detector sigue en código (no borrado hasta próxima release). Para F1 (compute_horas): si falla la agregación, las group rules no pueden evaluar — rollback general del change via `USE_RULE_ENGINE=false`.

## Dependencies

- DB migration para `catalogos` key `ide_simple_rules` (~80 rows de seed data)
- Ninguna externa

## Success Criteria

- [ ] `compute_horas` produce output idéntico a `_format_estancia` legacy para >100 facturas de prueba
- [ ] Cada reemplazo engine detecta los mismos problemas que su legacy (snapshot test)
- [ ] `detect_all.py` orquestadores funcionan sin legacy calls

## Review Workload Forecast

- **Líneas legacy a migrar**: ~730 (172+241+318)
- **Líneas engine nuevas estimadas**: ~250-350 (30 F1 + 60 F2 + 120 F3 + 80 F4)
- **Líneas eliminadas**: ~730
- **Budget risk**: **HIGH** (>400 diff sumando add+delete)
- **Chained PRs**: **Recomendado** — 1 PR por fase (F1 preparation → F2 → F3 → F4)
