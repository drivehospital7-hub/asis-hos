# Design: migrar-sala-obs — Replace SalaObservacionEvaluator with Condition Tree

## Technical Approach

Single OR tree of 6 AND sub-rules replacing `SalaObservacionEvaluator` (operator `sala_obs_check`). Same pattern as centro_costo migration (F14): each estancia/entidad/tarifario combination becomes an explicit AND sub-rule using `date.horas` (existing provider), `cat_in` (existing evaluator), and `eq`/`NOT` composites.

The bug fix: the evaluator returned `False` for `estancia <= 2h` (no detection). Sub-rule 6 detects any sala code ≠ 5DSB01 in that range.

## Architecture Decisions

### Decision: 6 AND sub-rules vs. flat case/switch

| Option | Tradeoff | Decision |
|--------|----------|----------|
| 6 AND sub-rules under OR root | ~30 condition rows; every branch explicit & editable | ✅ **Chosen** — mirrors centro_costo pattern, fully debuggable |
| Case/switch in a single evaluator | Requires new evaluator code; not transparent | ❌ Black-box, defeats migration purpose |

### Decision: `date.horas` (int) vs. float estancia

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `date.horas` (int, truncated) | ±1h tolerance at boundaries; already wired in engine | ✅ **Chosen** — existing provider, no engine changes |
| New float provider | No tolerance, but requires new code | ❌ Unnecessary complexity for ±1h clinical tolerance |

### Decision: Deprecation pattern (same as CentroCostoCheckEvaluator)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `DeprecationWarning` + keep in registry | Safe rollback, no crash | ✅ **Chosen** — same as F14/F15 |
| Immediate removal | Cleaner, but breaks rollback | ❌ Unsafe |

### Decision: New rule version vs. in-place update

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New version (v2) | Rollback-safe; orphan old conditions | ✅ **Chosen** — `rule_base_id` versioning |
| DELETE old + INSERT new | Simpler SQL, but no rollback path | ❌ Irreversible |

## Condition Tree

```
Root: OR
├── AND(1): SOAT, >6h, sala_code, NOT(=38114)
├── AND(2): SOAT, 2-6h, sala_code, NOT(=38915)
├── AND(3): NOT SOAT, >6h, ESS, sala_code, NOT(=05DSB01)
├── AND(4): NOT SOAT, >6h, NOT ESS, sala_code, NOT(=129B02)
├── AND(5): NOT SOAT, 2-6h, sala_code, NOT(=5DSB01)
└── AND(6): ≤2h, sala_code, NOT(=5DSB01)   ← bug fix
```

Each AND child: `tipo=composite, operador=AND`, atomic leafs `tipo=atomic` with appropriate `fuente_datos`. NOT composites wrap `eq` leafs for the "code is wrong" check.

Operators per leaf:
- `eq`: tarifario, tipo_factura_descripcion comparisons
- `gt`/`gte`/`lte`: date.horas comparisons (int truncated)
- `cat_in`: codigo → `sala_codes`, codigo_entidad_cobrar → `entidades_ess`

## Catalogos Seeds

| key | value (JSONB) | descripcion |
|-----|----------------|-------------|
| `sala_codes` | `["5DSB01","05DSB01","129B02","38114","38915"]` | Códigos de sala de observación activadores |
| `entidades_ess` | `["ESS118","ESSC18"]` | Entidades ESS que usan 05DSB01 para >6h |

## Data Flow

```
Excel row → Engine → ConditionEvaluator.evaluate(tree)
  → OR short-circuits on first AND=true
    → Each AND checks: tipo_factura + tarifario + horas + cat_in + NOT(eq)
      → cat_in → CatalogInEvaluator → DB catalogos (cached per instance)
      → date.horas → DateProvider._compute_horas() → int
  → outcome=true → evidence recorded → FAIL in ResultadoAuditoria
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `seeds/migracion-engine/16_sala_observacion_condiciones.sql` | Create | OR tree conditions + catalogos seeds |
| `app/services/engine/evaluators.py` | Modify | Deprecate `SalaObservacionEvaluator` (warning), remove from `_register_builtins()` |
| `app/services/urgencias/sala_observacion.py` | Modify | Add `DeprecationWarning` at module level |
| `tests/engine/test_sala_observacion_rules.py` | Create | Equivalence tests: evaluator vs tree (with bug fix delta) |

`detect_all.py` wiring is unchanged — rule name `sala_observacion_valido` stays the same; only the condition tree under it changes.

## date.horas Boundary Tolerance

`date.horas` returns `int(diff / 3600)` (truncated). The original evaluator used `float` comparison. Threshold mapping:

| Real time | evaluator float | date.horas int | Condition |
|-----------|----------------|----------------|-----------|
| >6h | `> 6.0` | ≥7 | `gt 6` |
| 2-6h | `2 < h ≤ 6` | 2-6 | `gte 2 AND lte 6` |
| ≤2h | `h ≤ 2` | ≤1 | `lte 2` |

±1h tolerance at boundaries. Acceptable for clinical rules (±1h does not change treatment classification).

## Bug Fix: ≤2h Detection

The evaluator returned `False` for `estancia <= 2` (line 482-483: `return None` → `evaluate` exits `False`). The legacy detector DID detect wrong codes here (line 234-238). Sub-rule 6 implements the legacy behavior: any sala code other than 5DSB01 is flagged.

## Migration Plan

1. Execute seed SQL: new version of `sala_observacion_valido` (v2), DELETE old conditions, INSERT OR tree + 30 condition rows
2. Insert catalogos `sala_codes`, `entidades_ess`
3. Deploy code: deprecate evaluator + remove from registry
4. Run equivalence tests against production snapshots

**Rollback**: Revert code, restore v1 seed, delete catalogos if unused.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Tree structure validity | Build tree from seed data, verify AND/OR/NOT parent-child relationships |
| Integration | Equivalence vs evaluator | 10+ facturas × 3 scenarios each (SOAT, ESS, non-ESS). Compare evaluator output vs tree output. Bug fix: ≤2h cases produce NEW detections in tree only |
| Snapshot | 50+ real facturas | Run both evaluator and tree on production data; diff detection sets. Bug fix cases are expected additions. |

## Effort Estimate

| Component | Effort |
|-----------|--------|
| Seed SQL (tree + catalogos) | 1h |
| Deprecate evaluator | 15min |
| Tests | 2h |
| Validation + snapshot diff | 1h |
| **Total** | **~4h** |

## Open Questions

- [ ] `sala_observacion_estancia_prolongada` (gt>6h warning): should it remain separate or merge? Currently a separate rule. Merge would change existing behavior — keep separate.
- [ ] Range overlap at `horas=6` boundary: `gt 6` excludes 6, `lte 6` includes 6. `date.horas=6` matches the ≤6h branch (sub-rules 2, 5). Confirm this matches evaluator's `estancia > 6` behavior (evaluator float: 6.0 is NOT >6, so it falls to the ≤6h branch). With int: `horas=6` means real time 6.0-6.99h. Since `6.0` is not >6 (float), and `6` is `lte 6` (int), the behavior is consistent for the exact 6h case. For 6.5h: evaluator sees `>6` (True), tree sees `horas=6` which is NOT `gt 6` (False) — this is the ±1h tolerance. Acceptable.
