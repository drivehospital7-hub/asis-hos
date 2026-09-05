# Design: /procesar UI Consistency — Handler Standardization

## Technical Approach

Standardize all 24 handlers across `build_odontologia_normalized_rows` (13 handlers) and `build_normalized_rows` (11 handlers) to a single pattern: **descripcion from `item["problema"]`, procedimiento from `_build_procedimiento(codigo, procedimiento)`, detalle from domain-specific value**. Add a generic fallback when both procedimiento and detalle are empty. Fix the 3 P0 handlers (ruta_duplicada, cantidades_urgencias, duplicados_farmacia) that produce broken rows with engine-enriched input.

No new modules. Both files are pure dict→dict transformations — the change is contained to handler logic inside existing loops.

## Architecture Decisions

### Decision: Single `_build_procedimiento` for ALL handlers

| Option | Tradeoff |
|--------|----------|
| Keep ad-hoc assignments per handler | Fragile, inconsistent (some use `codigo_profesional`, some use `tipo_procedimiento`, some hardcode) |
| **One function, always called with `codigo, procedimiento`** | Consistent; `_build_procedimiento` already exists in both files — just call it everywhere |

**Rationale**: Every row-by-row engine-enriched dict has `codigo` and `procedimiento`. Using them uniformly means procedimiento column always shows the CUPS code + procedure name, which is the correct semantic for "the object being audited". Group-by rules (sparse) get empty procedimiento — the generic fallback handles it.

### Decision: `descripcion` = `item.get("problema", "")` OR fallback

| Option | Tradeoff |
|--------|----------|
| Keep hardcoded per-type descriptions | Breaks with engine (engine provides `problema`), duplicates DB-stored rule descriptions |
| **Always use `problema` if present, fallback to hardcoded** | Single source of truth. Engine stores `rule.descripcion` in `problema`. When engine is off, hardcoded fallback preserves legacy behavior |

