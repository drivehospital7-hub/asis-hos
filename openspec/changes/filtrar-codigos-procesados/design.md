# Design: Filtrar Códigos Procesados

## Technical Approach

Two filtering layers in `procesar_cruce()` change: the individual no-facturados list switches from a negative filter (`not in CODIGOS_EXCEPCION`) to a positive one (`in PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS`), and the totalizado replaces per-code iteration with 4 aggregate rows computed via set-sum over the already-populated `conteo_reporte`, `conteo_ayudas_full`, and `conteo_ayudas` dicts. `CODIGOS_TOTALIZADO` is removed. `PROCESADOS_OTROS` is a new constant (`{"861801"}`) separate from `CODIGOS_MATCH_POR_DOCUMENTO` (which stays for matching logic only). All matching logic, Notas Enfermería processing, and helpers are untouched.

## Architecture Decisions

| Decision | Options | Tradeoff | Chosen |
|----------|---------|----------|--------|
| Filter strategy | (A) Negative: `not in CODIGOS_EXCEPCION`; (B) Positive: `in VISIBLE_CODES` | (A) includes any new code automatically; (B) explicit — only known processed codes appear | (B) — matches "only show processed codes" intent |
| Totalizado aggregation | (A) Per-code rows (current); (B) Category aggregate rows | (A) granular but noisy; (B) business-ready summaries | (B) — 4 rows replacing 9+, frontend handles summary rows via `es_notas` |
| OTROS visibility | (A) Always show; (B) Show only if any metric > 0 | (A) simpler but empty rows confuse; (B) matches conditional Traslados pattern | (B) — conditional on non-zero sum |
| OTROS grouping | (A) Reuse `CODIGOS_MATCH_POR_DOCUMENTO`; (B) New `PROCESADOS_OTROS` | (A) 890405 in both groups, needs dedup; (B) clean separation, matching logic unchanged | (B) — new constant `{"861801"}`, `CODIGOS_MATCH_POR_DOCUMENTO` stays for matching only |
| `total_excepciones_reporte` | (A) Compute inline during loop; (B) Compute via `sum()` before totalizado | (A) tied to loop structure; (B) independent | (B) — `sum(conteo_reporte.get(c,0) for c in CODIGOS_EXCEPCION)` |

## Data Flow

```
ayudas rows ──→ conteo_ayudas (no facturado) ──→ totalizado (PARTO/INTER/OTROS)
             ──→ conteo_ayudas_full (ordenadas) ─┘
reporte rows ──→ conteo_reporte ──→ total_excepciones_reporte ──→ TRASLADOS row
              ──→ pares_normal/pares_emssanar ──→ no_facturados filter
```

All four aggregate blocks consume only these three dicts. No new data sources.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/ordenado_facturado_service.py` | Modify | Filter (L672), totalizado (L557-573), remove `CODIGOS_TOTALIZADO` (L131-135) |
| `tests/services/test_ordenado_facturado_service.py` | Create | Unit tests for filtering + aggregation + edge cases |

## Code Changes

### Filter (L672)

```python
# Before
if cups and cups not in CODIGOS_EXCEPCION:

# After
VISIBLE_CODES = PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS
if cups and cups in VISIBLE_CODES:
```

### Totalizado (L557-573)

Replace per-code loop with:

```python
totalizado = []
total_excepciones_reporte = sum(
    conteo_reporte.get(c, 0) for c in CODIGOS_EXCEPCION
)

def _agregar_si_no_vacio(codigo, procedimiento, r, o, nf):
    if r > 0 or o > 0 or nf > 0:
        totalizado.append({"codigo": codigo, "procedimiento": procedimiento,
                           "total_reporte": r, "total_ordenadas": o,
                           "total_no_facturado": nf})

# PARTO
r = sum(conteo_reporte.get(c, 0) for c in PROCESADOS_PARTO)
o = sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_PARTO)
nf = sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_PARTO)
_agregar_si_no_vacio("PARTO", "Procesados Parto", r, o, nf)

# INTERCONSULTAS
r = sum(conteo_reporte.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
o = sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
nf = sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_INTERCONSULTAS)
_agregar_si_no_vacio("INTERCONSULTAS", "Procesados Interconsultas", r, o, nf)

# OTROS (PROCESADOS_OTROS)
r = sum(conteo_reporte.get(c, 0) for c in PROCESADOS_OTROS)
o = sum(conteo_ayudas_full.get(c, 0) for c in PROCESADOS_OTROS)
nf = sum(conteo_ayudas.get(c, 0) for c in PROCESADOS_OTROS)
_agregar_si_no_vacio("OTROS", "Procesados Otros", r, o, nf)
```

### Remove constant

Delete `CODIGOS_TOTALIZADO` (lines 131-135) entirely.

## Interfaces / Contracts

**No contract changes.** API response shape preserved:

```python
{
    "totalizado": [
        {"codigo": "PARTO"|"INTERCONSULTAS"|"OTROS"|"TRASLADOS",
         "procedimiento": str, "total_reporte": int,
         "total_ordenadas": int, "total_no_facturado": int,
         "es_notas": bool},  # TRASLADOS only
    ],
    "no_facturados": [...],  # same record shape
    ...
}
```

## Edge Cases

| Case | Behavior |
|------|----------|
| 861801 in PROCESADOS_OTROS | Visible in individual list + counted in OTROS aggregate |
| Empty ayudas | All aggregates = 0; no rows shown (conditional) |
| All codes facturados | Empty no_facturados; correct totals in totalizado |
| Only CODIGOS_EXCEPCION present | Only TRASLADOS row; no individual entries |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Filter produces correct subset | Mock `conteo_ayudas` with codes from each group; assert only PARTO/INTER/MATCH codes in individual list |
| Unit | Totalizado aggregation | Mock `conteo_reporte`, `conteo_ayudas_full`, `conteo_ayudas` with known values; assert PARTO/INTER/OTROS sums correct |
| Unit | 861801 visible in OTROS | Assert counted in OTROS aggregate and appears in individual list |
| Unit | Backward compat | Assert response shape unchanged (keys, types) |
| Unit | CODIGOS_TOTALIZADO gone | Assert module has no reference to `CODIGOS_TOTALIZADO` |
| Edge | Empty ayudas | Assert totalizado built correctly no crash |
| Edge | All facturado | Assert empty no_facturados, correct totals |

## Migration / Rollout

No migration. Single-commit scope. Rollback: `git checkout` the service file + delete test file.

## Open Questions

None.
