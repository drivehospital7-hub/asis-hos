# Tasks: Import Facturas — Cache-Only Gender System

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380–450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: constants + service + verifier + extractor — PR 2: routes + blueprints + frontend + tests + cleanup |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend core: constants, service, verifier, extractor | PR 1 | Base branch: main. Autonomous — no frontend dep. Tests included. |
| 2 | Routes, blueprints, frontend, remaining tests | PR 2 | Depends on interfaces from PR 1. Deploy together with backend. |

## Phase 1: Foundation — Constants

- [x] 1.1 Add `GENDER_DISPLAY_MAP`, `GENDER_CACHE_MAP`, `GENDER_VALID_SHORT`, `GENDER_VALID_LONG` to `app/constants/base.py` after `ENTIDADES` section — 4 values F/M/L/U per spec req "4-Value Normalization"

## Phase 2: Service Layer — Core Logic

- [x] 2.1 Rewrite `app/services/genderize_service.py` — no HTTP imports, no API calls, `_load_cache` with BOM/null→"undefined" cleaning, `_normalize_gender()`, `predict_genders()` returns `list[GenderResult]` only (no tuple per design decision)
- [x] 2.2 Modify `app/services/genderize_verifier.py` — `get_stats` returns 3-tuple `(Stats, dict, nombres_no_cache)`, `verificar_y_comparar` maps 4 values + 3 new fields in `Discrepancia`
- [x] 2.3 Modify `app/services/genderize_extractor.py` — add 3 columns: Nº Identificación, Entidad Cobrar, Tipo Identificación + `ExtractResult` fields; missing cols → empty string (spec scenario "Column missing from Excel")

## Phase 3: Routes, Wiring & Cleanup

- [x] 3.1 Modify `app/routes/import_facturas.py` — accept F/M/L/U, add `nombres_no_cache` to stats response, 3 new fields in discrepancy rows, remove `HTTPError` import/handler
- [x] 3.2 Delete `app/routes/genderize_api.py` — full file removal
- [x] 3.3 Modify `app/__init__.py` — remove `genderize_bp` import (line 108) + registration (line 127) per design

## Phase 4: Frontend

- [x] 4.1 Update `frontend/src/pages/genderize/page.tsx` — dropdown with F/M/L/U options, "Sexo JSON" label, 3 new columns in table, export no-cache button
- [x] 4.2 Copy pre-built bundles from feature branch (blocked build due to pre-existing TS error in abiertas-urgencias/page.tsx)

## Phase 5: Tests

- [x] 5.1 Create `tests/services/test_genderize_service.py` — 22 tests (TDD cycle: RED→GREEN→triangulated)
- [x] 5.2 Create `tests/services/test_genderize_verifier.py` — 14 tests (TDD cycle: RED→GREEN→triangulated)
- [x] 5.3 Delete `test_genderize.py` — root manual test script (was a one-liner with broken import syntax)