**Rationale**: The engine ALWAYS populates `problema` for row-by-row rules (it's `rule.descripcion`). Hardcoded text was a pre-engine pattern. Using `problema` gives the actual rule description from the DB — more accurate and maintainable.

### Decision: Generic fallback for empty procedimiento + detalle

| Option | Tradeoff |
|--------|----------|
| Leave empty columns | Confusing UI — user sees blank cells with no context |
| **Use first non-factura key:value as detalle** | Provides fallback context without hiding structural issues. Add a debug log so it's auditable |

**Rationale**: The `/procesar` React page already renders empty cells gracefully, but a blank procedimiento + blank detalle provides zero debugging value. The fallback uses `row_data` keys from engine enrichment, which at least shows something context-relevant.

### Decision: Fix P0 handlers in-place, no new abstractions

| Option | Tradeoff |
|--------|----------|
| Extract P0 handlers to separate module | Over-engineering — these are 3 loops out of 24 |
| **Fix in-place with guards + fallback keys** | Minimal diff, same pattern as all other handlers |

**Rationale**: The P0 handlers fail because they read keys the engine doesn't provide (`facturas`, `cantidad_repeticiones`, `pares_duplicados`). Adding `item.get("...", "")` guards and using available keys (engine provides `identificacion`, `problema`, `codigo_tipo_procedimiento`) fixes them. No structural change needed.

## Data Flow

```
Engine-enriched dict              normalized_rows handler         6-column output
┌──────────────────────┐          ┌─────────────────────┐         ┌────────────────┐
│ factura              │          │ _build_procedimiento│         │ tipo_error     │
│ problema             │─────────▶│ (codigo, proc)      │────────▶│ factura        │
│ codigo               │          │                     │         │ fec_factura    │
│ procedimiento        │          │ item.get("problema")│         │ responsable    │
│ vlr_subsidiado       │          │                     │         │ descripcion    │
│ (more row_data...)   │          │ domain-specific     │         │ procedimiento  │
└──────────────────────┘          │ detalle logic       │         │ detalle        │
                                  └─────────────────────┘         └────────────────┘
                                              │
                                              ▼
                                   Generic fallback:
                                   If procedimiento AND detalle
                                   are both empty → use first
                                   non-factura row_data key:value
```

Group-by rules (sparse dicts with only `factura, problema, regla, severidad`) produce empty procedimiento + empty detalle → fallback fires with non-empty `problema` → descripcion is set, procedimiento/detalle stay empty. The React page renders this as a row with description but no code/detail — acceptable for group-by.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/odontologia/normalized_rows.py` | Modify | Standardize 13 handlers to common pattern; add generic fallback; fix ruta_duplicada (P0) |
| `app/services/normalized_rows.py` | Modify | Standardize 11 handlers to common pattern; add generic fallback; fix cantidades_urgencias + duplicados_farmacia (P0) |
| `tests/services/test_odontologia_normalized_rows.py` | Modify | Add snapshot tests: engine-enriched input → verify 6-column output per handler |
| `tests/services/test_normalized_rows_shared.py` | Modify | Add snapshot tests: engine-enriched input → verify 6-column output per handler |

## Interfaces / Contracts

No new interfaces. The existing contract is unchanged:

```python
# Builder input: enriched dicts (engine) OR legacy detector dicts
# Builder output: list[dict] with keys:
#   tipo_error, factura, fec_factura, responsable_cierra,
#   descripcion, procedimiento, detalle [, fecha_cierre_vacia]

# Internal helper (already exists in both files):
def _build_procedimiento(codigo: str, procedimiento: str) -> str:
    ...

# New generic fallback:
# After all handlers process, if procedimiento == "" and detalle == "":
#   for k, v in item.items():
#       if k != "factura" and v:
#           detalle = f"{k}: {v}"
#           break
```

## Handler Standardization Matrix

### `build_odontologia_normalized_rows` (odontologia/normalized_rows.py)

| Handler | descripcion change | procedimiento change | detalle change |
|---------|-------------------|---------------------|----------------|
| Decimales | `problema` or "Valores con decimales" | `_build_procedimiento(codigo, proc)` or `valores` | `f"Sub: {vlr_sub}, Proc: {vlr_proc}"` if present |
| Doble Tipo | `problema` or "Múltiples tipos de procedimiento" | `_build_procedimiento(código, proc)` | `tipo_procedimiento` or `tipos` |
| Ruta Duplicada (P0 fix) | `problema` or `f"Paciente con {cantidad} facturas"` | `facturas` (comma-separated) or `identificacion` | `identificacion` |
| Profesionales | `problema` or `regla` | `_build_procedimiento(cod_prof, proc)` | `problema` (already correct) |
| Cantidades | `problema` or `f"Cantidad anómala: {cantidad}"` | `_build_procedimiento(codigo, proc)` | `str(cantidad)` |
| Tipo ID / Edad | `problema` or inferred desc | `numero_identificacion` | age string |
| Tipo ID / Entidad | `problema`-based (already correct) | `cod_actual` | detail string |
| Centro Costo | `problema` or `f"Centro debería ser {centro_deberia}"` | `_build_procedimiento(codigo, proc)` | `centro_actual` or `centro_costo` |
| IDE Contrato | `problema` or generated desc | `_build_procedimiento(codigo, "")` | `ide_actual` |
| Código Entidad vs Af. | `problema` (already correct) | `cod_actual` or proc_entidad | detail string |
| Tipo Usuario | `problema` or "Revisar tipo usuario en Targetero" | `_build_procedimiento(codigo, proc)` | `tipo_actual` or `tipo_usuario` |
| Cups Sin Contrato | `problema` (already correct) | `_build_procedimiento(codigo, proc)` | entidad detail |

### `build_normalized_rows` (shared/normalized_rows.py)

| Handler | Key changes |
|---------|------------|
| Centros de Costo | desc = `problema` or fallback; detalle = `centro_actual` or `centro_costo` |
| IDE Contrato | desc = `problema` or generated; detalle = `ide_contrato_actual` or `ide_contrato` |
| Cups Equivalentes | desc = `problema` or `accion`; detalle uses `codigo_str` fallback |
| MAL CAPITADO | desc = `problema` or `observacion`; detalle = `ide_contrato` or `ide_contrato_actual` |
| Cantidades (P0 fix) | desc = `problema` or template; catch KeyError on `cantidad_esperada` |
| Decimales | (list of strings) keep as-is — not dict-based |
| Tipo ID / Edad | desc = `problema` or generated; fallback for missing `tipo_deberia` |
| Profesionales | (already correct — uses `problema` and `_build_procedimiento`) |
| Código Entidad vs Af. | (already correct) |
| Tipo Usuario | desc = `problema` or hardcoded; procedimiento = `_build_procedimiento` |
| Revisión Necesaria | (already correct — uses `descripcion`/`problema` fallback) |
| Copago vs Entidad | (already correct) |
| Duplicados Farmacia (P0 fix) | guard missing `pares_duplicados`/`total_pares` with `.get()` defaults |
| Cups Sin Contrato | (already correct) |
| Cups No CAPITA | desc = `problema` or `observacion` |
| Duplicado ID+Código | desc = `problema` or `f"Procedimiento duplicado x{repeticiones}"` |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — per handler | Engine-enriched input → correct 6-column output | Add test methods to existing test classes. One test per handler with (a) engine-enriched dict, (b) legacy format, (c) empty/missing keys. Verify all 3 content columns (desc, proc, det) |
| Unit — generic fallback | Empty procedimiento + empty detalle → fallback fires | Input dict with only `factura` and `problema` (simulates group-by sparse output) → verify detalle uses first non-factura key |
| Unit — P0 handlers | Broken cases with engine data | ruta_duplicada: engine provides `identificacion` but no `facturas`/`cantidad`. cantidades_urgencias: no `cantidad_esperada`. duplicados_farmacia: no `pares_duplicados` list |
| Regression | Existing tests still pass | All 23 existing tests MUST pass unchanged |

**Method**: Pure dict→dict tests. No Excel files, no snapshots — each test constructs the input dict inline and asserts on the output dict. This matches the existing TDD pattern (see `tests/services/test_normalized_rows_shared.py`).

Key test scenarios per handler (example for Centro Costo):

```python
def test_centro_costo_con_engine_enriched(self):
    """Engine provides centro_costo instead of centro_actual."""
    rows = build_normalized_rows(
        error_groups={
            "Centros de Costo": [{
                "factura": "FAC-001",
                "codigo": "C001",
                "procedimiento": "CONSULTA",
                "centro_costo": "CC-A",
                "problema": "Centro de costo no coincide con profesional",
            }]
        },
        responsables_map={},
    )
    assert rows[0]["descripcion"] == "Centro de costo no coincide con profesional"
    assert rows[0]["procedimiento"] == "C001 - CONSULTA"
    assert rows[0]["detalle"] == "CC-A"
```

## Migration / Rollout

No migration required. Both files are pure data transformations with no external dependencies. Changes are deployed on next server restart.

Rollback: `git revert` the commit touching both `normalized_rows.py` files. No DB or schema involved.

## Open Questions

- [ ] Do group-by rules currently exist in seed data? Exploration says "none migrated yet" — verify in DB to confirm fallback logic path is tested.
- [ ] Should the generic fallback log via `logger.debug` or `logger.warning`? Debug-level is safer to avoid noise — settled.
