## Exploration: Auditoría de Rendimiento BRMS

### Current State

The system has a **DB-backed rule engine** (`app/services/engine/`) that replaces legacy hardcoded Python detectors. Rules are stored as data in PostgreSQL tables (`reglas`, `condiciones`, `excepciones`) and evaluated against Excel invoice rows loaded via openpyxl.

**Full flow**:

1. **Entry**: A single `detect_problems_only()` call in `app/services/exporter.py` reads an Excel file with Polars (calamine engine), converts to a lightweight `_SimpleSheet` (2D list), and delegates to domain-specific `detect_all.py` orchestrators.

2. **Orchestration**: Each `detect_all.py` (odontología, urgencias, equipos_básicos) calls `RuleBasedDetector` for every rule — **opening a separate DB session per rule** via `get_session()`. This is the worst anti-pattern: ~20–30 rules × 1 session each, all sequential.

3. **Rule loading**: `RuleResolver.resolve(domain, session)` queries: `SELECT * FROM reglas WHERE (dominio = :domain OR dominio = 'transversal') AND estado = 'active' AND activo = true ORDER BY prioridad ASC` — no composite index on `(dominio, estado, activo, prioridad)`.

4. **Row-by-row evaluation**: For each rule, `RuleEvaluationEngine.evaluate_sheet()` iterates rows 2..max_row (~5K–50K rows). Per row:
   - Extracts all cell values via `data_sheet.cell(row, col).value` (N cells × N rows)
   - Calls `ExceptionHandler.apply_exceptions()` → queries `excepciones WHERE regla_id = :id AND activo = true` (1 DB query per row if exceptions exist)
   - Builds `EvaluationContext` with row data + merged params
   - Pre-resolves computed fields (`date.edad`, `date.edad_meses`)
   - Evaluates the condition tree recursively (AND/OR/NOT with short-circuit)
   - If `persist=True`, records `Evidencia` + `ResultadoAuditoria` in batch per rule

5. **Group-by rules**: Some rules use `GroupEvaluator` which pre-scans rows, partitions by key (e.g., `numero_factura`), computes aggregations (`distinct_count`, `sum`, `collect_set`), then evaluates the condition tree once per group.

6. **Evidence/audit persistence**: After each rule, `flush_batch()` does `session.add_all()` + `session.flush()`. Then `ResultadoAuditoria` rows are created and flushed. This means ~2 batches per rule × number of rules.

**Current algorithm**: **Naive sequential evaluation** with:
- O(R × N) complexity (R = rules, N = rows)
- R separate DB sessions
- O(N × R) openpyxl cell accesses
- O(N × R) exception queries when exceptions exist
- No inter-rule caching of facts (each rule re-resolves `invoice.*` provider values)
- Evidence flushing per-rule creates N_write amplification

### ⚠️ Contexto real: 50K acumulados procesados todos los días

Cada día se procesa **EL MISMO Excel acumulado del mes**, no solo los nuevos. Comienza con ~1.000 filas el día 1 y crece hasta **~50.000 filas al cierre del mes**. Son 1M de evaluaciones (20 reglas × 50K filas) por corrida al final del mes.

| Día | Filas acumuladas | Evaluaciones (R=20) | Sesiones DB |
|-----|-----------------|---------------------|-------------|
| 1   | 1.000           | 20K                 | 20          |
| 10  | ~16.000         | ~320K               | 20          |
| 20  | ~33.000         | ~660K               | 20          |
| **30** | **~50.000**   | **1.000.000**       | **20**      |

**Tres problemas que se multiplican con N:**

1. 🔴 **20-30 sesiones DB independientes** — conexión/desconexión PostgreSQL POR REGLA, a 50K filas duele el doble
2. 🔴 **O(N × R) cell() openpyxl** — 1M accesos a celdas al final del mes (50K filas × 20 reglas), todo secuencial
3. 🔴 **O(N × R) en queries de excepciones** — si una regla tiene excepciones activas, son 50K queries extra por regla

| Metric | Valor |
|--------|-------|
| Active rules per domain | ~15–30 |
| Condition nodes per rule | 1–10, hasta ~50 |
| Rows per Excel (fin mes) | **50K** |
| Complexity pico | **O(20 × 50K) = 1M evaluaciones** |
| openpyxl cell() accesses | **1M por corrida** |
| DB sessions per run | **20–30 (anti-patrón crítico)** |
| Evidence rows per run | ~20 × 50K = 1M filas |

### Affected Areas

- `app/services/engine/engine.py` — Core evaluation loop, sequential row-by-row
- `app/services/engine/rule_resolver.py` — Rule loading (no index hint, loads all conditions per rule)
- `app/services/engine/condition_evaluator.py` — Recursive tree evaluation per row
- `app/services/engine/evaluators.py` — Each `AtomicEvaluator.evaluate()` call per condition per row
- `app/services/engine/group_evaluator.py` — Aggregation functions scan rows O(N) per group rule
- `app/services/engine/evidence_collector.py` — Per-rule evidence flushing (N writes × R rules)
- `app/services/engine/exception_handler.py` — Per-row exception query
- `app/services/odontologia/detect_all.py` — Session-per-rule pattern
- `app/services/urgencias/detect_all.py` — Session-per-rule pattern
- `app/services/equipos_basicos/detect_all.py` — Session-per-rule pattern
- `app/services/exporter.py` — Entry point, converts Polars → openpyxl-compatible sheet
- `app/models.py` — Schema: `reglas`, `condiciones`, `excepciones`, `evidencias`, `resultados_auditoria`

