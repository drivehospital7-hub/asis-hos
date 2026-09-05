# Exploration: migrar-sala-obs — Replace SalaObservacionEvaluator with Condition Trees

## Current State

### Three layers coexist

| Layer | What | Status |
|-------|------|--------|
| **Legacy detector** | `app/services/urgencias/sala_observacion.py` — `detect_sala_observacion()` | Full two-pass detector (collect → validate), still active |
| **Engine evaluator** | `app/services/engine/evaluators.py` — `SalaObservacionEvaluator` (operator `sala_obs_check`) | Active, row-level black-box, registered in `detect_all.py` as `sala_observacion_valido` |
| **Engine group rules** | 6 DB rules (`sala_obs_obligatorios`, `sala_obs_ess_129b02`, `sala_obs_soat_completo`, `sala_obs_soat_prohibido`, `sala_obs_890601h`, `sala_obs_05dsb01_no_ess`) | Already condition tree-based, cover the secondary checks from legacy |

### What `sala_obs_check` evaluator does (`SalaObservacionEvaluator`, lines 444-488)

Per-row evaluator, returns `True` (detection) when a sala code doesn't match what's expected:

1. **Filter**: Only `tipo_factura_descripcion == "Urgencias"`
2. **SALA_CODES gate**: `row_value` must be in `{"5DSB01", "05DSB01", "129B02", "38114", "38915"}`
3. **Estancia**: Computes hours between `fec_factura` and `fecha_cierre`
4. **Expected code** logic (`_codigo_esperado`):
   - `estancia <= 2` → `None` (bails out, returns `False` — **no detection for this case**)
   - `tarifario == "SOAT"` → `"38114"` if `> 6h`, `"38915"` if `<= 6h`
   - `estancia > 6`, not SOAT → `"05DSB01"` if entity in `{ESS118, ESSC18}`, else `"129B02"`
   - Otherwise → `"5DSB01"`
5. **Detection**: `code != expected_code` → `True`

### What the Legacy Detector does (beyond the evaluator)

The legacy `detect_sala_observacion()` has a **group-level** two-pass approach:

**Pass 1**: Collect per-factura data (entidad, tarifario, estancia_horas, set of codigos_sala, set of codigos_urgencias_obligatorios, etc.)

**Pass 2**: Validates multiple rules against collected data:
1. **Estancia rule** (same as evaluator) — estancia + entidad + tarifario → expected code
2. **Estancia <= 2h rule**: any code that's NOT 5DSB01 is an error **(MISSING from evaluator — evaluator bails with `return False`)**
3. **ESS118/ESSC18 can't have 129B02** → covered by `sala_obs_ess_129b02`
4. **Urgencias can't have 890601H** → covered by `sala_obs_890601h`
5. **05DSB01 prohibited in non-ESS** → covered by `sala_obs_05dsb01_no_ess`
6. **Mandatory codes 890701+890601 when sala activators present** → covered by `sala_obs_obligatorios`
7. **SOAT sala completeness (39145+39131 when 38114/38915)** → covered by `sala_obs_soat_completo`
8. **SOAT Urgencias can't have 39133** → covered by `sala_obs_soat_prohibido`
9. **Exception: tipo_identificacion=CN or reingreso≠0 → 890701 NOT mandatory** → **MISSING from `sala_obs_obligatorios`**

### Existing DB Rules Using Engine

From SQL seeds and backups:

| Rule ID | DB Name | Type | Current Tree | Notes |
|---------|---------|------|-------------|-------|
| ~30 | `sala_observacion_estancia_prolongada` | row-level warning | `AND(gt(date.horas, 6), eq(tipo_factura_descripcion, "Urgencias"))` | Already explicit tree, no evaluator |
| ~30 | `sala_observacion_valido` | row-level | `atomic(sala_obs_check, invoice.codigo, "")` | **This is the one to migrate** |
| ~48 | `sala_observacion_entidad` | row-level | `AND(gt(date.horas, 6), in(codigo_entidad_cobrar, ["EPSS41","EPSI05","EPSIC5"]))` | Already explicit tree |
| ~49 | `sala_obs_check_set` | group-by | `collect_set(codigo)` → set_contains_all | Legacy transitional |
| — | `sala_obs_obligatorios` | group-by | collect_set → set_intersects + NOT set_contains_all | Via admin UI |
| — | `sala_obs_ess_129b02` | group-by | collect_set → set_intersects + contains | Via admin UI |
| — | `sala_obs_soat_completo` | group-by | collect_set → set_intersects + NOT set_contains_all | Via admin UI |
| — | `sala_obs_soat_prohibido` | group-by | collect_set → contains | Via admin UI |
| — | `sala_obs_890601h` | group-by | collect_set → contains | Via admin UI |
| — | `sala_obs_05dsb01_no_ess` | group-by | collect_set → contains + NOT set_intersects | Via admin UI |

