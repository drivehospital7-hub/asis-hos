# Tasks: Revisión Cantidad Intramural

## Review Workload Forecast

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

| Field | Value |
|-------|-------|
| Estimated changed lines | ~230–265 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-always |
| Work units | 1 single PR |

---

## Phase 1: Foundation — Constants

- [x] 1.1 Add 6 new constants to `app/constants/intramural.py`:
      `CODIGO_TIPO_PROC_02`, `CODIGOS_TIPO_PROC_03_04` (frozenset),
      `LABORATORIO_NO`, `CANTIDAD_MAX_02_NO_LAB`, `CANTIDAD_MAX_03_04`,
      `CANTIDAD_MAX_GENERAL_INTRAMURAL`

## Phase 2: RED — Failing Tests

- [x] 2.1 Create `tests/services/intramural/test_revision_cantidad_intramural.py`
      with `_build_workbook` helper + tests for each rule:
      - R2: 02+Lab=No → Cantidad ≤ 2 (flag if > 2, not if ≤ 2)
      - R3: 03/04 → Cantidad ≤ 12 (flag if > 12, not if ≤ 12)
      - R4: General → Cantidad ≤ 1 (flag if > 1, not if ≤ 1)
      - R5: No tipo_factura filter — all rows evaluated unconditionally
      - R6: Flagged item has all 7 keys: `factura`, `codigo`, `procedimiento`,
        `cantidad`, `codigo_tipo_procedimiento`, `laboratorio`, `detalle`
      - R7: Missing `Cantidad` column → empty list; missing `Laboratorio` → falls
        through to general rule; missing `Código Tipo Procedimiento` → general rule
      - Cascade: 02+Lab=No matches before 03/04; 03/04 matches before general

## Phase 3: GREEN — Implement Detector

- [x] 3.1 Create `app/services/intramural/revision_cantidad_intramural.py`
      with `detect_revision_cantidad_intramural(data_sheet, indices) -> list[dict]`
      following the Urgencias cascade pattern but without tipo_factura filter,
      without exento tables, using new Intramural constants
- [x] 3.2 Verify all Phase 2 tests pass: `python -m pytest tests/services/intramural/test_revision_cantidad_intramural.py -v`

## Phase 4: GREEN — Wire into Orquestador

- [x] 4.1 Add import + call to `app/services/intramural/detect_all.py`:
      import, invoke detector, register in `error_groups["⚠️ Revisión Necesaria"]`,
      add key to `resultado["problemas"]` and `resultado["totales"]`
- [x] 4.2 Add integration test in `tests/services/test_intramural_detect_all.py`:
      verify `"⚠️ Revisión Necesaria"` present in `error_groups` and
      `resultado["totales"]["revision_cantidad"]` matches flagged count
- [x] 4.3 Run full test suite: `python -m pytest tests/services/intramural/ tests/services/test_intramural_detect_all.py -v`

## Phase 5: REFACTOR — Cleanup

- [x] 5.1 Review code: no print() or debug logs, logging follows `[BACK]` convention,
      detector under 100 lines, functions under 50 lines
- [x] 5.2 Final run: `python -m pytest tests/ -v` — all intramural tests green (47 pre-existing failures outside scope)
