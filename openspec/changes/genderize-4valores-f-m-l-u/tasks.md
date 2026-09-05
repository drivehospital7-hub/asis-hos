# Tasks: Genderize 4 valores (F/M/L/U)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~100-200 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Constants — Foundation

- [x] 1.1 Add `GENDER_FEMALE`, `GENDER_MALE`, `GENDER_LASTNAME`, `GENDER_UNDEFINED` constants to `app/constants/base.py`
- [x] 1.2 Add `GENDER_DISPLAY_MAP` (`{"F":"female","M":"male","L":"lastname","U":"undefined"}`) to `app/constants/base.py`
- [x] 1.3 Add `GENDER_CACHE_MAP` (reverse: `{"female":"F",...}`) to `app/constants/base.py`
- [x] 1.4 Add `GENDER_VALID_SHORT` / `GENDER_VALID_LONG` frozensets to `app/constants/base.py`

## Phase 2: Backend — Service Layer

- [x] 2.1 `genderize_service._load_cache()`: map `null` → `"undefined"` for each cached entry's gender field
- [x] 2.2 `genderize_service.predict_genders()`: store `"undefined"` instead of `null` when API returns `{"gender": null}`
- [x] 2.3 `genderize_service.override_gender()`: accept short codes (F/M/L/U) + long forms, normalize via `GENDER_DISPLAY_MAP`, reject invalid values with `ValueError`
- [x] 2.4 `genderize_verifier.verificar_y_comparar()`: replace M/F mapping with 4-value mapping (male→M, female→F, lastname→L, undefined→U); remove `if sexo_api_code == "?": continue` skip

## Phase 3: Backend — Route

- [x] 3.1 Update `POST /api/import/cache-corregir` validation in `import_facturas.py`: accept short codes F/M/L/U + long forms female/male/lastname/undefined, normalize via `_normalize_gender` in service, return 400 for invalid values

## Phase 4: Frontend

- [x] 4.1 In `frontend/src/pages/genderize/page.tsx`: replace single "Corregir → {sexo_excel}" button with a `<select>` dropdown (F/M/L/U options) + "Apply" button per row
- [x] 4.2 Pre-select dropdown based on `sexo_excel` value; on submit send chosen code to `cache-corregir`

## Phase 5: Tests

- [x] 5.1 Create `tests/services/test_genderize_service.py` with tests for `_load_cache` null→undefined, `override_gender` short/long/ invalid, `predict_genders` undefined-on-null
- [x] 5.2 Update `tests/services/test_genderize_verifier.py`: verify fixtures work with new 4-value mapping; add scenario for U/L discrepancies (mock cache with "undefined"/"lastname", assert Discrepancia.sexo_api is "U"/"L")
