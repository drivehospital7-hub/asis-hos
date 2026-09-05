# Design: Migrate `cups_sin_contrato` to DB Rule Engine

## Technical Approach

Single `CupsContratadoEvaluator(AtomicEvaluator)` with operator `"cups_contratado"` that pre-loads the 5-table JOIN (`eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`) on first `evaluate()` and replicates the 6 exception branches internally. The seed SQL condition tree is simplified to `NOT(cups_contratado(invoice.codigo, ...))` — the evaluator returns `True` when contracted, the outer `NOT` inverts to MATCH.

## Architecture Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| **Compound evaluator** (single class, internal exceptions) | Pro: matches legacy fall-through logic; simple condition tree; follows `CentroCostoCheckEvaluator` pattern (~80 LoC). Con: ~180-200 LoC total, but isolated and testable. | **Chosen** — exception chain has priority ordering that would require deeply nested AND/OR/NOT trees if decomposed. |
| **Decomposed evaluators** (one per exception) | Pro: smaller classes, SRP, composable. Con: complex condition tree; hard to replicate the fall-through-to-normal-check behavior. | **Rejected** — would increase seed SQL complexity without runtime benefit. |
| **First-call pre-load** (cache 4 datasets on first `evaluate()`) | Pro: single DB round-trip for all rows avoids N+1. Con: memory overhead (~hundreds of tuples). | **Chosen** — batch processing (hundreds of rows) makes this optimal; same strategy as legacy. |
| **Per-row query** | Pro: no pre-load code. Con: N+1 queries per sheet. | **Rejected** — poor performance for batch processing. |
| **Internal exception handling** | Pro: 6 branches with fall-through logic stay coherent; simple seed SQL. Con: evaluator is "fat" but well-scoped. | **Chosen** — CAP, urgencias, FEV branches must fall through to normal check; external tree would be fragile. |
| **External condition tree** | Pro: fully visible logic. Con: deeply nested conditions (each exception is a subtree). | **Rejected** — fall-through to `pares_validos` check is hard to model as AND/OR/NOT. |

### Evaluator returns True when contracted

The evaluator returns `True` if the CUPS IS properly contracted (matching `pares_validos` or passing an exception). The seed SQL wraps it in `NOT(...)` so detection fires only when NOT contracted. This avoids negative semantics in the evaluator itself.

## Data Flow

```
┌─────────────────────────────────────────────────────┐
│  First evaluate() call:                              │
│  1. Query DB JOIN → pares_validos: set[(entidad,cups)]│
│  2. Query eps_contratado → eps_map: dict[str,str]    │
│  3. Query nota_hoja id=1,27 → nota_urgencias_cups    │
│  4. Query nota_hoja id=2,3 → nota_cap_cups           │
│     Cached in self.* for subsequent calls.            │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
     Per-row evaluate(codigo, context.invoice_data)
                         │
                         ▼
           ┌── 1. Farmacia skip (tarifario check)?
           │    YES → return True (skip)
           │
           ├── 2. Urgencias + CUPS in nota_hoja 1/27?
           │    YES → return True
           │
           ├── 3. CAP + ESS118 in nota_cap[3]?
           │    YES → return True
           │    NO  → return False (error directo)
           │
           ├── 4. CAP + EPSS41 in nota_cap[2]?
           │    YES → return True
           │    NO  → return False (error directo)
           │
           ├── 5. Entidad not in DB? → return True (skip)
           │
           ├── 6. (entidad, codigo) in pares_validos?
           │    YES → return True
           │
           ├── 7. codigo_equiv in pares_validos?
           │    YES → return True
           │
           ├── 8. FEV + (EPS037|EPSS41)? → return True
           │
           └── All checks failed → return False
                                    │
                                    ▼
                  NOT(invert) → MATCH → problem detected
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/evaluators.py` | Modify | Add `CupsContratadoEvaluator` class (~170 LoC) + register in `_register_builtins()` |
| `seed/phase7/insert_procedimiento_contratado.sql` | Modify | Replace `NOT(exists_in_db(...))` tree with `NOT(cups_contratado(invoice.codigo, ...))` |
| `app/services/transversales/procedimiento_contratado.py` | Modify | Stub `detect_cups_sin_contrato` to delegate to `RuleBasedDetector` when engine is active; full delete deferred |
| `tests/engine/test_snapshot_phase7_cross_ref.py` | Modify | Add test scenarios covering all 6 exception branches + snapshot comparison |
| `tests/services/test_detect_cups_sin_contrato.py` | Delete | Legacy tests replaced by engine snapshot tests |

