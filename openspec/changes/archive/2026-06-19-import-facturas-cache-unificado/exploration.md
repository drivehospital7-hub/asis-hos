## Exploration: import-facturas-cache-unificado

### Current State
On `main`, the `/import-facturas` route (genderize verification flow) works as follows:

1. **Backend service** (`genderize_service.py`): Uses a hybrid approach — local JSON cache (`genderize_cache.json`) **plus** HTTP calls to `api.genderize.io` for uncached names. `predict_genders()` batches uncached names (10 at a time) and queries the external API with retry/backoff for rate limits (429). Accepts only `male`/`female` values (or `M`/`F` short codes).

2. **Route** (`import_facturas.py`): 
   - `GET /import-facturas` — React shell (served via `react_shell.html`)
   - `POST /api/import/facturas-stats` — stats only (no tokens), returns `{total_excel, nombres_unicos, cache_hits, api_calls_necesarias}` without `nombres_no_cache`
   - `POST /api/import/cache-corregir` — accepts only `M`/`F` or `male`/`female` values
   - `POST /api/import/facturas-verify` — full verification with API calls, returns discrepancies. Has `except HTTPError` handler for 429 rate limits.

3. **Debug route** (`genderize_api.py`): Blueprint at `/api/genderize/` with a hardcoded test list of 10 names, directly calls `predict_genders()`.

4. **Frontend** (`genderize/page.tsx`): Shows "API calls = tokens" label, verify button shows `(N tokens)`, discrepancy correction button says "Corregir → M/F", no drop-down selector, export not available, table has only 5 columns (Nº Factura, Nombre Completo, Sexo Excel, Sexo API, Acción).

5. **Gender values**: Only 2 — `M` (male) and `F` (female). No `L` or `U`.

### Feature Branch Changes

The `feature/procesamiento-unificado` branch introduces TWO interrelated changes to this flow:

#### Change A: 4-Value Gender System (F/M/L/U)
- **New constants** in `app/constants/base.py`: `GENDER_DISPLAY_MAP` (F→female, M→male, L→lastname, U→undefined), `GENDER_CACHE_MAP` (reverse), `GENDER_VALID_SHORT`, `GENDER_VALID_LONG`
- **`_normalize_gender()`** function validates and normalizes both short codes and long forms
- **`override_gender()`** now accepts all 4 values
- **`verificar_y_comparar()`** maps: male→M, female→F, lastname→L, undefined→U, other→?

#### Change B: Remove API, Cache-Only Mode
- **`predict_genders()`** rewritten: no HTTP imports, no API calls. Cache hit → return cached value. Cache miss → skip silently (no result). "Hijo de"/"Hija de" classified locally.
- **`get_stats()`** now returns 3-tuple: `(Stats, facturas, nombres_no_cache)` where `nombres_no_cache` is `list[dict]` with `{"nombre", "sexo"}` (includes sexo from Excel)
- **`verificar_y_comparar()`** no longer calls API at all — only processes cache hits, silently skips uncached names
- **`genderize_api.py`** — file deleted entirely, blueprint removed from `app/__init__.py`
- **`_load_cache()`** — maps null gender → `"undefined"` in memory, cleans BOM/zero-width chars
- **No module-level cache file creation** — `CACHE_FILE.parent.mkdir()` and `CACHE_FILE.write_text("{}")` moved from module level to `_save_cache()`

#### Frontend Adaptation
- **New columns**: Nº Identificación, Entidad Cobrar, Tipo Identificación (with column widths via `<colgroup>`)
- **Dropdown selector**: Per-row `<select>` with F/M/L/U options instead of fixed "Corregir → M/F" button
- **Export**: New "Exportar no-cache" button downloads `nombre\tsexo` rows
- **UX**: "API calls = tokens" → "No procesados", verify button no longer shows `(N tokens)`, "Sexo API" → "Sexo JSON"
- **`Discrepancia` interface**: Added `numero_identificacion`, `entidad_cobrar`, `tipo_identificacion`

### Affected Areas

#### Backend (Python)
- `app/constants/base.py` — **New constants**: `GENDER_DISPLAY_MAP`, `GENDER_CACHE_MAP`, `GENDER_VALID_SHORT`, `GENDER_VALID_LONG`, `GENDER_FEMALE`, `GENDER_MALE`, `GENDER_LASTNAME`, `GENDER_UNDEFINED`
- `app/constants/__init__.py` — **New import**: `from app.constants.base import ...` (re-exports already happen via wildcard, so constants are accessible)
- `app/services/genderize_service.py` — **Major rewrite**: no HTTP, `predict_genders()` cache-only, `_normalize_gender()` for 4-value validation, `_load_cache()` null→undefined mapping
- `app/services/genderize_verifier.py` — **Modified**: `get_stats()` returns `list[dict]` 3rd element, `verificar_y_comparar()` no API, `Discrepancia` has 3 new fields, 4-value display mapping
- `app/services/genderize_extractor.py` — **Modified**: extracts 3 new columns (Nº Identificación, Entidad Cobrar, Tipo Identificación), `ExtractResult` has 3 new fields
- `app/routes/import_facturas.py` — **Modified**: `get_facturas_stats()` returns `nombres_no_cache`, `corregir_genero()` accepts F/M/L/U, `verify_facturas()` returns 3 new fields, removed `HTTPError` import + `except` block
- `app/routes/genderize_api.py` — **Deleted**: entire file + blueprint registration
- `app/__init__.py` — **Modified**: removed `genderize_bp` import and registration

