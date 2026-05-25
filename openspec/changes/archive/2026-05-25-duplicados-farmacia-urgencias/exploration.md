## Exploration: duplicados-farmacia-urgencias

### Current State

The system currently has **no detection of row-level duplicates within the same invoice** for any tarifario. The existing `ruta_duplicada` detector in `transversales/` detects patients with multiple invoices in PyP — completely different scope (patient-level cross-invoice, not row-level within-invoice).

The area of Urgencias already has a constant `VALOR_TARIFARIO_FARMACIA = "Suminstros, Medicamentos"` in `app/constants/urgencias.py` (line 106), used by `centro_costo_urgencias.py` (Regla 9) to validate the center cost for pharmacy items.

The **column indices** `numero_factura`, `codigo`, `cantidad`, and `tarifario` are already mapped in `exporter.py` (lines 221-250) and available to all detectors through the `indices` dict.

### How the Detection Pipeline Works

1. `exporter.py` reads Excel headers → builds `indices` dict → calls `detect_all_problems_urgencias()`
2. `detect_all.py` imports individual detector functions, calls each, builds `resultado["problemas"]` dict with keys like `"centros_de_costos"`, `"ide_contrato"`, etc.
3. Each detector list is then normalized via `build_urgencias_normalized_rows()` into 6-column flat rows
4. The route (`urgencias.py`) groups normalized rows by `tipo_error` and generates `tipo_key` as `"norm_" + tipo.lower().replace(" ", "_")`
5. The HTML template renders each `tipo_key` with specific table layouts; unrecognized keys fall through to a unified 6-column table (lines 677-711)
6. The `enviarAControl()` JS function maps `tipo_key` to a Control Errores type (lines 126-138); unknown keys default to `'Otro'`

### Affected Areas

| File | Why Affected |
|------|-------------|
| `app/services/urgencias/duplicados_farmacia.py` | **New file**: detector module for this rule |
| `app/services/urgencias/detect_all.py` | Import and call the new detector, add to `resultado["problemas"]` and `resultado["totales"]` |
| `app/services/urgencias/normalized_rows.py` | Add a new section to normalize the new detector's output into 6-column format |
| `app/services/urgencias/__init__.py` | Export the new function (optional but consistent) |
| `app/templates/urgencias.html` | Add `duplicados_farmacia` to the `enviarAControl` mapping (line 138) |
| `tests/services/test_urgencias_detect_all.py` | Add tests for the new detector |
| (No changes needed) `app/constants/urgencias.py` | `VALOR_TARIFARIO_FARMACIA` already exists |
| (No changes needed) `app/constants/columnas.py` | Column headers are already defined |
| (No changes needed) `app/constants/colores.py` | No new color needed |
| (No changes needed) `app/routes/urgencias.py` | The route handles all error types generically via normalized rows |

### Approaches

1. **Approach A — New standalone detector module (RECOMMENDED)**
   - Create `app/services/urgencias/duplicados_farmacia.py` with function `detect_duplicados_farmacia(data_sheet, indices)`
   - Row-by-row iteration reading `tarifario`, `numero_factura`, `codigo`, `cantidad` from each row
   - Filter rows where `tarifario == VALOR_TARIFARIO_FARMACIA`
   - Build a dict keyed by `(factura, codigo, cantidad)` → list of row numbers
   - Any key with >1 entry = duplicate → return dicts with factura, codigo, cantidad, procedimiento, filas (which rows)
   - Integrate into `detect_all.py` using the same pattern as existing detectors
   - Pros: Clean SRP, follows existing pattern (one file per detector), easy to test
   - Cons: Minor boilerplate
   - Effort: **Low** (~1 hour implementation, ~30 min tests)

2. **Approach B — Add logic to an existing detector**
   - Add the duplicate check inside `centro_costo_urgencias.py` since it already reads `tarifario`
   - Would need to collect rows across the entire sheet first (two-pass), breaking the current single-pass pattern
   - Pros: Reuses existing row iteration
   - Cons: Violates SRP (centro_costo detector would now also detect duplicates), less testable
   - Effort: **Medium** (modification is easy, but architectural cleanliness suffers)

### Recommendation

**Approach A** — New standalone module.

The rationale:
1. SRP: centro_costo validates center costs; this new rule validates row uniqueness. Different concerns.
2. Testability: a standalone function is trivially unit-testable without triggering all centro_costo rules.
3. Pattern consistency: every other detector in urgencias is a separate file.
4. Risk: near-zero. The detector only reads columns already mapped; it doesn't modify state.

#### Detailed Design for Approach A

**Module**: `app/services/urgencias/duplicados_farmacia.py`

```python
# Signature matching existing pattern:
def detect_duplicados_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
```

**Algorithm**:
1. Check `tarifario_idx`, `num_fact_idx`, `codigo_idx`, `cantidad_idx` are all not None — return `[]` if any missing
2. Iterate rows 2..max_row, read values
3. Only process rows where `tarifario_str == VALOR_TARIFARIO_FARMACIA`
4. Build a dict: `seen[(factura, codigo, cantidad)]` = list of row numbers (or just track first occurrence and flag duplicates)
5. For each duplicate pair, append a problem dict with:
   - `factura`, `codigo`, `cantidad`, `procedimiento`
   - Optionally `regla = "DUPLICADO_FARMACIA"`
   - `filas_duplicadas` (the row numbers for reference)

**Return format** (per item for normalized_rows):
```python
{
    "factura": "FAC-001",
    "codigo": "12345",
    "cantidad": 2,
    "procedimiento": "MEDICAMENTO X",
}
```

**Normalization** (in `normalized_rows.py`):
```python
tipo_error: "Duplicados Farmacia"
descripcion: "Código duplicado en factura para tarifario Suminstros, Medicamentos"
procedimiento: "Código - Nombre"
detalle: "Cantidad: 2 (repetido 2 veces en factura)"
```

**tipo_key mapping** in `enviarAControl()`:
```javascript
'duplicados_farmacia': 'Duplicados farmacia'
```

**Integration in `detect_all.py`**:
- Import `detect_duplicados_farmacia` from the new module
- Call it alongside other detectors
- Add to `resultado["problemas"]["duplicados_farmacia"]`
- Add to `resultado["totales"]["duplicados_farmacia"]`
- Pass to `build_urgencias_normalized_rows(duplicados_farmacia=...)`

### How the type renders in the UI

Since this error type will be normalized into the 6-column format (tipo_error, factura, responsable_cierra, descripcion, procedimiento, detalle), the frontend template already handles it automatically via the `else` branch (lines 677-711) which renders a unified table. The only template change needed is adding `'duplicados_farmacia': 'Duplicados farmacia'` to the `enviarAControl` mapping (around line 138) so the "Send to Control Errores" feature works.

### Risks

- **Risk: Low column availability**. If `tarifario`, `codigo`, or `cantidad` columns are missing, the detector gracefully returns `[]` (empty results) with a log warning. No crash risk.
- **Risk: False positives on legitimate repeats**. Some procedures may legitimately have the same code+cantidad within a single invoice for different patients/family members. Needs business validation during proposal phase. **Mitigation**: name the tipo_key descriptively ("Revisión Farmacia Duplicado") and mark as review-needed rather than auto-error.
- **Risk: Performance on large sheets**. Single-pass iteration with dict lookup is O(n); negligible impact on existing runtime (sheets are typically <5000 rows).

### Ready for Proposal

Yes — the approach is clear, low-risk, and the change is well-scoped. The orchestrator should proceed with `sdd-propose`.
