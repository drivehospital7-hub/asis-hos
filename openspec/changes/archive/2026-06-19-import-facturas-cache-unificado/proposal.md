# Proposal: Import Facturas — Cache-Only Gender System

## Intent

Remove external API dependency (genderize.io) and expand gender system to 4 values (F/M/L/U) for `/import-facturas`. No more API costs, no rate-limit errors, no internet requirement during processing.

## Scope

### In Scope
- New `GENDER_*` constants in `app/constants/base.py` (F, M, L, U with display/cache maps, valid sets, normalization)
- Cache-only `genderize_service.py` (no HTTP imports, no API calls, BOM/zero-width cleaning, null→undefined mapping)
- 4-value `genderize_verifier.py` (`get_stats` returns `nombres_no_cache`, `verificar_y_comparar` maps all 4 values)
- 3 new extractor columns: Nº Identificación, Entidad Cobrar, Tipo Identificación
- Route updates: F/M/L/U acceptance, new fields in responses, remove `HTTPError` handler
- Delete `genderize_api.py` blueprint + `app/__init__.py` cleanup
- Frontend: dropdown selector (F/M/L/U), 3 new columns, export no-cache button, "Sexo API" → "Sexo JSON"
- Tests: `test_genderize_service.py` (18), `test_genderize_verifier.py` (14), delete `test_genderize.py`

### Out of Scope
- Unified processing pipeline (feature/procesamiento-unificado scope)
- Permissions/users module
- Catalog/dashboard restructuring
- Any file outside genderize/import-facturas boundary

## Capabilities

No existing genderize spec found in `openspec/specs/`. This introduces a new capability.

### New Capabilities
- `genderize-sistema-4valores`: Cache-only gender prediction with F/M/L/U values for import-facturas route, including frontend display, override, and no-cache export

### Modified Capabilities
None

## Approach

Selective file extraction from `feature/procesamiento-unificado` + manual adaptation to `main`. Apply in dependency order: constants → `genderize_service` → `genderize_verifier` → `genderize_extractor` → routes → `__init__.py` → frontend → tests. Delete `genderize_api.py`. Rebuild frontend bundles after TSX changes. Most delicate: `__init__.py` blueprint removal (no conflict on main), constants section isolated from `DASHBOARD_AREAS`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/base.py` | Modified | Add `GENDER_*` constants |
| `app/services/genderize_service.py` | Rewritten | Cache-only, no HTTP |
| `app/services/genderize_verifier.py` | Modified | 4-value mapping, no API |
| `app/services/genderize_extractor.py` | Modified | 3 new columns |
| `app/routes/import_facturas.py` | Modified | F/M/L/U, new fields |
| `app/routes/genderize_api.py` | Deleted | Full removal |
| `app/__init__.py` | Modified | Remove `genderize_bp` |
| `frontend/src/pages/genderize/page.tsx` | Modified | Dropdown, columns, export |
| `tests/services/test_genderize_service.py` | New | 18 tests |
| `tests/services/test_genderize_verifier.py` | New | 14 tests |
| `test_genderize.py` (root) | Deleted | Manual test script |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Frontend build mismatch | Medium | Rebuild after TSX changes |
| Cache null→undefined mapping | Low | BOM/zero-width handling in `_load_cache` |
| Missing `genderize_bp` removal | Low | pytest catches import error |
| Frontend/backend API contract | Low | Deploy together, test response shapes |

## Rollback Plan

`git revert <commit-hash>` for the merge commit, or `git reset --hard HEAD~1` if caught before push. Restore deleted files from `git checkout main -- <path>`.

## Dependencies

- Flask route structure on main must match expected import patterns
- No external API dependencies (cache-only)

## Success Criteria

- [ ] All pytest pass (existing + 32 new tests)
- [ ] `/import-facturas` serves cache-only gender resolution with no API calls
- [ ] Frontend shows F/M/L/U dropdown, 3 new columns, export no-cache button
- [ ] `genderize_api.py` removed — no blueprint registered
