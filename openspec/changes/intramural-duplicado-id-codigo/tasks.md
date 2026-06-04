# Tasks: Intramural — Duplicado ID+Código

> Implementation tasks for detecting duplicate rows where same `Nº Identificación` + same `Código` appear more than once in Intramural billing.

---

## Dependency Graph

```
Task 1 (Create detector)
    ├── Task 2 (Register in orquestador)
    ├── Task 3 (Handler in normalized_rows)
    └── Task 4 (Write tests)
```

Tasks 2 and 3 are independent of each other but both depend on Task 1 for the module to exist and the error group key to be known. Task 4 depends on Task 1.

---

## Task 1: Create detector `duplicado_id_codigo.py` ✅

| Field | Value |
|-------|-------|
| **Files involved** | `app/services/intramural/duplicado_id_codigo.py` (CREATE) |
| **Dependencies** | None |
| **Estimated effort** | Small |

### Description

Create a new detector function `detect_duplicado_id_codigo()` that:
1. Accepts `(data_sheet: Worksheet, indices: dict[str, int | None]) -> list[dict]`
2. Validates that `indices["numero_factura"]`, `indices["identificacion"]`, and `indices["codigo"]` are not `None` — if any is missing, return `[]` with a `logger.warning`
3. Iterates rows 2..max_row, normalizing `numero_factura` via `normalize_invoice()`, skipping rows with empty factura, empty identificación, or empty código
4. Groups rows by `(identificacion_str.strip(), codigo_str.strip())` using a `defaultdict[list]` — both values cast to `str` before comparison to handle mixed types (e.g. `123` vs `"123"`)
5. For each group with `len > 1`, produces **one error dict per row** with keys:
   - `"factura"`: str — invoice number
   - `"identificacion"`: str — patient ID (stripped)
   - `"codigo"`: str — procedure code (stripped)
   - `"procedimiento"`: str — procedure name (read from `procedimiento` column, fallback `""` if column missing)
   - `"cantidad_repeticiones"`: int — total size of the duplicate group
6. Logs at `logger.info` the count of duplicate rows and groups found (only when > 0)
7. Returns `[]` if all groups have size ≤ 1

### Acceptance Criteria

- [x] Function signature matches `(data_sheet: Worksheet, indices: dict[str, int | None]) -> list[dict]`
- [x] Missing `numero_factura` → returns `[]` with warning
- [x] Missing `identificacion` → returns `[]` with warning
- [x] Missing `codigo` → returns `[]` with warning
- [x] Missing `procedimiento` → uses `""` as procedure name (non-blocking)
- [x] Two rows with same ID+código → returns 2 errors with `cantidad_repeticiones=2`
- [x] Three rows with same ID+código → returns 3 errors with `cantidad_repeticiones=3`
- [x] Rows with `None` identificación or `None` código → skipped
- [x] Mixed types (`123` string vs `123` int) → treated as equal
- [x] Whitespace variations (e.g. `" 123 "` vs `"123"`) → treated as equal
- [x] No duplicate groups → returns `[]`
- [x] Uses `normalize_invoice()` from `app.services.transversales.normalize`
- [x] Uses `logger` from `logging.getLogger(__name__)` with `[BACK]` prefix per logging conventions

### Implementation Notes

- Base the implementation on the reference code in `openspec/changes/intramural-duplicado-id-codigo/design.md` (lines 78–176)
- Follow the detector pattern from `.agent/skills/asis-hos-detector-pattern/SKILL.md`
- Column name mapping: `identificacion` → `"Nº Identificación"`, `codigo` → `"Cód. Equivalente CUPS"` (existing mapping — see design decision on column name)
- Import `normalize_invoice` from `app.services.transversales.normalize`

---

## Task 2: Register detector in orquestador ✅

| Field | Value |
|-------|-------|
| **Files involved** | `app/services/intramural/detect_all.py` (MODIFY) |
| **Dependencies** | Task 1 |
| **Estimated effort** | Small |

