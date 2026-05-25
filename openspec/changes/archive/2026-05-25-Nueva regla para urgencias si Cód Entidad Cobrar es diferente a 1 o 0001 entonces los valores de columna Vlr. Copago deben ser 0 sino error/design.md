# Design: Copago vs Entidad — Urgencias

## Technical Approach

New per-row detector in `app/services/urgencias/` that validates: if `Cód Entidad Cobrar` is NOT `"1"` or `"0001"`, the `Vlr. Copago` MUST be `0`. Wired into the existing Urgencias pipeline: `detect_all.py` → `normalized_rows.py` → `exporter.py`.

## Architecture Decisions

### Decision: Per-row (no dedup)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Per-factura dedup | Skips rows, hides valid errors | Rejected |
| Per-row | Each row evaluated independently, same factura can appear multiple times | **Chosen** — spec R3 requires it |

### Decision: Copago parsing with try/float

| Option | Tradeoff | Decision |
|--------|----------|----------|
| `float(val)` raw | Crashes on string garbage | Rejected |
| `try: float(val or 0)` | Strings like `"500"` → 500.0; `None`/empty → 0 | **Chosen** — spec R2 |

### Decision: Normalization on normalized_rows.py

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New section in `build_urgencias_normalized_rows` | Follows existing pattern (same as revision_entidad_86, revision_cantidad) | **Chosen** — minimal new code |

## Data Flow

```
Excel (.xlsx)
    │
    ▼
exporter.py:_do_detect_problems()
    │  reads headers → required_headers (add "vlr_copago")
    │                                                
    ▼                                                
indices dict {..., "vlr_copago": int|None}           
    │                                                
    ▼                                                
detect_all_problems_urgencias()
    │  calls detect_copago_entidad_urgencias(sheet, indices)
    │                                                
    ▼                                                
detect_copago_entidad_urgencias()
    │  per-row: if cod_ent ∉ {"1","0001"} and copago ≠ 0 → error
    │  returns list[{"factura","codigo","procedimiento","entidad_cobrar","vlr_copago"}]
    │                                                
    ▼                                                
build_urgencias_normalized_rows()
    │  new section: tipo_error="Copago vs Entidad"
    │  descripción: "Vlr. Copago debe ser 0 cuando entidad no es default"
    │  detalle: "Ent: {entidad}, Copago: {vlr_copago}"
    │                                                
    ▼                                                
resultado["problemas"]["normalizados"]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/urgencias/detect_copago_entidad.py` | Create | New detector, follows revision_entidad_86 pattern but per-row |
| `app/services/urgencias/detect_all.py` | Modify | Import + call + wire into resultado dict + normalized_rows args |
| `app/services/urgencias/normalized_rows.py` | Modify | New `copago_entidad` parameter; "Copago vs Entidad" section + fecha_cierre_vacia |
| `app/services/exporter.py` | Modify | Add `"vlr_copago": "Vlr. Copago"` to `required_headers` |
| `app/constants/columnas.py` | Modify | Add `"Vlr. Copago"` to `URGENCIA_COLUMNS_TO_KEEP` |
| `tests/test_urgencias_copago_entidad.py` | Create | Unit tests with openpyxl worksheet builder |

## Interfaces / Contracts

### Detector function signature

```python
def detect_copago_entidad_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
    """
    Returns:
        List[dict] with keys: factura, codigo, procedimiento, entidad_cobrar, vlr_copago
    """
```

### Error dict keys

```python
{
    "factura": str,          # normalized invoice
    "codigo": str,           # CUPS code
    "procedimiento": str,    # procedure name
    "entidad_cobrar": str,   # normalized entity code
    "vlr_copago": float,     # parsed copago value
}
```

### Normalized row keys

```python
{
    "tipo_error": "Copago vs Entidad",
    "factura": str,
    "responsable_cierra": str,
    "descripcion": "Vlr. Copago debe ser 0 cuando entidad no es default",
    "procedimiento": str,     # "Código - Nombre"
    "detalle": str,            # "Ent: {entidad}, Copago: {vlr_copago}"
    "fecha_cierre_vacia": bool,
}
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Detector logic | `openpyxl.Worksheet` builder (same as `test_odontologia_cantidades.py`): inject known values, assert errors |
| Unit | Normalization | Small dict arrays → assert normalized shape |
| Integration | `detect_all` wiring | Call through `detect_all_problems_urgencias`, assert errors appear in `resultado` |

### Test matrices

**Entidad values**: `"1"`, `"0001"`, `"86"`, `"ESS118"`, empty `""`, `None`
**Copago values**: `0`, `500`, `"0"`, `"500"`, `None`, `""`

Expected: errors only when entidad NOT in `{"1","0001"}` AND copago != 0.

## Migration / Rollout

No migration required. New detector activates on next detect-all call.

## Open Questions

None.
