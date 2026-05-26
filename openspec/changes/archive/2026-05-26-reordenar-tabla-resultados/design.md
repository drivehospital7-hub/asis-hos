# Design: Reordenar Tabla de Resultados

## Technical Approach

Two independent changes across 3 areas (odontología, urgencias, equipos básicos):
1. **Remove Acción column** — simple DOM deletion in 3 React pages
2. **Add Fec. Factura as first column** — mirror the existing `responsable_cierra` pattern: scan raw sheet → build `{factura: fec_factura}` map → pass to normalized rows → include in JSON response → render in React

## Architecture Decisions

### Decision: Mirror `responsable_cierra` pattern for `fec_factura`

| Option | Tradeoff |
|--------|----------|
| Extract in route as additional pass | Duplicates iteration logic; diverges from established convention |
| Mirror `responsable_cierra` | Same scan loop, same data flow, minimal surprise — 3hits the codebase idiom exactly |

**Chosen**: Mirror `responsable_cierra`. Rationale: the pattern is proven, tested, and identical in structure (factura-keyed map from raw sheet → per-row enrichment). No new patterns needed.

### Decision: Pass `fec_factura_map` as separate parameter (not merged with `responsable_cierra`)

| Option | Tradeoff |
|--------|----------|
| Merge into `responsable_cierra` dict | Semantic mismatch — `responsable_cierra` is for enrichment, not data passthrough |
| Separate param | Clear responsibility; follows `fecha_cierre_vacia_map` precedent in urgencias |

**Chosen**: Separate `fec_factura_map` parameter. Keeps each map single-purpose and self-documenting.

### Decision: Equipos básicos reuses odontología's normalized_rows builder

Equipos básicos calls `build_odontologia_normalized_rows()`. Adding `fec_factura_map` to its signature affects both odontología AND equipos básicos from one change. No branching needed.

## Data Flow

```
Excel Sheet
    │
    ├─► detect_all.py
    │     ├─ Scan rows 2..max_row
    │     ├─ Build {factura_normalized: fec_factura_raw} map
    │     └─ Pass map to build_*_normalized_rows()
    │
    ├─► normalized_rows.py
    │     └─ For each normalized row dict, add "fec_factura" key
    │
    ├─► route (excel_headers.py / urgencias.py / odontologia_equipos_basicos.py)
    │     ├─ Include "fec_factura" in all_items[] dict
    │     └─ Prepend "Fec. Factura" to columnas array
    │
    └─► React page (page.tsx)
          ├─ Remove <th>Acción</th> + <td><Button>Controlar</Button></td>
          └─ Add <th>Fec. Factura</th> first, render item.fec_factura
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/odontologia/detect_all.py` | Modify | Build `fec_factura_map` from raw sheet (lines 80-93 pattern copied); pass to `build_odontologia_normalized_rows()` |
| `app/services/odontologia/normalized_rows.py` | Modify | Add `fec_factura_map: dict[str, str]` param; add `fec_factura` key to every row dict via `_get_fec_factura()` helper |
| `app/services/urgencias/detect_all.py` | Modify | Same fec_factura_map build (lines 216-229 pattern); pass to `build_urgencias_normalized_rows()` |
| `app/services/urgencias/normalized_rows.py` | Modify | Same param + helper; add `fec_factura` to every row |
| `app/services/equipos_basicos/detect_all.py` | Modify | Build fec_factura_map (same pattern); pass to `build_odontologia_normalized_rows()` |
| `app/routes/excel_headers.py` | Modify | Include `"fec_factura": row.get("fec_factura", "")` in all_items; prepend `"Fec. Factura"` to columnas |
| `app/routes/urgencias.py` | Modify | Same |
| `app/routes/odontologia_equipos_basicos.py` | Modify | Same |
| `frontend/src/pages/odontologia/page.tsx` | Modify | Remove `<th>Acción</th>` and `<td><Button>Controlar</Button></td>`; add `<th>Fec. Factura</th>` as first `<th>`; add `<td>{f.fec_factura}</td>` as first `<td>` |
| `frontend/src/pages/urgencias/page.tsx` | Modify | Same |
| `frontend/src/pages/odontologia-equipos-basicos/page.tsx` | Modify | Same |

## Interfaces / Contracts

### Normalized row shape (after change)

Each dict in `normalized_rows` gains one key:

```python
{
    "tipo_error": str,
    "factura": str,
    "fec_factura": str,          # ← NEW (empty string fallback)
    "responsable_cierra": str,
    "descripcion": str,
    "procedimiento": str,
    "detalle": str,
}
```

Urgencias rows also keep their existing `fecha_cierre_vacia: bool`.

### fec_factura_map parameter

```python
# Type
fec_factura_map: dict[str, str]  # {factura_normalized: raw_fec_factura_value}

# Usage in detect_all.py (all 3 areas) — modeled on responsable_cierra block
fec_factura_map: dict[str, str] = {}
fec_factura_idx = indices.get("fec_factura")
if fec_factura_idx is not None and num_fact_idx is not None:
    for row in range(2, data_sheet.max_row + 1):
        numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura = normalize_invoice(numero)
        if not factura:
            continue
        raw = data_sheet.cell(row=row, column=fec_factura_idx + 1).value
        val = str(raw).strip() if raw else ""
        if val and factura not in fec_factura_map:
            fec_factura_map[factura] = val
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `fec_factura_map` builds correctly in detect_all | Assert dict has expected keys/values given known row data |
| Unit | Empty/None fec_factura cells produce `""` fallback | Insert None cell → assert row gets empty string |
| Integration | JSON response includes `fec_factura` in every item | POST to each route → assert `all_items[*].fec_factura` exists |
| Integration | `columnas` array starts with "Fec. Factura" | Assert columnas[0] == "Fec. Factura" |
| Visual | Acción column absent from rendered table | Manual check in browser for all 3 pages |
| Regression | `pytest -v` passes with no failures | Run full test suite |

## Migration / Rollout

No migration required. This is a UI + data passthrough change — no schema, no DB, no stored state.

## Open Questions

None.