### Description

Register the new detector in the Intramural orquestador by making three changes to `app/services/intramural/detect_all.py`:

**A — `_get_intramural_detectors()`:**
- Add import for `detect_duplicado_id_codigo` from `app.services.intramural.duplicado_id_codigo`
- Append `detect_duplicado_id_codigo` to the returned list

**B — `detect_all_problems_intramural()` — direct call (step 8):**
- After the existing step 7 (IDE Contrato, around line 171), import and call the detector:
  ```python
  duplicado_id_codigo = detect_duplicado_id_codigo(data_sheet, indices)
  ```
- Add a `logger.info` line logging the count of problems found

**C — Build result structures:**
- Add `"Duplicado ID+Código": duplicado_id_codigo` to `error_groups` dict (around line 174)
- Add `"duplicado_id_codigo": duplicado_id_codigo` to `resultado["problemas"]` dict
- Add `"duplicado_id_codigo": len(duplicado_id_codigo)` to `resultado["totales"]` dict

### Acceptance Criteria

- [x] `_get_intramural_detectors()` returns the new detector in its list
- [x] `detect_all_problems_intramural()` calls `detect_duplicado_id_codigo()` and stores result
- [x] `error_groups` contains key `"Duplicado ID+Código"` with detector results
- [x] `resultado["problemas"]["duplicado_id_codigo"]` contains the detector results
- [x] `resultado["totales"]["duplicado_id_codigo"]` is `len(result)`
- [x] Orquestador continues to work if the detector returns `[]` (no crash)
- [x] Logging uses `[BACK]` prefix and follows asis-hos-logging conventions

---

## Task 3: Add handler in `build_normalized_rows()` ✅

| Field | Value |
|-------|-------|
| **Files involved** | `app/services/normalized_rows.py` (MODIFY) |
| **Dependencies** | Task 1 (for error group key and dict structure) |
| **Estimated effort** | Small |

### Description

Add a new handler block at the end of `build_normalized_rows()`, after the "Cups No CAPITA" block (after line 365), inside the function before the `return rows` statement:

```python
# --- Duplicado ID+Código ---
for item in error_groups.get("Duplicado ID+Código", []):
    factura = item.get("factura", "")
    identificacion = item.get("identificacion", "")
    codigo = item.get("codigo", "")
    proc = item.get("procedimiento", "")
    repeticiones = item.get("cantidad_repeticiones", 0)
    rows.append({
        "tipo_error": "Duplicado ID+Código",
        "factura": factura,
        "fec_factura": _get_fec_factura(factura),
        "responsable_cierra": _get_responsable(factura),
        "descripcion": (
            f"Identificación+Código duplicado "
            f"({repeticiones} veces)"
        ),
        "procedimiento": _build_procedimiento(codigo, proc),
        "detalle": f"ID: {identificacion} | Cód: {codigo}",
        "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
    })
```

### Acceptance Criteria

- [x] Handler reads from `error_groups.get("Duplicado ID+Código", [])` — no crash if key missing
- [x] Each item produces a row with correct `tipo_error = "Duplicado ID+Código"`
- [x] `descripcion` includes repetition count (e.g. "Identificación+Código duplicado (2 veces)")
- [x] `detalle` shows `ID: {id} | Cód: {codigo}`
- [x] `procedimiento` uses `_build_procedimiento(codigo, proc)` — consistent with other handlers
- [x] `fec_factura`, `responsable_cierra`, `fecha_cierre_vacia` are populated from mapping dicts
- [x] Blank line convention matches existing handler blocks (comment `# --- Duplicado ID+Código ---` before code)

---

## Task 4: Write unit and integration tests ✅

| Field | Value |
|-------|-------|
| **Files involved** | `tests/services/intramural/test_duplicado_id_codigo.py` (CREATE) |
| **Dependencies** | Task 1 |
| **Estimated effort** | Small |

