# Tasks: Copago vs Entidad — Urgencias

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~150-200 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Notes |
|------|------|-------|
| 1 | Single PR — full change | All phases, ~150-200 lines total |

## Phase 1: Infrastructure

- [x] 1.1 Add `"vlr_copago": "Vlr. Copago"` to `required_headers` in `app/services/exporter.py` (line ~249, before closing brace)
- [x] 1.2 Add `"Vlr. Copago"` to `URGENCIA_COLUMNS_TO_KEEP` in `app/constants/columnas.py`

## Phase 2: Detector (TDD)

- [x] 2.1 Create `app/services/urgencias/detect_copago_entidad.py`: function `detect_copago_entidad_urgencias(data_sheet, indices) → list[dict]`
  - Per-row: if `codigo_entidad_cobrar` ∉ `{"1","0001"}` and `vlr_copago ≠ 0` → error
  - Copago normalization: `try: float(val or 0)` — empty/None → 0
  - Missing `vlr_copago` column → log warning, return `[]`
  - Returns: `[{"factura","codigo","procedimiento","entidad_cobrar","vlr_copago"}]`
- [x] 2.2 Create `tests/services/test_urgencias_copago_entidad.py` with openpyxl Worksheet builder
  - Matrix: entidad `"1"` / `"0001"` / `"86"` / `None` × copago `0` / `500` / `None` / `"500"`
  - Assert only non-default entidad + non-zero copago trigger errors
  - Assert missing `vlr_copago` column returns `[]` (no crash)
  - Assert same factura with 2 rows produces 1 error (per-row)
  - Assert type normalization: string `"500"` → 500.0, string `"0"` → no error

## Phase 3: Integration

- [x] 3.1 In `app/services/urgencias/detect_all.py`:
  - Import `detect_copago_entidad_urgencias`
  - Call detector (section 5, after `revision_cantidad`)
  - Add `copago_entidad=copago_entidad` to `build_urgencias_normalized_rows()` call
  - Add `"copago_entidad": copago_entidad` to `resultado["problemas"]`
  - Add `"copago_entidad": len(copago_entidad)` to `resultado["totales"]`
- [x] 3.2 In `app/services/urgencias/normalized_rows.py`:
  - Add `copago_entidad: list[dict] | None = None` parameter
  - Add normalization block: `tipo_error="Copago vs Entidad"`, `descripcion="Vlr. Copago debe ser 0 cuando entidad no es default"`, `detalle="Ent: {entidad}, Copago: {vlr_copago}"`, `fecha_cierre_vacia`

## Phase 4: Verification

- [x] 4.1 Run `pytest -v tests/services/test_urgencias_copago_entidad.py` — all tests pass (16/16)
- [x] 4.2 Run `pytest -v` — no regressions in existing tests (391/391 pass)
