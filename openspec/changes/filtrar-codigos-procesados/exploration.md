## Exploration: filtrar-codigos-procesados

### Current State

The `ordenado_facturado_service.py` has three groups of exception codes defined as module-level constants:

1. **`CODIGOS_EXCEPCION`** (line 56, ~35 codes) — traslados, NOT shown as individual "no facturados". Instead handled separately via Notas Enfermería OCF066 matching.
2. **`PROCESADOS_PARTO`** (line 82, 20 codes) — recently added, currently treated as normal codes (appear in individual list and totalizado via `CODIGOS_TOTALIZADO`).
3. **`PROCESADOS_INTERCONSULTAS`** (line 106, 18 codes) — recently added, same as above.
4. **`CODIGOS_TOTALIZADO`** (line 131, 9 codes) — subset of Parto + Interconsulta codes that appear as individual rows in the totalizado.
5. **`CODIGOS_MATCH_POR_DOCUMENTO`** (line 128) — codes matched by patient ID instead of invoice number.

**Current filtering behavior:**

- **Individual "no_facturados" list** (lines 654-706): filters by `cups not in CODIGOS_EXCEPCION` — shows ALL codes EXCEPT the exception codes. **Parto and Interconsulta codes are included** as individual entries.
- **Totalizado** (lines 557-573): iterates all codes, skips exceptions (sums to `total_excepciones_reporte`), filters by `CODIGOS_TOTALIZADO` to show only ~9 specific codes as individual rows.
- **Traslados row** (lines 629-651): appended as a summary row using `total_excepciones_reporte` + Notas Enfermería OCF066 data.
- **Traslados individual entries** (lines 708-760): appended separately from Notas Enfermería for CODIGOS_EXCEPCION codes matched via OCF066.

**Key: The recently-added `PROCESADOS_PARTO` and `PROCESADOS_INTERCONSULTAS` codes are already defined but are NOT distinguished from normal codes in the filtering logic.** They currently appear individually in both the totalizado and the no_facturados list.

### Affected Areas

- `app/services/ordenado_facturado_service.py` — **only file that needs modification**. All constants and logic are local to this file.
- `app/constants/base.py` — NOT affected (no ordenado-related constants here).
- `app/routes/ordenado_facturado.py` — NOT affected (just delegates to service).
- Frontend (minified React in `static/react-dist/`) — NOT affected (backend API contract preserved).
- `tests/services/test_ordenado_facturado_service.py` — **needs to be created** (no existing tests for this service).

### Detailed Change Analysis

#### Change 1: Individual "no_facturados" filter (lines 654-706)

**Current (line 672):**
```python
if cups and cups not in CODIGOS_EXCEPCION:
```

**Should become:**
```python
CODIGOS_VISIBLES = PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS
if cups and cups in CODIGOS_VISIBLES:
```

This ensures only Parto and Interconsulta codes appear in the individual list. The inner matching logic (CAP, documento, normal) stays exactly as-is. Traslados section (lines 708-760) is unaffected since it handles CODIGOS_EXCEPCION separately.

**Context:** The `CODIGOS_MATCH_POR_DOCUMENTO` set (`{"890405", "861801"}`) is used for matching logic only (how to determine if a code is facturado), not for filtering. Code "890405" is in `PROCESADOS_INTERCONSULTAS` so it WILL be visible post-change. Code "861801" is NOT in any of the three groups, so it will be excluded — this is by-design.

#### Change 2: Totalizado section (lines 557-573)

**Current (lines 558-573):**
- Iterates all codes, skips CODIGOS_EXCEPCION, filters by CODIGOS_TOTALIZADO
- Appends individual code rows (one per code)
- Computes `total_excepciones_reporte` incrementally

**Should become:**
Replace the entire loop with aggregate rows per category:

```python
totalizado = []

# Parto summary
parto_reporte = sum(conteo_reporte.get(c, 0) for c in PROCESADOS_PARTO)
parto_ordenadas = sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_PARTO)
parto_no_facturado = sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_PARTO)
if parto_reporte > 0 or parto_ordenadas > 0 or parto_no_facturado > 0:
    totalizado.append({
        "codigo": "PARTO",
        "procedimiento": "Procesados Parto",
        "total_reporte": parto_reporte,
        "total_ordenadas": parto_ordenadas,
        "total_no_facturado": parto_no_facturado,
    })

# Interconsultas summary
inter_reporte = sum(conteo_reporte.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
inter_ordenadas = sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
inter_no_facturado = sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
if inter_reporte > 0 or inter_ordenadas > 0 or inter_no_facturado > 0:
    totalizado.append({
        "codigo": "INTERCONSULTAS",
        "procedimiento": "Procesados Interconsultas",
        "total_reporte": inter_reporte,
        "total_ordenadas": inter_ordenadas,
        "total_no_facturado": inter_no_facturado,
    })

# Exception count (still needed for Traslados row below)
total_excepciones_reporte = sum(conteo_reporte.get(c, 0) for c in CODIGOS_EXCEPCION)
```