### Description

Create test file with comprehensive coverage for the new detector. Use `pytest` and `openpyxl` to build test Excel sheets in memory.

**Unit tests (detector):**
1. `test_two_rows_same_id_codigo_returns_two_errors` — Build sheet with 2 rows sharing same ID+código → assert 2 errors with `cantidad_repeticiones=2`
2. `test_unique_pairs_returns_empty` — All `(id, codigo)` pairs unique → assert `[]`
3. `test_missing_identificacion_column_returns_empty` — Remove `Nº Identificación` from indices → assert `[]` with no crash
4. `test_missing_codigo_column_returns_empty` — Remove `codigo` from indices → assert `[]`
5. `test_missing_numero_factura_column_returns_empty` — Remove `numero_factura` from indices → assert `[]`
6. `test_none_values_skipped` — Rows with `None` identificación or `None` código → skipped, not errored
7. `test_three_rows_same_pair_returns_three_errors` — 3 rows same ID+código → assert 3 errors with `cantidad_repeticiones=3`
8. `test_mixed_types_123_vs_string` — `identificacion=123` and `identificacion="123"` → treated as duplicate
9. `test_whitespace_variations` — `" 123"` and `"123 "` → treated as equal
10. `test_missing_procedimiento_column_uses_empty_string` — Remove `procedimiento` from indices → assert results have `procedimiento=""`

**Integration tests (orquestador):**
11. `test_detector_integration_with_detect_all` — Call `_get_intramural_detectors()` and verify `detect_duplicado_id_codigo` is in the list
12. `test_error_groups_integration` — Build full `error_groups` dict with mock data and call `build_normalized_rows()`, verify output rows exist

### Acceptance Criteria

- [x] All unit tests pass
- [x] At least 10 test functions covering the scenarios above
- [x] Tests use in-memory openpyxl `Workbook()` — no fixture files needed
- [x] `indices` dict built programmatically matching the pattern in existing detectors
- [x] Integration test verifies `_get_intramural_detectors()` includes the new detector
- [x] Integration test verifies `build_normalized_rows()` handles `"Duplicado ID+Código"` key
- [x] Edge case tests cover: None values, missing columns, mixed types, whitespace, 3+ duplicates
- [x] No test writes to disk (no side effects)

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| **New files** | 2 (`duplicado_id_codigo.py`, `test_duplicado_id_codigo.py`) |
| **Modified files** | 2 (`detect_all.py`, `normalized_rows.py`) |
| **Total lines (new + modified)** | ~250 |
| **Risk assessment** | **Low** |
| **400-line budget at risk?** | No — well under budget (~250 lines) |
| **Chained PRs recommended?** | No — single PR is well within review limits |

### Detailed Estimate

| Task | New lines | Modified lines | Complexity |
|------|-----------|----------------|------------|
| 1 — Create detector | ~70 | 0 | Low |
| 2 — Register in orquestador | 0 | ~20 | Low |
| 3 — Handler in normalized_rows | 0 | ~20 | Low |
| 4 — Tests | ~140 | 0 | Low |
| **Total** | **~210** | **~40** | **Low** |

### Risk Factors

| Risk | Impact | Mitigation |
|------|--------|------------|
| Column name mismatch (`"Código"` vs `"Cód. Equivalente CUPS"`) | Medium — detector would always return `[]` | Verify Excel column name during implementation; adjust `required_headers` mapping if needed |
| Existing tests broken by changes to `detect_all.py` / `normalized_rows.py` | Low — only additive changes, no refactoring | Run full test suite after implementation |
| New detector slows down processing on large files | Low — single pass O(n) with dict grouping | N/A for current data volume |

### Recommendation

Single PR is appropriate. CI run to confirm existing tests are not broken, plus new tests for the detector. Review workload is ~250 lines across 4 files — comfortable for one reviewer session.