#### Frontend (TypeScript/React)
- `frontend/src/pages/genderize/page.tsx` — **Modified**: new columns, dropdown selector, export, label changes, `GENDER_OPTIONS = ["F", "M", "L", "U"]`
- `app/static/react-dist/src/pages/genderize/index.html` — **Modified**: new JS bundle hash, new preload for `download-C8wq8Rqr.js`

#### Tests
- `tests/services/test_genderize_service.py` — **New file**: 18 tests for `_load_cache` null→undefined, `predict_genders` local-only, `override_gender` 4-value acceptance
- `tests/services/test_genderize_verifier.py` — **New file**: 14 tests for `get_stats` format and `verificar_y_comparar` 4-value mapping
- `test_genderize.py` (root) — **Deleted**: manual test script

### Approaches

1. **Surgical cherry-pick of commits** — Cherry-pick specific genderize-related commits from the feature branch
   - Pros: Clean git history, preserves authorship, minimal risk of picking unrelated changes
   - Cons: Feature branch has 60+ commits with interdependencies (perm refactor, unified processing). Several genderize commits also touch other areas. Conflicts with main's different `app/__init__.py`, `constants/base.py`, and `test_genderize_service.py` (which doesn't exist on main).
   - Effort: High — requires manual conflict resolution for each commit

2. **Selective file extraction** — Checkout specific files from feature branch, manually adapt to main
   - Pros: Maximum control, no unrelated changes leak in, can adapt to main's current structure
   - Cons: Manual work to ensure no missing dependencies, no merge commit history, frontend built artifacts need updating
   - Effort: Medium — ~7 Python files + 1 TSX file + tests + frontend rebuild

3. **Merge limited parts + revert unwanted** — Create a merge commit from the feature branch, then revert everything except the genderize/import-facturas changes
   - Pros: Full git history preserved
   - Cons: Very messy; feature branch has sweeping changes (permissions, catalog, unified processing, dashboard restructure) that would need reverting
   - Effort: Very High — tons of reverts

4. **Manual reimplementation** — Read the logic from the feature branch and re-code on main following the same patterns
   - Pros: Cleanest code, can improve on the original, no git history entanglement
   - Cons: More writing effort, risk of missing edge cases handled in the feature branch
   - Effort: Low-Medium — the changes are well-understood and documented in existing SDD artifacts

### Recommendation

**Approach 2 (Selective file extraction)**, with the following steps:

1. Apply the `GENDER_*` constants to `app/constants/base.py` (add after existing constants)
2. Rewrite `app/services/genderize_service.py` with the cache-only version
3. Rewrite `app/services/genderize_verifier.py` with the local-only + 4-value version
4. Update `app/services/genderize_extractor.py` with the 3 new columns
5. Update `app/routes/import_facturas.py` (remove HTTPError, add nuevos campos, F/M/L/U)
6. Delete `app/routes/genderize_api.py` and remove its blueprint from `app/__init__.py`
7. Update `frontend/src/pages/genderize/page.tsx`
8. Rebuild frontend (or copy built artifacts from feature branch)
9. Add/update test files

The most delicate parts are:
- `app/__init__.py` on main imports `genderize_bp` — simple removal, no conflict
- `app/constants/base.py` on main has a different `DASHBOARD_AREAS` structure — the `GENDER_*` constants go in their own section, no overlap
- The feature branch's `genderize_service.py` also adds `_load_cache()` BOM cleaning and null→undefined mapping that are important edge cases

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Breaking frontend API contract** | Low | High | Frontend expects `nombres_no_cache` as `{nombre, sexo}[]` — stats endpoint must return the new format. Backend and frontend must be deployed together. |
| **Cache file format change** | Low | Medium | Existing `genderize_cache.json` files with null genders will be mapped to "undefined" in memory. No physical rewrite until explicit override. This is backward-compatible. |
| **Missing `genderize_bp` deletion** | Low | Low | If we forget to remove the blueprint, Flask will fail to import. Easy to catch. |
| **Frontend build mismatch** | Medium | Medium | The built JS bundles reference specific filenames. If we don't rebuild, the old genderize page loads the old bundle. Need to rebuild after applying TSX changes OR copy the pre-built assets from the feature branch. |
| **Dependency on other feature branch changes** | Medium | Medium | The new `GENDER_*` constants don't depend on any other constants change. But if `app/__init__.py` structure differs significantly, we must be careful. Main's `app/__init__.py` still imports `genderize_bp` and `odontologia_equipos_basicos_bp` — safe to remove only `genderize_bp`. |
| **Merge conflict with concurrent work** | Low | Low | No known concurrent branches touching the same files. |

### Ready for Proposal
Yes — all changes are well-understood, the scope is clear, and the existing SDD artifacts (`genderize-4valores-f-m-l-u` and `genderize-local-sin-api` on the feature branch) provide complete spec, design, and verification documentation.
