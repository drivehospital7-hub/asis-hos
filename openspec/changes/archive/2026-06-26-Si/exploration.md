## Exploration: Migrate cups_sin_contrato to Rule Engine

### Current State

**Legacy detector** (`app/services/transversales/procedimiento_contratado.py`, 267 lines):

Pre-loads 4 datasets from DB, then row-by-row scans the Excel:
1. **pares_validos**: `set[tuple[str, str]]` — all (cod_contrato, cups) pairs via JOIN: `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`
2. **eps_map**: `dict[cod_contrato → eps_name]` — for error messages
3. **nota_urgencias_cups**: `set[str]` — CUPS in nota_hoja id=1/27 (used by urgencias facturadores)
4. **nota_cap_cups**: `dict[int, set[str]]` — CUPS in nota_hoja id=2 (EPSS41) and id=3 (ESS118) for CAP invoice exception

Per row, applies exceptions in order:
1. Skip if tarifario == "Suminstros, Medicamentos" (farmacia)
2. Skip if responsable_cierra is urgencias facturador AND CUPS in nota_hoja 1/27
3. CAP + ESS118 → validate against nota_hoja 3 only
4. CAP + EPSS41 → validate against nota_hoja 2 only
5. Skip if entity has no procedures in DB (entidades_con_datos check)
6. Check main CUPS in pares_validos
7. Fallback to codigo_equiv in pares_validos
8. Skip FEV + EPS037/EPSS41 (authorization)
9. Otherwise → error

**Engine rule** (`cups_sin_contrato` — from `seed/phase7/insert_procedimiento_contratado.sql`):

```
NOT(exists_in_db(invoice.codigo, {"table": "procedimiento", "field": "cups"}))
```

This is a radical simplification — it only checks if the CUPS exists in the `procedimiento` catalog table, NOT whether it's contracted for the specific entity. The seed SQL comment itself acknowledges this is a Phase 7 simplification awaiting a future enhancement.

**Current integration**: All 7 domain `detect_all.py` files call BOTH the legacy detector and the engine rule via `is_rule_engine_enabled()` feature flag. The engine version runs after the legacy one, overwriting results.

### Affected Areas

- `app/services/transversales/procedimiento_contratado.py` — legacy detector to be replaced (all 267 lines)
- `app/services/engine/evaluators.py` — needs a new evaluator implementing the contracted-pair check (existing `ExistsInDBEvaluator` only handles single-table catalog lookups)
- `app/services/engine/providers.py` — may need a new provider or enhancement to `ContractProvider` for entity-level pre-load
- `app/constants/urgencias.py` — `FACTURADORES_URGENCIAS` (line 634) and `VALOR_TARIFARIO_FARMACIA` (line 113) used by legacy detector, source of truth for exceptions
- `app/models.py` — `EpsContratado`, `EpsNota`, `NotaHoja`, `NotasTecnicas`, `Procedimiento` — the 5 tables in the JOIN chain
- `seed/phase7/insert_procedimiento_contratado.sql` — must update the engine rule definition
- `tests/services/test_detect_cups_sin_contrato.py` — ~1000 lines, covers all legacy detector scenarios
- `tests/engine/test_snapshot_phase7_cross_ref.py` — engine tests for the simplified version
- 7 `detect_all.py` files (urgencias, odontologia, equipos_basicos, intramural, extramural, ambulatoria, hospitalizacion, farmacia) — each calls `detect_cups_sin_contrato` and overrides via `RuleBasedDetector("cups_sin_contrato")`

### Approaches

1. **New compound evaluator `cups_contratado_check`** — Best fit
   - Create `CupsContratadoEvaluator(AtomicEvaluator)` with operator `"cups_contratado"`
   - Pre-loads the 5-table JOIN in `evaluate()` (first call), caches in `self._cache`
   - Handles all 5 exceptions internally based on context.invoice_data:
     - tarifario == "Suminstros, Medicamentos" → skip
     - responsable_cierra in FACTURADORES_URGENCIAS → check nota_hoja 1/27
     - CAP + ESS118 → check nota_hoja 3
     - CAP + EPSS41 → check nota_hoja 2
     - FEV + EPS037/EPSS41 → skip
     - codigo_equiv fallback
   - Condition tree: `NOT(cups_contratado_check(invoice.codigo, invoice.codigo_entidad_cobrar))`
   - Pros: Single evaluator encapsulates all business logic; cache avoids per-row queries; same pre-load pattern as legacy; all exceptions in one place
   - Cons: Evaluator becomes ~150+ lines with hardcoded exception logic; mixing "what to check" (engine) with "how to check" (evaluator); exceptions not expressed in condition tree
   - Effort: Medium

