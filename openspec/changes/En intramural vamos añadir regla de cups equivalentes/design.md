# Design: CUPS Equivalentes — Intramural

## Technical Approach

Add a new detector `detect_cups_equivalentes_intramural()` that checks each row against a lookup dict `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL`. When a match is found, emit an error dict with the correct equivalent code and action message. Wire it into `_get_intramural_detectors()` and call it inside `detect_all_problems_intramural()` replacing the existing empty placeholders.

This follows the exact same pattern as Urgencias' `detect_cups_equivalentes()` in `app/services/urgencias/cups_equivalentes.py`, but simplified: Intramural only needs a static dict lookup (no entity-based conditions), so no complex branching.

## Architecture Decisions

### Decision: Constants as a dict vs individual constants

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Dict mapping `{"906317": "1906317", "906249": "906249PR"}` | Compact, one import, easy to extend, matches proposal | ✅ **Chosen** |
| Individual constants like Urgencias (`CODIGO_CUPS_EQUIVALENTE_890205`) | More verbose, requires per-rule constants | ❌ Rejected — 1:1 mapping with no conditions doesn't need individual constants |

**Rationale**: A single dict is simpler, testable in one assertion, and trivially extensible (just add entries). The Urgencias pattern uses individual constants because rules have conditions (entidad filtering, tipo_factura checks). Intramural's rule is pure lookup — no branching needed.

### Decision: Function named `detect_cups_equivalentes_intramural`

Consistent with existing Intramural detectors: `detect_centro_costo_intramural`, `detect_ide_contrato_intramural`, `detect_bacteriologas_cronograma`. This avoids collision with Urgencias' `detect_cups_equivalentes`.

### Decision: Insert as step 10 in detect_all.py

| Reason | Detail |
|--------|--------|
| Natural insertion point | After duplicado_id_codigo (8) and revision_cantidad (9), before normalized rows (10→11) |
| No renumbering needed | Add as new step 10, renumber old 10→11 and 11→12 |

## Data Flow

```
Excel rows ──→ detect_cups_equivalentes_intramural()
                   │
                   ▼
         for each row:
           codigo = row[Código]
           factura = row[Número Factura]
           procedimiento = row[Procedimiento]
                   │
                   ▼
         lookup codigo in CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL
                   │
          ┌────────┴────────┐
          ▼                  ▼
       Match?            No match?
          │                  │
          ▼                  ▼
   [{"factura",        [empty list]
    "codigo",
    "codigo_equiv",
    "accion":
     "Usar {equiv}",
    "procedimiento"}]
          │
          ▼
   → resultado["problemas"]["cups_equivalentes"]
   → resultado["totales"]["cups_equivalentes"] = len(...)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/intramural.py` | Modify | Add `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL` dict |
| `app/services/intramural/cups_equivalentes.py` | **Create** | New detector function |
| `app/services/intramural/detect_all.py` | Modify | Import, register in `_get_intramural_detectors()`, call in `detect_all_problems_intramural()`, update placeholders |

## Interfaces / Contracts

### New constant in `app/constants/intramural.py`

```python
CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL: dict[str, str] = {
    "906317": "1906317",   # Hepatitis B (Rápida)
    "906249": "906249PR",  # VIH Prueba Rápida
}
```

### New function in `app/services/intramural/cups_equivalentes.py`

```python
def detect_cups_equivalentes_intramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
```

**Input**: `data_sheet` (openpyxl Worksheet), `indices` (column index map with `numero_factura`, `codigo`, `procedimiento` keys)
**Output**: `list[dict]` — each dict has keys: `factura` (str), `codigo` (str), `codigo_equiv` (str — the correct code), `accion` (str — e.g. "Usar 1906317"), `procedimiento` (str)
**Edge cases**: Missing index → return `[]`; empty cell or non-string → skip row

### Integration points in `detect_all.py`

- **`_get_intramural_detectors()`**: add `detect_cups_equivalentes_intramural` to the returned list
- **`detect_all_problems_intramural()`**: add call block (step 10) and populate `resultado["problemas"]["cups_equivalentes"]` and `resultado["totales"]["cups_equivalentes"]`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `num_fact_idx` or `codigo_idx` missing | Return `[]`, log warning |
| Cell value is `None`, empty, or non-string | `continue` — skip row silently |
| `procedimiento_idx` missing | Default `procedimiento` to `""` |
| Exception during row processing | Let it propagate (consistent with other detectors; caller in detect_all.py does NOT wrap in try/except for simple lookup detectors) |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Constant dict values correct | Assert `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL == {"906317": "1906317", "906249": "906249PR"}` |
| Unit | Detector finds both codes | Create minimal Worksheet fixture with rows for each code; assert 2 results |
| Unit | Detector skips non-matching codes | Add row with unrelated code; assert empty result |
| Unit | Missing columns → empty result | Call with `indices = {}`; assert `[]` |
| Integration | Wired into detect_all | Run `detect_all_problems_intramural()` with real data containing 906317; assert `problemas["cups_equivalentes"]` populated |
| Regression | Urgencias cups_equivalentes unaffected | Existing Urgencias tests pass unchanged |

## Migration / Rollout

No migration required. Three-file additive change with zero existing behavior modification.

## Open Questions

None.
