# Proposal: Migrar SalaObservacionEvaluator a árbol de condiciones

## Intent

Reemplazar `SalaObservacionEvaluator` (operador `sala_obs_check`) con un árbol OR de 6 sub-árboles AND, siguiendo el mismo patrón que centro_costo (F14). El evaluador actual tiene un bug: estancia ≤ 2h retorna `False` en vez de detectar códigos incorrectos. El árbol corrige esto.

## Scope

### In Scope

1. Reemplazar `sala_observacion_valido` (actualmente `atomic(sala_obs_check, ...)`) con árbol OR de 6 AND sub-reglas en `condiciones`
2. Seed 2 catalogos: `sala_codes` → `["5DSB01","05DSB01","129B02","38114","38915"]`, `entidades_ess` → `["ESS118","ESSC18"]`
3. Corregir bug de estancia ≤ 2h (sub-árbol explícito que detecta cualquier código ≠ 5DSB01)
4. Tests de equivalencia contra output del evaluador actual (considerando el bug fijo)
5. Deprecar `SalaObservacionEvaluator` en `evaluators.py` (`DeprecationWarning`)
6. Deprecar `app/services/urgencias/sala_observacion.py`

### Out of Scope

- Las 6 group rules de sala-obs (ya migradas en condición tree via admin UI)
- Otros evaluadores (`ent_code_match`, `exists_in_db`, `cat_in`)
- Excepción `tipo_identificacion=CN/reingreso≠0` en `sala_obs_obligatorios` (legacy gap documentado)

## Capabilities

### New Capabilities

None — refactor interno, sin nuevas capacidades de sistema.

### Modified Capabilities

- `motor-reglas` (R18): Cambia "Row-level evaluator se mantiene para estancia" → "Row-level reemplazado por árbol de condiciones OR/AND".

## Approach

**Árbol OR único**, mismo patrón que centro_costo F14. Cada combinación estancia/entidad/tarifario es un sub-árbol AND:

```
OR
├── AND(SOAT, >6h, sala_codes, NOT(=38114))
├── AND(SOAT, 2-6h, sala_codes, NOT(=38915))
├── AND(NO-SOAT, >6h, ESS, sala_codes, NOT(=05DSB01))
├── AND(NO-SOAT, >6h, NO-ESS, sala_codes, NOT(=129B02))
├── AND(NO-SOAT, 2-6h, sala_codes, NOT(=5DSB01))
└── AND(≤2h, sala_codes, NOT(=5DSB01))       ← bug fix
```

Usa `date.horas` (provider existente) para estancia, `cat_in` para sets constantes. Seed SQL destructivo (DELETE + INSERT) sobre la rule existente.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `seed/migracion-engine/12_sala_observacion_valido.sql` | Modified | Reemplazar atomic(sala_obs_check) con árbol OR |
| `seed/migracion-engine/16_catalogos_sala_obs.sql` | **New** | Catalogos `sala_codes`, `entidades_ess` |
| `app/services/engine/evaluators.py` | Modified | Deprecar `SalaObservacionEvaluator`, remover de `_register_builtins()` |
| `app/services/urgencias/detect_all.py` | Modified | `sala_observacion_valido` ya usa RuleBasedDetector — sin cambios de wiring |
| `app/services/urgencias/sala_observacion.py` | Deprecated | Marcar como deprecado |
| `openspec/specs/motor-reglas/spec.md` | Modified | Actualizar R18 |
| `tests/engine/test_sala_observacion_rules.py` | **New** | Tests de equivalencia árbol vs evaluador |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **date.horas** retorna `int` (truncado), evaluador usa `float` — diferencias en bordes ~2-3h reales | Medium | Documentar límite; aceptar error de 1h en bordes. Si causa falsos positivos, corregir `_compute_horas` a float. |
| **Equivalence gap**: árbol produce MÁS detecciones que evaluador (bug fix) | High | Tests de snapshot contra datos reales; validar que las nuevas detecciones son correctas |
| **6 cat_in** por fila → performance | Low | Catálogo cacheado por instancia (1er row → DB, resto en memoria) |

## Rollback Plan

Revertir seed: re-ejecutar seed original `12_sala_observacion_valido.sql` (versión atomic). Eliminar catalogos `sala_codes` y `entidades_ess` si no los usa otra regla. Reactivar `SalaObservacionEvaluator` en registry.

## Dependencies

- `date.horas` provider debe estar cargado para row-level evaluation (confirmado: activo via `DateProvider` en `providers.py`)
- `cat_in` evaluator debe aceptar `sala_codes` y `entidades_ess` como catalog keys (confirmado: existe y funcional desde F13)

## Success Criteria

- [ ] Árbol OR produce mismo output que evaluador (excepto bug fix) para ≥50 facturas de test
- [ ] Bug ≤2h corregido: códigos ≠ 5DSB01 detectados en estancias ≤ 2h
- [ ] `SalaObservacionEvaluator` marcado como deprecado con `DeprecationWarning`
- [ ] Tests pasan: `python -m pytest tests/engine/test_sala_observacion_rules.py -v`
- [ ] Snapshot tests no muestran regresiones inesperadas