**Important:** The `conteo_ayudas` and `conteo_ayudas_full` dictionaries (lines 505-553) are already computed for ALL codes regardless of category. They remain unchanged — we just aggregate differently.

**Frontend compatibility:** The `codigo`, `procedimiento`, `total_reporte`, `total_ordenadas`, `total_no_facturado` fields match what the frontend table renders. The `es_notas` flag (used by Traslados row for styling) is NOT needed for Parto/Interconsulta rows.

#### Change 3: Remove `CODIGOS_TOTALIZADO` (lines 131-135)

This constant becomes dead code after Change 2. It's only used on line 565 (the filter that gets removed). Either delete it or keep as comment for reference.

#### Change 4: New test file

Create `tests/services/test_ordenado_facturado_service.py` covering:
- Filtering: only Parto, Interconsulta, and Exception codes appear in no_facturados
- Totalizado: summary rows for Parto, Interconsultas, Traslados
- Edge cases: empty ayudas, no matching, all facturado, etc.
- Backward compatibility: existing API response shape preserved

### What Does NOT Change

| Code Section | Reason |
|---|---|
| `conteo_reporte` building (476-486) | Still needed for totals |
| `pares_normal` / `pares_emssanar` (489-500) | Still needed for matching |
| `conteo_ayudas` / `conteo_ayudas_full` (505-553) | Still needed for all totals |
| `excepcion_facturas_reporte` (577-586) | Still needed for Traslados |
| `ayudas_excepcion_facturas` (589-596) | Still needed for Traslados |
| Notas Enfermería processing (598-627) | Unchanged |
| Traslados row in totalizado (629-651) | Unchanged (uses `total_excepciones_reporte` computed separately) |
| Traslados individual entries (708-760) | Unchanged (handles CODIGOS_EXCEPCION separately) |
| All helper functions (_normalizar_, _leer_, _detectar) | Unchanged |
| Route (`ordenado_facturado.py`) | Unchanged |
| Frontend JS | Unchanged (API contract preserved) |

### Effort Estimate

- **Lines changed:** ~25 lines (filter logic + totalizado + CODIGOS_TOTALIZADO removal)
- **Files touched:** 1 service file + 1 new test file
- **Effort level:** Low — straightforward filtering change, no new concepts
- **Risk:** Low — all changes are within a single function (`procesar_cruce`), no external dependencies

### Risks

1. **"861801" disappears from results.** This code is in `CODIGOS_MATCH_POR_DOCUMENTO` but NOT in any of the three visible groups. Confirm with user this is intentional.
2. **Frontend expects individual code rows.** The totalizado currently lists individual codes (e.g., "735301", "890409"). After the change, only three aggregate rows ("PARTO", "INTERCONSULTAS", "TRASLADOS") appear. The frontend already handles `es_notas` for special rows — the new rows follow the same table structure.
3. **`total_excepciones_reporte` computation.** Currently calculated incrementally inside the loop. Must be computed separately after the loop is removed.
4. **No existing tests.** Need a comprehensive test file to validate the new filtering behavior.

### Ready for Proposal

Yes. The approach is clear, minimal, and well-understood. Proceed to sdd-propose directly.

### Key Questions Answered

1. **What changes in `procesar_cruce()` to filter individual list?** Change line 672 from `cups not in CODIGOS_EXCEPCION` to `cups in PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS`. Traslados section unchanged.

2. **What changes in totalizado?** Replace per-code iteration (lines 557-573) with 2 summary aggregations (Parto + Interconsultas), each summing `conteo_reporte`, `conteo_ayudas_full`, and `conteo_ayudas` for their respective code sets. Traslados row is unchanged.

3. **Does `CODIGOS_TOTALIZADO` need to change?** Yes — it becomes dead code and should be removed. The totalizado no longer filters by individual codes.

4. **Tests?** No existing tests. Need to create `tests/services/test_ordenado_facturado_service.py`.

5. **Scope?** 1 file modified (~25 lines changed), 1 new test file. Effort: Low. Risk: Low.
