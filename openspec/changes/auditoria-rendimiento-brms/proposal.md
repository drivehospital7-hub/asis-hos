# Proposal: Auditoría de Rendimiento BRMS

## Intent

Engine opens one DB session per rule (~20-30/domain), reads cells N×R times (50K×20=1M accesos a fin de mes), flushes evidence per-rule. Para 50K filas acumuladas, el costo de O(R×N) con sesiones separadas es INSOSTENIBLE. Refactorizar a facts-first + sesión única + batch evidence. Cero cambio de comportamiento.

## Scope

### In Scope
- **Facts-first evaluation**: precargar todas las filas como `list[dict]` UNA VEZ, compartir entre todas las reglas. Engine acepta datos precargados en vez de Worksheet.
- **Single DB session**: `SessionManager` context manager para los 3 dominios.
- **Composite indexes**: `reglas(dominio, estado, activo, prioridad)`, `condiciones(regla_id)`, `excepciones(regla_id, activo)`.
- **Deferred batch evidence**: acumular evidence de todas las reglas, flush único al final.
- **Pre-filter ligero**: condiciones `eq`/`in` comunes resueltas con lookup O(1) antes del árbol de condiciones completo.
- **Performance benchmark**: timer básico antes/después para validar mejora.

### Out of Scope
- Rete algorithm (overkill para batch diario con 50K filas)
- GroupEvaluator rewrite (recibe datos precargados igual)
- Cambio en output de detección

## Capabilities

### New Capabilities

None — pure performance refactor, zero new business capability.

### Modified Capabilities

None — `motor-reglas/spec.md` behavior is identical before and after.

## Approach

1. **Facts-first**: El exporter ya lee el Excel con Polars. Extender `_SimpleSheet` → `RowStore` (list[dict]) en `exporter.py`. `RuleEvaluationEngine.evaluate_sheet()` recibe `rows: list[dict]` en vez de Worksheet. Cada regla itera las filas sin tocar openpyxl. Pre-filter: condiciones `eq`/`in` se evalúan con dict lookup en vez de tree traversal completo.

2. **Session**: `SessionManager` context manager. `detect_all.py` wrap domain block en `with session_manager(domain) as session:`. Savepoints por regla preservan rollback individual.

3. **Indexes**: `migrations/005_add_performance_indexes.sql` — 3 `CREATE INDEX CONCURRENTLY`.

4. **Batch evidence**: `EvidenceCollector` asciende a scope del dominio. `session.bulk_insert_mappings()` único para todas las reglas. Commit 1 vez al final.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/engine/` | Modified | Add `row_store.py`, `session_manager.py`; refactor `engine.py` para aceptar `list[dict]`; `evidence_collector.py` a batch diferido |
| `app/services/*/detect_all.py` | Modified | 3 domains: `SessionManager` wrap + pasar RowStore en vez de Worksheet |
| `app/services/exporter.py` | Modified | Construir `RowStore` después de Polars read, pasar downstream |
| `migrations/005_add_performance_indexes.sql` | New | 3 composite indexes |
| `app/models.py` | Minor | `__table_args__` con los nuevos índices |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Mid-batch rule failure rolls back prior rules | Low | Savepoints per rule within shared session |
| Index write overhead on rule edits | Low | <10K rows, negligible impact |
| GroupEvaluator recibe RowStore | Low | Ya itera rows, adaptar a `list[dict]` es análogo a iterar Worksheet |
| Row store memory | Low | 50K filas × ~20 columnas × 50 bytes ≈ 50MB, aceptable |
| Refactor condition_evaluator para dict | Medium | Pasa de cell() a dict lookup, probar exhaustivamente |

## Rollback Plan

- **Code**: `USE_RULE_ENGINE=false` reverts to legacy pure-Python detectors, bypassing engine entirely
- **Indexes**: `DROP INDEX IF EXISTS` in `migrations/005_rollback_performance_indexes.sql`
- **Evidence**: `PER_RULE_COMMIT=true` config restores per-rule commit behavior
- **Verification**: Snapshot tests must pass identically; any delta blocks deployment

## Dependencies

- PostgreSQL 14+ (index `CONCURRENTLY` support)
- Existing `migrations/` runner (raw SQL)

## Success Criteria

- [ ] Integration tests pass with identical detection output
- [ ] Evidence row counts identical before/after
- [ ] All snapshot tests pass unchanged
- [ ] Composite indexes present via `\d reglas` / `\d condiciones` / `\d excepciones`
- [ ] DB connections per domain drops from ~20-30 to exactly 1
- [ ] Performance benchmark: tiempo de procesamiento 50K filas medido antes/después
