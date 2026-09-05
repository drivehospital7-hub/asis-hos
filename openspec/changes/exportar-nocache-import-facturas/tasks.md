# Tasks: Botón "exportar no-cache" en /import-facturas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~50–80 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Backend — Extend `get_stats()` return value

- [x] 1.1 In `genderize_verifier.py`, build `nombres_no_cache` inside `get_stats()`: iterate `facturas.values()` preserve order, add compound_name (`f"{r.primer_nombre} {r.segundo_nombre}".strip()` or `r.primer_nombre`) for each `r.nombre_normalizado` not in `cache`
- [x] 1.2 Change `get_stats()` return type from `tuple[Stats, dict[str, ExtractResult]]` to `tuple[Stats, dict[str, ExtractResult], list[str]]` returning `nombres_no_cache` as third element

## Phase 2: Backend — Update route JSON response

- [x] 2.1 In `import_facturas.py`, change unpacking from `stats, _ = ...` to `stats, _, nombres_no_cache = ...`
- [x] 2.2 Add `"nombres_no_cache": nombres_no_cache` to the `data` dict in `/api/import/facturas-stats` response

## Phase 3: Frontend — Add export button + Blob download

- [x] 3.1 In `page.tsx`, add `nombres_no_cache: string[]` to the `StatsData` interface
- [x] 3.2 Add `exportNoCache` handler: build `\uFEFF` + `names.join(", ")`, create `Blob` with `type: "text/plain"`, trigger download via temporary `<a>` element, revoke ObjectURL
- [x] 3.3 Inside the stats preview `Card` (after the grid), conditionally render "Exportar no-cache" button if `statsPreview?.nombres_no_cache?.length > 0`, styled matching existing buttons

## Phase 4: Tests — Write backend tests

- [x] 4.1 Create `tests/services/test_genderize_verifier.py` with pytest test(s): mock cache with known subset, verify `nombres_no_cache` contains correct `compound_name` values for uncached names
- [x] 4.2 Assert return type: third element is `list[str]`, length matches `api_calls_necesarias`