2. **Pre-load provider + composite condition tree** — More declarative
   - Enhance `ContractProvider` (or new `CupsContratadoProvider`) to pre-load all valid pairs at domain start
   - Condition tree expresses each exception as a separate AND/OR/NOT branch:
     - `OR(farmacia_skip, urgencias_nota1, cap_ess118, cap_epss41, fev_skip, contracted_pair_check, codigo_equiv_fallback)`
   - Requires a `cat_in`-style evaluator for the pair check or a new `is_contracted_pair` evaluator
   - Pros: Each exception is visible in the condition tree (auditable); exception handler can override specific branches
   - Cons: Complex tree with 6+ branches; FEV/CAP/urgencias conditions need regex or composite values; codigo_equiv needs OR with second field lookup; significantly harder to maintain
   - Effort: High

3. **Keep legacy + simplify engine rule** — Status quo
   - Document the engine rule as intentionally simplified (catalog-only check)
   - Keep the feature flag switching between legacy and engine
   - Pros: Zero risk, no migration effort
   - Cons: Engine rule is functionally wrong (false negatives: checks catalog only, not entity contract); blocks full engine migration; feature flag creates confusion
   - Effort: None

4. **Decomposed evaluators + ExceptionHandler** — Most architectural
   - Create `ContractedPairEvaluator` (pure: checks pair against pre-loaded set, no exceptions)
   - Create separate evaluators for each exception: `UrgenciasNota1Evaluator`, `CAPEvaluator`, `FevAutorizadoEvaluator`
   - Create a `CodigoEquivFallbackEvaluator` for the OR fallback
   - Chain them in a condition tree: `NOT(OR(UrgenciasNota1, CAP, FEV, AND(ContractedPair, CodigoEquivFallback)))`
   - Farmacia skip via `ExceptionHandler` (already supported: match on tarifario)
   - Pros: Each piece is testable in isolation; exceptions visible in condition tree; ExceptionHandler works with DB-level Excepcion records
   - Cons: Very complex tree (7+ nodes); some exceptions (codigo_equiv fallback) are awkward to express declaratively; still needs custom evaluators
   - Effort: High

### Recommendation

**Approach 1 (New compound evaluator `cups_contratado_check`)** is the pragmatic choice for this migration.

The legacy detector has 4 exceptions + codigo_equiv fallback that are deeply intertwined with the contractual validation. Trying to decompose them into a condition tree (Approach 2/4) would produce a 7+ branch tree that is harder to understand and maintain than the evaluator itself. The engine's condition tree model excels at simple comparisons (eq, gt, in, exists_in_db) but doesn't express multi-step fallback chains with entity-specific branching well.

A single `CupsContratadoEvaluator` mirrors the existing legacy code structure, reuses the same DB query patterns, keeps all exception logic in one auditable place, and can be tested with the same test patterns as the legacy detector. The evaluator uses `context.invoice_data` for row values and `context.session` for DB access — both already available in the EvaluationContext.

Key design decisions for the evaluator:
- Cache strategy: pre-load all pairs + urgencias + CAP on first `evaluate()` call, same pattern as legacy
- Exception data (`FACTURADORES_URGENCIAS`, `_ENTIDADES_NOTA_URGENCIAS`, `VALOR_TARIFARIO_FARMACIA`): import from `app.constants.urgencias` as the legacy detector does
- Returns `True` when CUPS IS properly contracted (so `NOT` inverts to MATCH)
- `codigo_equiv` handling: read from `context.invoice_data.get("codigo_equiv")` if present

### Risks

- **Evaluator bloat**: The evaluator will be ~150-200 lines, larger than any existing evaluator. Mitigate with internal helper methods (same pattern as `CentroCostoCheckEvaluator`).
- **Cache invalidation**: If the DB changes mid-session, the evaluator cache is stale. Same risk as the legacy detector — acceptable for batch processing.
- **Test coverage gap**: The engine tests for `cups_sin_contrato` (in `test_snapshot_phase7_cross_ref.py`) only cover the simplified catalog check. Need to port the 30+ test scenarios from `test_detect_cups_sin_contrato.py` to the engine test framework.
- **Rollback complexity**: If the evaluator fails, all domains fail. Mitigate with try/except returning False (fails open → no false positives but possible false negatives).
- **Feature flag interaction**: All 7 `detect_all.py` files need the engine path to work correctly once the evaluator is live. The legacy detector stays as fallback until fully removed.

### Ready for Proposal

Yes
