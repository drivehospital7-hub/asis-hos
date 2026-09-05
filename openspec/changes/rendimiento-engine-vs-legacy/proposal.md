# Proposal: DB Engine Intra-Row Optimizations

## Intent

El engine DB-backed es 10–50× más lento que los detectores legacy Python. Tres cuellos de botella internos causan 1M+ consultas redundantes y 1M asignaciones ORM por corrida (50K filas × 20 reglas). Eliminar el N+1 de excepciones, resolver date.edad solo cuando se usa, y saltar evidencia para NO_MATCH. Cero cambio de comportamiento.

## Scope

### In Scope
- **Excepción caching per-rule**: Mover `apply_exceptions()` fuera del loop de filas en `evaluate_sheet()`. La query de excepciones es rule-level — misma para todas las filas. Guardar resultado y reusar.
- **Lazy date.edad pre-resolution**: Escanear el condition tree después de `build_tree()`. Solo llamar `_resolve_computed("date.edad")` y `_resolve_computed("date.edad_meses")` si el árbol contiene referencias a esos campos (~20% de reglas).
- **Skip NO_MATCH evidence**: Solo llamar `collector.record()` y construir `arbol_evaluado` (trace dict) cuando outcome es MATCH o ERROR. NO_MATCH no necesita evidencia inmutable.

### Out of Scope
- Facts-first RowStore o SessionManager (ya en `auditoria-rendimiento-brms`)
- Índices compuestos (ya en `auditoria-rendimiento-brms`)
- Cambio en output de detección

## Capabilities

### New Capabilities

None — pure performance optimization, zero new business capability.

### Modified Capabilities

None — `motor-reglas/spec.md` and `evidencia-auditoria/spec.md` requirements unchanged. Evidence for MATCH/ERROR rows remains identical.

## Approach

Three targeted changes inside `engine.py` `evaluate_sheet()`, none changing the public interface:

1. **Exception caching (lines 136–138)**: `apply_exceptions()` today queries `excepciones WHERE regla_id = X` per row. Move BEFORE the `for row in range(2, max_row+1)` loop. Return `(effect, overrides)` once, reuse across all rows. If `effect == "skip"` with no row-specific scope, skip entire rule evaluation — O(N) → O(1).

2. **Lazy date.edad (lines 154–160)**: After `build_tree()`, walk the tree recursively. Flag `needs_edad` / `needs_edad_meses` if any atomic leaf references `date.edad` or `date.edad_meses` in `fuente_datos`. Only call `_resolve_computed()` inside the row loop when the flag is set.

3. **NO_MATCH skip (lines 174–186)**: Guard the `collector.record()` call with `if final_outcome != "NO_MATCH"`. The `eval_result.get("trace")` dict is built during evaluation regardless — no extra cost. Skip only the ORM allocation + DB insert path.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/engine.py` | Modified | Exception caching, lazy date.edad, NO_MATCH guard |
| `app/services/engine/exception_handler.py` | Modified | Separate `query_exceptions(rule, session)` from `apply_exceptions()` for cached reuse |
| `app/services/engine/condition_evaluator.py` | Modified | Add `tree_uses_field(tree, field_name)` helper for lazy date scanning |
| `tests/engine/test_engine_perf_optimizations.py` | New | TDD: exception caching, lazy edad, NO_MATCH skip |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scope-based exceptions break caching — algunas excepciones son por factura, no por regla | Low | `_matches_scope()` ya usa `invoice_data`; si el scope no es trivial, invalidar cache y caer a per-row |
| `tree_uses_field()` false negative omite date.edad | Low | Recursive walk de todos los nodos; test con árboles que referencian `date.edad` en niveles profundos |
| NO_MATCH skip rompe auditoría | Low | `evidencia-auditoria/spec.md` R1 dice "for every rule evaluated" — pero el contrato actual ya persiste NO_MATCH. Verificar que ningún consumer depende de evidencia NO_MATCH en DB |

## Rollback Plan

- **Code**: Cada optimización detrás de feature flags: `CACHE_EXCEPTIONS=true`, `LAZY_DATE_EDAD=true`, `SKIP_NO_MATCH_EVIDENCE=true`. Desactivar individualmente.
- **Verificación**: Snapshot tests (`test_snapshot_legacy_vs_engine.py`) deben pasar idénticos con flags on/off.
- **DB**: No schema changes. Si `SKIP_NO_MATCH_EVIDENCE=true`, simplemente hay menos filas en `evidencias` — sin impacto en queries existentes (que filtran `outcome='MATCH'`).

## Dependencies

- `auditoria-rendimiento-brms` — independiente. Este cambio aplica dentro del loop, el otro cambia la estructura. Sin conflictos de merge.

## Success Criteria

- [ ] `test_engine_perf_optimizations.py` — TDD verde para los 3 casos
- [ ] Snapshot tests idénticos antes/después
- [ ] Exception query count drops from O(N) to O(1) por regla (verificable con SQLAlchemy event listener en tests)
- [ ] `_resolve_computed("date.edad")` solo se llama cuando el condition tree lo referencia (contador en tests)
- [ ] NO_MATCH rows no generan `Evidencia` ORM objects (assert collector.record no llamado)
