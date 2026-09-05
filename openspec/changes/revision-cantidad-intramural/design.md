# Design: Revisión Cantidad Intramural

## Technical Approach

New detector `detect_revision_cantidad_intramural()` following the Urgencias rule-cascade pattern from `app/services/urgencias/revision_cantidad.py`, but simplified for Intramural: no `tipo_factura` filter, no exento/límite-específico tables, and area-specific thresholds (2/12/1 vs 2/20/1). Items flagged as `"⚠️ Revisión Necesaria"` — human review, not auto-error.

## Architecture Decisions

### Decision: Rule cascade order mirrors Urgencias — first match wins

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Evaluate all rules independently | Multiple flags per row, noisy output | ❌ Rejected |
| **First-match cascade (02→03/04→General)** | One reason per row, clean output | ✅ Chosen |

### Decision: No `tipo_factura` filter

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Filter by "Intramural" | Redundant — `detect_all` only called for Intramural rows | ❌ Rejected |
| **Process all rows unconditionally** | Simpler, matches caller contract | ✅ Chosen |

### Decision: Item dict includes `codigo_tipo_procedimiento` and `detalle`

Per spec (R6), each flagged item carries `factura`, `codigo`, `procedimiento`, `cantidad`, `codigo_tipo_procedimiento`, `laboratorio`, `detalle` — slightly richer than the Urgencias variant, which omits `codigo_tipo_procedimiento` and `detalle`.

### Decision: New constants in `app/constants/intramural.py`

All thresholds live in the Intramural constants module per spec's non-functional requirement. No extraction or sharing with Urgencias — the values differ and they're domain-specific.

## Data Flow

```
data_sheet (Worksheet) + indices
        │
        ▼
  detect_revision_cantidad_intramural()
        │
        ├─ For each row (2..max_row):
        │    1. Read numero_factura, codigo, cantidad, procedimiento,
        │       codigo_tipo_procedimiento, laboratorio
        │    2. Apply rule cascade:
        │       02 + Lab=No → max 2  (skip if None columns)
        │       03 or 04    → max 12
        │       else        → max 1
        │    3. If exceeds threshold → append flagged item
        │
        └─ Returns list[dict] (empty if missing Cantidad column)
                 │
                 ▼
        detect_all_problems_intramural()
        │
        ├─ Error group: "⚠️ Revisión Necesaria"
        ├─ resultado["problemas"]["revision_cantidad"]
        └─ resultado["totales"]["revision_cantidad"]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/intramural.py` | Modify | Add threshold constants |
| `app/services/intramural/revision_cantidad_intramural.py` | **Create** | New detector with rule cascade |
| `app/services/intramural/detect_all.py` | Modify | Import, call, register in error_groups + resultado |
| `tests/services/intramural/test_revision_cantidad_intramural.py` | **Create** | Unit tests via `_build_workbook` |
| `tests/services/test_intramural_detect_all.py` | Modify | Add integration test for new key |

## Interfaces / Contracts

```python
def detect_revision_cantidad_intramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Returns flagged items. Each item:
    {
        "factura": str,
        "codigo": str,
        "procedimiento": str,
        "cantidad": int | float,
        "codigo_tipo_procedimiento": str,
        "laboratorio": str,
        "detalle": str,       # Human-readable why flagged
    }
    Empty list if Cantidad column missing.
    """
```

New constants in `app/constants/intramural.py`:

```python
CODIGO_TIPO_PROC_02 = "02"
CODIGOS_TIPO_PROC_03_04: frozenset[str] = frozenset({"03", "04"})
LABORATORIO_NO = "No"
CANTIDAD_MAX_02_NO_LAB: int = 2
CANTIDAD_MAX_03_04: int = 12
CANTIDAD_MAX_GENERAL_INTRAMURAL: int = 1
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | All 3 rules + edge cases | `_build_workbook` pattern from existing tests: row-level scenarios per spec |
| Unit | Graceful degradation | Missing column → empty list, exceptions never raised |
| Unit | Detalle format | Verify human-readable message contains expected values |
| Integration | Key in `error_groups` | `"⚠️ Revisión Necesaria"` present in detect_all output |
| Integration | `_get_intramural_detectors()` | New detector registered |
| Integration | Totals count | `resultado["totales"]["revision_cantidad"]` matches items count |

## Migration / Rollout

No migration required. Pure additive change — existing pipeline unaffected. Unregistered detectors simply return nothing.

## Open Questions

None — spec is complete and the Urgencias pattern provides full precedent.
