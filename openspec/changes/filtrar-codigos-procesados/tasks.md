# Tasks: Filtrar Códigos Procesados

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~180 (30 service + 150 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR to main |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Service refactor + tests | PR 1 | Single PR to main; all changes one commit slice |

## Phase 1: Service Refactor (`ordenado_facturado_service.py`)

- [x] 1.0 Add `PROCESADOS_OTROS` constant: `{"861801"}` (already existed)
- [x] 1.1 Remove `CODIGOS_TOTALIZADO` constant — dead code after aggregation change
- [x] 1.2 Replace totalizado loop (L557-573) with 4 aggregate blocks — PARTO (`PROCESADOS_PARTO`), INTERCONSULTAS (`PROCESADOS_INTERCONSULTAS`), OTROS (`PROCESADOS_OTROS`), TRASLADOS (existing, uses `total_excepciones_reporte` computed via `sum()`)
- [x] 1.3 Change individual filter: `cups not in CODIGOS_EXCEPCION` → `cups in (PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS)`

## Phase 2: Testing (`tests/services/test_ordenado_facturado_service.py`)

Apply MUST follow `tdd: true` (RED → GREEN → REFACTOR) per `openspec/config.yaml`.

- [x] 2.1 Write filter tests: Parto/Interconsulta/OTROS inclusion, non-matching exclusion, exception exclusion
- [x] 2.2 Write totalizado aggregation tests: 4 category rows (PARTO, INTERCONSULTAS, OTROS, TRASLADOS), empty category suppression
- [x] 2.3 Write 861801 inclusion test: visible in OTROS (individual + totalizado)
- [x] 2.4 Write backward-compat test: API response shape unchanged (`{codigo, procedimiento, total_reporte, total_ordenadas, total_no_facturado}`)
- [x] 2.5 Write edge case tests: empty ayudas, all facturado, only CODIGOS_EXCEPCION present
- [x] 2.6 Run `python -m pytest -v` and verify all tests pass and `CODIGOS_TOTALIZADO` has zero references

## Implementation Notes

| Risk | Detail |
|------|--------|
| `total_excepciones_reporte` | Currently set inside loop. Must compute via `sum(conteo_reporte.get(c,0) for c in CODIGOS_EXCEPCION)` before building totalizado since the loop is removed. |
| TRASLADOS unchanged | Existing block stays as-is, but relies on `total_excepciones_reporte` being computed independently. |