### How `detect_all.py` wires it today

```python
# Engine path for sala_obs:
problemas_cups_equivalentes.extend(
    RuleBasedDetector("sala_observacion_valido", ...).detect(...)  # ← evaluator
)
for rule_name in [
    "sala_obs_obligatorios",      # group rule (already tree)
    "sala_obs_ess_129b02",        # group rule (already tree)
    "sala_obs_soat_completo",     # group rule (already tree)
    "sala_obs_soat_prohibido",    # group rule (already tree)
    "sala_obs_890601h",           # group rule (already tree)
    "sala_obs_05dsb01_no_ess",    # group rule (already tree)
]:
    problemas_cups_equivalentes.extend(RuleBasedDetector(rule_name, ...).detect(...))
```

Additionally, `sala_observacion_estancia_prolongada` (warning) and `sala_observacion_entidad` are also running via their respective `RuleBasedDetector` calls, each as row-level tree rules.

**But**: these two row-level rules are NOT called in `detect_all.py` — they appear to be called via `evaluate_sheet_domain()` somewhere or from `tipo_factura_registry.py`. Let me trace...

Looking at `detect_all.py`, only `sala_observacion_valido` and the 6 group rules are called there. The `sala_observacion_estancia_prolongada` and `sala_observacion_entidad` row-level rules appear to run through a different path (likely `tipo_factura_registry.py` or direct evaluation).

---

## Affected Areas

- `app/services/engine/evaluators.py` — `SalaObservacionEvaluator` (deprecate after migration)
- `app/services/engine/evaluators.py` — `EVALUATOR_REGISTRY` (remove from registry)
- `app/constants/urgencias.py` — all SALA_OBSERVACION constants (may add catalog seeds)
- `seed/migracion-engine/` — new seed file (e.g., `16_sala_observacion_condiciones.sql`)
- `seed/migracion-engine/13_catalogos_centro_costo.sql` or new catalog seed — add `sala_codes` + `entidades_ess` catalogos entries
- `app/services/urgencias/detect_all.py` — update wiring: replace `sala_observacion_valido` with new tree-based rule
- `tests/engine/test_sala_observacion_rules.py` — add tests for new tree-based estancia check
- `tests/engine/test_snapshot_phase5_date.py` — update if `_estancia_prolongada_conditions` changes
- `app/services/urgencias/sala_observacion.py` — legacy detector (may keep until full retirement)

---

## Approaches

### Approach A: Single row-level rule replacing the evaluator

Replace `sala_observacion_valido` (currently `atomic(sala_obs_check, ...)`) with an explicit OR tree of AND sub-trees:

```
Root: OR
├── AND(                                             # SOAT > 6h → needs 38114
│     ├── eq(tarifario, "SOAT")
│     ├── gt(date.horas, 6)
│     ├── cat_in(sala_codes, codigo)
│     └── NOT(eq(codigo, "38114"))
│   )
├── AND(                                             # SOAT 2-6h → needs 38915
│     ├── eq(tarifario, "SOAT")
│     ├── gt(date.horas, 2)
│     ├── lte(date.horas, 6)
│     ├── cat_in(sala_codes, codigo)
│     └── NOT(eq(codigo, "38915"))
│   )
├── AND(                                             # No-SOAT > 6h + ESS → needs 05DSB01
│     ├── NOT(eq(tarifario, "SOAT"))
│     ├── gt(date.horas, 6)
│     ├── cat_in(entidades_ess, codigo_entidad_cobrar)
│     ├── cat_in(sala_codes, codigo)
│     └── NOT(eq(codigo, "05DSB01"))
│   )
├── AND(                                             # No-SOAT > 6h + non-ESS → needs 129B02
│     ├── NOT(eq(tarifario, "SOAT"))
│     ├── gt(date.horas, 6)
│     ├── NOT(cat_in(entidades_ess, codigo_entidad_cobrar))
│     ├── cat_in(sala_codes, codigo)
│     └── NOT(eq(codigo, "129B02"))
│   )
├── AND(                                             # No-SOAT 2-6h → needs 5DSB01
│     ├── NOT(eq(tarifario, "SOAT"))
│     ├── gt(date.horas, 2)
│     ├── lte(date.horas, 6)
│     ├── cat_in(sala_codes, codigo)
│     └── NOT(eq(codigo, "5DSB01"))
│   )
└── AND(                                             # ≤ 2h → only 5DSB01 allowed
      ├── lte(date.horas, 2)
      ├── cat_in(sala_codes, codigo)
      └── NOT(eq(codigo, "5DSB01"))
    )
```

**This also fixes the legacy bug**: the evaluator bailed out for `estancia <= 2` (returned `False` even when code was wrong). The tree catches this case explicitly.