## Interfaces / Contracts

```python
class CupsContratadoEvaluator(AtomicEvaluator):
    """Check if a CUPS is properly contracted for the entity.

    operator = "cups_contratado"

    Pre-loads 4 DB datasets on first evaluate(), then checks each row
    against the contracted pairs, applying the same 6 exception branches
    as the legacy detector.

    Returns True when properly contracted (NOT inverts to MATCH).
    """

    operator = "cups_contratado"

    def __init__(self) -> None:
        self._loaded: bool = False
        self._pares_validos: set[tuple[str, str]] = set()
        self._eps_map: dict[str, str] = {}
        self._nota_urgencias_cups: set[str] = set()
        self._nota_cap_cups: dict[int, set[str]] = {}
        self._entidades_con_datos: set[str] = set()

    def evaluate(
        self,
        condition: dict,
        row_value: Any,          # invoice.codigo (CUPS code)
        expected: Any,           # unused (static None)
        context: EvaluationContext | None = None,
    ) -> bool:
        ...
```

**Context keys read from `context.invoice_data`**:

| Key | Source | Used In |
|-----|--------|---------|
| `codigo` | row_value (from `invoice.codigo`) | All branches |
| `codigo_entidad_cobrar` | `invoice.codigo_entidad_cobrar` | CAP, pares_validos, FEV |
| `tarifario` | `invoice.tarifario` | Farmacia skip |
| `responsable_cierra` | `invoice.responsable_cierra` | Urgencias exception |
| `codigo_equiv` | `invoice.codigo_equiv` | Fallback check |
| `numero_factura` | Derived from factura | CAP/FEV prefix detection |

**Seed SQL condition tree** (replaces current 3 INSERTs):

```sql
-- Root: NOT composite node
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (<id>, NULL, 'composite', 'NOT', NULL, NULL, 0);

-- Child of NOT: atomic cups_contratado evaluator
INSERT INTO condiciones (regla_id, padre_id, tipo, operador, fuente_datos, valor_esperado, orden)
VALUES (<id>, <root_id>, 'atomic', 'cups_contratado', 'invoice.codigo', NULL, 0);
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `CupsContratadoEvaluator.evaluate()` | Direct instantiation with mocked `EvaluationContext`; test each exception branch in isolation |
| Integration | Full condition tree via `RuleBasedDetector` | Build worksheet with rows covering all 6 exception branches; snapshot-compare output against legacy detector results |
| Data | DB integrity | Verify seed SQL is idempotent (no duplicate rows on re-run) |

**Test scenarios to port** (30+ from legacy tests):

| Scenario | Entity | CUPS | Exception | Expected |
|----------|--------|------|-----------|----------|
| Farmacia skip | Any | Any | tarifario=farmacia | No detection |
| Urgencias nota_hoja 1/27 | ESS118 | Code in nota_hoja 1/27 | responsable=facturador | No detection |
| CAP+ESS118 capitado | ESS118 | Code in nota_cap[3] | CAP prefix | No detection |
| CAP+ESS118 no capitado | ESS118 | Code NOT in nota_cap[3] | CAP prefix | Error |
| CAP+EPSS41 capitado | EPSS41 | Code in nota_cap[2] | CAP prefix | No detection |
| Normal contracted | EPS012 | Code in pares_validos | — | No detection |
| Normal not contracted | EPS012 | Code NOT in pares_validos | — | Error |
| codigo_equiv fallback | EPS012 | Main missing, equiv present | Equiv check | No detection |
| FEV autorizado | EPS037 | Any | FEV prefix | No detection |

## Migration / Rollout

No migration required. The seed SQL is idempotent — re-running updates the condition tree. Feature flag `USE_RULE_ENGINE=false` keeps legacy path active.

## Open Questions

None.