### Approaches

1. **Low-hanging: Fix orchestration + add indexes** — Keep the current algorithm but fix the biggest inefficiencies:
   - Create composite index on `reglas(dominio, estado, activo, prioridad)` for RuleResolver
   - Create composite index on `condiciones(regla_id)` for condition loading
   - Create composite index on `excepciones(regla_id, activo)` for exception queries
   - Fix `detect_all.py` to use a **single DB session** across all rule evaluations
   - Disable evidence persistence when not needed (`persist=False`)
   - Add in-memory row cache (read all rows once, reuse across rules)
   - use_single_session + row_cache reduces O(R × N) openpyxl calls to O(N)
   - **Pros**: Minimal code changes, immediate gains, safe
   - **Cons**: Still O(R × N) evaluation, doesn't address algorithm inefficiency
   - **Effort**: Low (1–2 days)

2. **Facts-first: Pre-load all facts + batch evaluation** — Instead of per-row evaluation, pre-load all rows as structured facts once, then evaluate ALL rules against ALL facts in a batch:
   - Phase 1: Read Excel once → structured fact list (Polars is already doing this)
   - Phase 2: For each rule, evaluate against all facts using pre-loaded data
   - Phase 3: Batch persistence of evidence
   - Add a per-rule **match index**: pre-filter rows by simple conditions before full tree evaluation
   - **Pros**: Eliminates N×R openpyxl overhead, enables fact pre-filtering, clean separation
   - **Cons**: Still sequential rule evaluation, medium refactor
   - **Effort**: Medium (3–5 days)

3. **Rete-inspired incremental matching** — Implement a simplified Rete-like network in Python that matches incrementally:
   - Build a **discrimination network** (alpha network) for each atomic condition across ALL rules
   - Each alpha node filters facts by a single condition (e.g., `convenio_facturado == "PyP"`)
   - Beta nodes join matches across conditions (AND/OR)
   - Terminal nodes collect full rule matches
   - Facts flow through the network once; all rules are evaluated simultaneously
   - **Delta propagation**: if incremental rows are added, only new facts flow through
   - **Pros**: O(N + R) instead of O(N × R), truly incremental, handles all rules in one pass
   - **Cons**: Significant complexity, Python implementation needs careful optimization, not a full Rete (no conflict resolution needed for this use case), condition trees are dynamic (DB-backed) so the network needs to be rebuilt when rules change
   - **Effort**: High (2–3 weeks)

### Recommendation (CORREGIDA: 50K acumulados)

Con 50K filas al final del mes y 1M de evaluaciones por corrida, los approaches cambian de prioridad. El Rete sigue siendo discutible (N=50K está en el límite), pero **facts-first ya no es opcional**.

**Prioridades finales**:

1. 🔴 **Sesión única** (2h) — 20 conexiones DB al pedo. Impacta siempre, independientemente de N.
2. 🔴 **Índices compuestos** (1h + migration) — queries de resolución de reglas sin seq scan.
3. 🔴 **Facts-first + row cache** (3-5 días) — EL CAMBIO MÁS IMPORTANTE. Elimina el O(N×R) de openpyxl cell() pasando a O(N) + O(R × condiciones). Lee el Excel UNA vez, construye lista de dicts, comparte entre todas las reglas.
4. 🟡 **Batch de evidencia diferido** (2 días) — de 20-40 flushes a 1 solo al final.
5. 🟡 **Pre-filter ligero por regla** (add-on de facts-first) — condiciones `eq`/`in` comunes chequeadas con lookup O(1) antes del árbol completo.
6. ⚪ **Rete** — Sigue siendo overkill para Python puro con 50K filas, a menos que el engine se use para carga incremental en tiempo real. Con procesamiento batch diario, facts-first alcanza y sobra.

**Rete descartado explícitamente**: Facts-first + row cache + pre-filter cubren el mismo caso de uso con 1/10 de la complejidad. Rete solo tendría sentido si hubiera decenas de miles de facts entrando en streaming, no en batch diario.

### Risks

- **Risk 1**: Cambiar el patrón de `detect_all.py` a sesión única puede afectar la atomicidad transaccional. Hoy, si la regla #10 falla, las reglas #1–9 ya persistieron sus resultados. Con sesión única, un error en la mitad del batch podría revertir TODO. Solución: usar savepoints por regla, o hacer flush por regla dentro de la misma sesión (commit al final).
- **Risk 2**: Los índices nuevos pueden afectar el rendimiento de inserts en `reglas`/`condiciones`/`excepciones` si se editan reglas frecuentemente. Monitorear.
- **Risk 3**: No hay benchmarks actuales. No podemos medir mejora sin una línea de base. Sugiero agregar timing básico antes/después.
- **Risk 4**: El `GroupEvaluator` (agregaciones cross-row como `distinct_count`, `sum`) necesita atención especial si se cambia el modelo de evaluación.

### Ready for Proposal

Yes — the analysis is comprehensive. The orchestrator should proceed with `sdd-propose` focusing on Approach 2 (facts-first batch evaluation) with the understanding that the session fix and index additions are quick wins that can be done alongside or even before the proposal.

Key constraints for the design phase:
- Must preserve exact detection behavior (legacy parity is critical)
- The `GroupEvaluator` path must remain functional
- Evidence/audit immutability must be preserved
- Rollback must be possible: keep the old `evaluate_sheet` path as a fallback
