# Tasks: Duplicados Farmacia en Urgencias (Updated)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~250 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Decision needed before apply | Yes |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Detector Rewrite — Group-Level Algorithm

- [x] 1.1 Rewrite `app/services/urgencias/duplicados_farmacia.py` — filter by `tarifario == VALOR_TARIFARIO_FARMACIA` AND `codigo_tipo_procedimiento in CODIGOS_TIPO_PROC_09_12`; group rows by `(factura, codigo_tipo_procedimiento)`; within each group count distinct `(codigo, cantidad)` pairs; flag group only if ALL pairs have count >= 2; output: `{factura, codigo_tipo_procedimiento, pares_duplicados: [{codigo, cantidad, count}], total_pares}`

## Phase 2: Update Normalized Rows

- [x] 2.1 Update `app/services/urgencias/normalized_rows.py` — adapt duplicados_farmacia section (lines 362–376) to iterate over `item["pares_duplicados"]` per group, building one normalized row per group with description `"Duplicados Farmacia — Grupo {09|12}"`

## Phase 3: Rewrite Tests

- [x] 3.1 Rewrite `tests/services/test_duplicados_farmacia.py` covering 8 spec scenarios + 3 bonus edge cases: grupo 09/12 con todos duplicados → flag; grupo con mezcla → `[]`; múltiples grupos (09 flag, 12 skip); sin filas farmacia → `[]`; tarifario farmacia con tipo_proc=02 → `[]`; columna tipo_proc faltante → `[]`; columna tarifario faltante → `[]`; cantidad None → 0; sin datos → `[]`; 3 pares distintos todos duplicados

## Phase 4: Verify Integration

- [x] 4.1 Run `pytest tests/services/test_duplicados_farmacia.py -v` — all 11 pass
- [x] 4.2 Verify `detect_all.py` imports still work (no signature change — same `(data_sheet, indices)` contract)
