# Tasks: Export no-cache con genero del Excel y eliminar dependencia de API Genderize

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~100-200 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Backend — get_stats() export format with sexo

- [x] 1.1 `genderize_verifier.py` — Change `get_stats()` return 3rd element from `list[str]` to `list[dict]`: each entry `{"nombre": str, "sexo": str}` using `r.sexo` from ExtractResult. Deduplicate by `nombre_normalizado` (not by compound_name).
- [x] 1.2 `routes/import_facturas.py` — No route change needed: `nombres_no_cache` is already serialized via `jsonify`. Verify the response shape matches `array[{nombre, sexo}]` in `/api/import/facturas-stats`.

## Phase 2: Backend — Remove API dependency from predict_genders()

- [x] 2.1 `genderize_service.py` — Remove imports: `time`, `os` (check if still needed for GENDERIZE_CACHE_FILE), `urlopen`, `Request`, `urlencode`, `HTTPError`. Remove `RateLimitInfo` dataclass. Remove constants `GENDERIZE_API_URL`, `GENDERIZE_API_KEY`, `GENDERIZE_COUNTRY_ID`.
- [x] 2.2 `genderize_service.py` — Rewrite `predict_genders()`: cache hit → append `GenderResult`; cache miss → skip silently (no API call, no auto-U, no cache mutation). Remove entire `if api_names:` block (~75 lines). Return signature simplifies to `list[GenderResult]` (no `RateLimitInfo`).
- [x] 2.3 `genderize_verifier.py` — Rewrite `verificar_y_comparar()`: remove batching loop (`for i in range(0, len(nuevos), 10)`). Results come only from cache hits. Remove `predict_genders` call. Nombres sin cache simply don't appear in `all_results` → no discrepancy generated.
- [x] 2.4 `routes/import_facturas.py` — Remove `from urllib.error import HTTPError` import. Remove `except HTTPError` block (lines 289-299) in `/api/import/facturas-verify`.

## Phase 3: Cleanup

- [x] 3.1 Delete `app/routes/genderize_api.py` (entire file, ~56 lines).
- [x] 3.2 `app/__init__.py` — Remove line 106 `from app.routes.genderize_api import genderize_bp` and line 127 `app.register_blueprint(genderize_bp, url_prefix="/api/genderize")`.
- [x] 3.3 Delete `test_genderize.py` (root-level manual script, 4 lines).
- [x] 3.4 `genderize_service.py` — Remove unused `os` import if `GENDERIZE_API_KEY` was the only user; keep if `CACHE_FILE` still needs it (it does — remove `os` import for API_KEY, keep for CACHE_FILE path resolution).

## Phase 4: Frontend

- [x] 4.1 `frontend/src/pages/genderize/page.tsx` — Change `StatsData.nombres_no_cache` type from `string[]` to `{nombre: string; sexo: string}[]`.
- [x] 4.2 `page.tsx` — Rewrite `exportNoCache()` to produce `"\uFEFF" + items.map(i => `${i.nombre}\t${i.sexo}`).join(", ")`.
- [x] 4.3 `page.tsx` — Remove token count label from verify button: change from `` `Verificar (${statsPreview.api_calls_necesarias} tokens)` `` to `"Verificar"`.

## Phase 5: Tests

- [x] 5.1 `tests/services/test_genderize_service.py` — Remove entire class `TestPredictGendersUndefinedOnNull` (3 test methods that mock `urlopen`). Add class `TestPredictGendersLocalOnly` with: cache-hit test (mock cache → assert `GenderResult`), cache-miss test (mock empty cache → assert empty results), Hijo/Hija test (assert classified via `_classify()` locally).
- [x] 5.2 `tests/services/test_genderize_verifier.py` — Update `TestGetStatsNombresNoCache`: assertions for `list[dict]` format (each entry has `nombre` + `sexo` keys). Update `api_calls_necesarias` assertions to expect 0. Update `TestVerificarYComparar4Valores`: expect stats with zero `api_calls_necesarias`; verify no API path invoked.
