# Tasks: /procesar UI Consistency — Handler Standardization

## Review Workload Forecast

Estimated changed lines: ~450-550. 400-line budget risk: **High**. Chained PRs recommended: **Yes**.

Decision needed before apply: **Yes**
Chained PRs recommended: **Yes**
Chain strategy: **pending**
400-line budget risk: **High**

| Unit | Scope | PR | Lines |
|------|-------|----|-------|
| 1 | Odontología handlers + tests | PR 1 (base=main) | ~210 |
| 2 | Shared/Urgencias handlers + tests | PR 2 (base=main) | ~260 |

## Phase 1: Odontología — `app/services/odontologia/normalized_rows.py`

- [x] 1.1 Decimales — desc=`problema`; proc=`_build_procedimiento`; det=`vlr_sub/vlr_proc`
- [x] 1.2 Doble Tipo — desc=`problema`; proc=`_build_procedimiento`; det=`tipo_procedimiento`
- [x] 1.3 Ruta Duplicada (P0) — guard `facturas`/`cantidad` with `.get()`; fallback `identificacion`
- [x] 1.4 Profesionales — desc=`problema` or `regla`; proc=`_build_procedimiento(codigo, procedimiento)`
- [x] 1.5 Cantidades — desc=`problema` or template; proc=`_build_procedimiento`
- [x] 1.6 Tipo ID / Edad — desc=`problema` or inference; proc=`num_id`; det=age string
- [x] 1.7 Tipo ID / Entidad — desc from `problema`; proc=`cod_actual`; det=detail
- [x] 1.8 Centro Costo — desc=`problema` or template; proc=`_build_procedimiento`; det=`centro_costo`
- [x] 1.9 IDE Contrato — desc=`problema` or template; proc=`_build_procedimiento(codigo,"")`; det=`ide_contrato`
- [x] 1.10 Código Entidad vs Af. — already correct; verify `problema` usage
- [x] 1.11 Tipo Usuario — desc=`problema` or hardcoded; proc=`_build_procedimiento`; det=`tipo_usuario`
- [x] 1.12 Cups Sin Contrato — already correct; verify `_build_procedimiento`
- [x] 1.13 Generic fallback — after all loops: if proc+det empty, first non-`factura` key:value → detalle

## Phase 2: Shared/Urgencias — `app/services/normalized_rows.py`

- [x] 2.1 Centros Costo — desc=`problema`; proc=`_build_procedimiento`; det=`centro_costo`
- [x] 2.2 IDE Contrato — desc=`problema` or generated; proc=`_build_procedimiento`; det=`ide_contrato`
- [x] 2.3 Cups Equivalentes — desc=`problema` or `accion`; proc=`_build_procedimiento`; det=`codigo_equiv`
- [x] 2.4 MAL CAPITADO — desc=`problema` or `observacion`; det=`ide_contrato`
- [x] 2.5 Cantidades (P0) — catch `KeyError` on `cantidad_esperada`; desc=`problema` or template
- [x] 2.6 Decimales (list) — keep as-is; replace hardcoded headers with actual values from engine
- [x] 2.7 Tipo ID / Edad — desc=`problema` or generated; fallback missing `tipo_deberia`
- [x] 2.8 Profesionales — already correct; verify
- [x] 2.9 Código Entidad vs Af. — already correct; verify
- [x] 2.10 Tipo Usuario — desc=`problema` or hardcoded; proc=`_build_procedimiento`
- [x] 2.11 ⚠️ Revisión Necesaria — already correct; verify
- [x] 2.12 Copago vs Entidad — already correct; verify
- [x] 2.13 Duplicados Farmacia (P0) — guard `pares_duplicados`/`total_pares` with `.get()`
- [x] 2.14 Cups Sin Contrato — already correct; verify
- [x] 2.15 Cups No CAPITA — desc=`problema` or `observacion`; proc=`_build_procedimiento`
- [x] 2.16 Duplicado ID+Código — desc=`problema` or template; guard `cantidad_repeticiones`
- [x] 2.17 Generic fallback — same as 1.13, after all `build_normalized_rows` loops

## Phase 3: Testing

- [x] 3.1 Per Phase-1 handler test (engine+legacy+empty keys) in `test_odontologia_normalized_rows.py`
- [x] 3.2 Per Phase-2 handler test (same scenarios) in `test_normalized_rows_shared.py`
- [x] 3.3 Generic fallback test — sparse dict with only `factura`+`problema`
- [x] 3.4 P0 regression tests — ruta_duplicada, cantidades_urgencias, duplicados_farmacia edge cases
- [x] 3.5 `python -m pytest -v` — verify zero regressions (existing 19 pre-existing + 52 new = 71 tested)
