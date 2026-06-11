# Proposal: filtrar-codigos-procesados

## Intent

Currently `ordenado_facturado_service.py` shows ALL non-exception codes in the
individual "no_facturados" list and iterates a hardcoded subset
(`CODIGOS_TOTALIZADO`) in the totalizado. The user needs both views restricted
to only `PROCESADOS_PARTO`, `PROCESADOS_INTERCONSULTAS`, plus a cleaner
category-based totalizado with aggregate rows instead of per-code entries.

## Scope

### In Scope
- Filter individual "no_facturados" list to only `PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | CODIGOS_MATCH_POR_DOCUMENTO`
- Replace per-code totalizado loop with 3 aggregate rows: **PARTO**, **INTERCONSULTAS**, **TRASLADOS** (+ **OTROS** for `CODIGOS_MATCH_POR_DOCUMENTO` codes not in previous groups)
- Remove dead constant `CODIGOS_TOTALIZADO`
- Add `tests/services/test_ordenado_facturado_service.py`
- Deduplicate 890405 (present in both `PROCESADOS_INTERCONSULTAS` and `CODIGOS_MATCH_POR_DOCUMENTO` — count once in INTERCONSULTAS)

### Out of Scope
- Frontend changes (API response shape preserved)
- Route changes
- Matching logic (`conteo_ayudas` / `conteo_ayudas_full` computation)

## Capabilities

### New Capabilities
None — no new domain capabilities introduced.

### Modified Capabilities
- `ordenado-facturado`: Filtering rules for individual list and totalizado aggregation change.
  `CODIGOS_TOTALIZADO` is removed. Only codes from `PROCESADOS_PARTO`,
  `PROCESADOS_INTERCONSULTAS`, `CODIGOS_MATCH_POR_DOCUMENTO`, and
  `CODIGOS_EXCEPCION` (traslados) appear in results.

## Approach

1. **Individual filter** (line 672): Change `cups not in CODIGOS_EXCEPCION` to
   `cups in (PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | CODIGOS_MATCH_POR_DOCUMENTO)`.
2. **Totalizado** (lines 557–573): Replace loop with 4 aggregate sections:
   PARTO, INTERCONSULTAS, OTROS (CODIGOS_MATCH_POR_DOCUMENTO filtered to
   exclude 890405 since it's already in INTERCONSULTAS), TRASLADOS (unchanged).
3. **Remove** `CODIGOS_TOTALIZADO` (lines 131–135).
4. **Write** new test file covering filtering, totals, edge cases, and backward
   compatibility.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/ordenado_facturado_service.py` | Modified | ~25 lines: filter condition, totalizado logic, remove dead constant |
| `tests/services/test_ordenado_facturado_service.py` | New | Tests for filtering + aggregation + edge cases |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Code 861801 disappears from results | High | Already confirmed by user — it's excluded by design |
| Frontend expects per-code rows in totalizado | Low | Aggregate row shape matches existing `codigo/procedimiento/total_*` contract; `es_notas` pattern shows frontend handles summary rows |
| `total_excepciones_reporte` becomes stale | Low | Compute it separately from the sum of `CODIGOS_EXCEPCION` counts before building totalizado |

## Rollback Plan

Revert `ordenado_facturado_service.py` to HEAD and delete the test file. Single
commit scope — revert is one `git checkout` command.

## Dependencies

None. All changes local to one service file and one new test file.

## Success Criteria

- [ ] Individual list only shows codes from `PROCESADOS_PARTO`, `PROCESADOS_INTERCONSULTAS`, and `CODIGOS_MATCH_POR_DOCUMENTO`
- [ ] Totalizado shows PARTO, INTERCONSULTAS, OTROS, and TRASLADOS aggregate rows (not per-code entries)
- [ ] 890405 appears only in INTERCONSULTAS, not duplicated
- [ ] `CODIGOS_TOTALIZADO` constant removed
- [ ] All existing tests pass; new tests validate filtering + aggregation + edge cases
- [ ] API response preserves shape: `{codigo, procedimiento, total_reporte, total_ordenadas, total_no_facturado}`