**Catalogos needed** (seeded to `catalogos` table):
- `sala_codes` → `["5DSB01", "05DSB01", "129B02", "38114", "38915"]`
- `entidades_ess` → `["ESS118", "ESSC18"]`

**Pros**:
- Single rule replaces the entire evaluator
- Every sub-rule is transparent, auditable, and editable via the condition tree editor
- Fixes the `estancia <= 2` gap
- Same centro_costo migration pattern
- `cat_in` provides case-insensitive matching (fixes any casing bugs)

**Cons**:
- Tree is ~30 condition rows (6 sub-rules × ~5 conditions each + root)
- 6 redundant `cat_in(sala_codes, codigo)` checks (but necessary without row-level pre-filter)
- Slightly more DB round-trips for `cat_in` lookups (6 per row) — though each cat_in is cached in-memory per evaluator instance

**Effort**: Medium

### Approach B: Use a row-level pre-filter + simpler OR tree

Use the engine's exception mechanism or a dedicated "skip if not sala code" filter. If we extend the engine to support a `skip_condition` at the rule level (simpler than a full pre-filter), we can remove the redundant `cat_in(sala_codes, codigo)` from each sub-rule.

But this requires engine changes — more invasive, higher risk.

**Effort**: Medium-High (engine change + new rule)

### Approach C: Mixed — keep evaluator but add missing rules as condition trees

Keep `SalaObservacionEvaluator` as-is and only add a new rule for the `estancia <= 2` gap. This is the minimum viable change.

**Effort**: Low

**But**: this leaves the black-box evaluator in place, defeating the purpose of the migration. Not recommended.

---

## Recommendation

**Approach A**: Single row-level OR tree replacing `sala_obs_check`.

Rationale:
- Same pattern as centro_costo migration (F14/F15) — team already knows this
- The `date.horas` provider already computes estancia correctly (proven by `sala_observacion_estancia_prolongada`)
- `cat_in` + catalogos provides the same constant-set lookups already proven in F13
- Fixes the existing `estancia <= 2` detection gap
- All sub-rules become visible and editable
- Creates audit trail via evidence per sub-rule branch

### Detailed Steps

1. **Seed catalogos**: `sala_codes` and `entidades_ess` in the `catalogos` table (new seed file)
2. **Create seed SQL**: new rule `sala_observacion_valido` OR tree replacing the evaluator
   - Either update the existing rule's conditions (requires deleting old ones first) OR
   - Create a new rule version (cleaner, allows rollback)
3. **Deprecate evaluator**: Mark `SalaObservacionEvaluator` with DeprecationWarning (like `CentroCostoCheckEvaluator`)
4. **Remove from registry**: Remove `SalaObservacionEvaluator()` from `_register_builtins()`
5. **Update `detect_all.py`**: Replace `sala_observacion_valido` reference
6. **Tests**: Update tests to use condition tree assertions, not evaluator mock

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Equivalence gap**: condition tree might not match evaluator behavior exactly | Wrong detections | Snapshot test against production Excel files before/after migration (same approach as centro_costo) |
| **Performance**: 6 `cat_in` DB lookups per row | Slower processing | `CatalogInEvaluator` has per-instance cache (1st row hits DB, subsequent rows are cached) |
| **Tree complexity**: 30+ condition nodes | Hard to maintain/verify in admin UI | Well-documented seed SQL with comments per sub-tree (same as F14/F15) |
| **Missing rule**: `sala_obs_obligatorios` doesn't have the `tipo_identificacion=CN` exception from legacy | False positives | Add exception as a separate task in the same change, or document as known legacy gap |
| **Duplicate detections**: tree might fire for rows that are ALSO caught by group rules | Over-reporting | Quick check: group rules fire at factura level, tree fires at row level — they detect different things; no dedup needed |
| **Ordering of hora threshold**: `lte(date.horas, 6)` vs `gt(date.horas, 6)` boundary | Off-by-one at exactly 6h | Verify both evaluator and legacy use `>` for ">6" and `<=` for "≤6" — matching `_codigo_esperado` which does `estancia > 6` |

---

## Ready for Proposal

**Yes**.

### What the orchestrator should tell the user

> Migrar `SalaObservacionEvaluator` (sala_obs_check) a árbol de condiciones es viable y sigue el mismo patrón que centro_costo. Se reemplaza el evaluador con un árbol OR de 6 sub-árboles AND, cada uno representando una rama de la lógica de estancia/entidad/tarifario. Además se corrige un bug: la regla para estancia ≤ 2h (solo 5DSB01 permitido) no se disparaba en el evaluador actual. Se necesitan 2 catálogos nuevos (sala_codes, entidades_ess). Esfuerzo estimado: **Medium** — comparable a la migración de centro_costo (F14).
