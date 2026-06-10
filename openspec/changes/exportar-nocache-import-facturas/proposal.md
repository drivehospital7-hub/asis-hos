# Proposal: Botón "exportar no-cache" en /import-facturas

## Intent

After token estimation in /import-facturas, users see cache hit/miss counts but cannot extract **which** names are uncached. Add a button that exports a `.txt` with uncached `compound_name` values (comma-separated, single line) so they can be processed outside the system.

## Scope

### In Scope
- Extend `genderize_verifier.py::get_stats()` to return uncached `compound_name` list
- Update `POST /api/import/facturas-stats` to include `nombres_no_cache`
- Add "Exportar no-cache" button in GenderizePage (React) — Blob download as `.txt`
- Tests for the backend change (TDD mode active)

### Out of Scope
- Modifying the cache system (read/write/key format)
- Changing existing exports (`exporter.py`, `cruce_sheet.py`)
- Upload/re-import of the `.txt`
- Existing frontend behavior

## Capabilities

### New Capabilities
- `exportar-nocache`: Export uncached patient names from genderize cache verification as comma-separated `.txt`; single-button flow from stats view.

### Modified Capabilities
- None

## Approach

1. `get_stats()` already iterates names to classify cache hits — expose `nombres_no_cache: list[str]` using `compound_name` format
2. Route adds the list to JSON response under `nombres_no_cache`
3. Frontend: after "Ver estimación" succeeds, if `nombres_no_cache.length > 0`, show "Exportar no-cache" button; onClick → `Blob(text, {type: 'text/plain'})` → download link

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/genderize_verifier.py` | Modified | Return uncached names from `get_stats()` |
| `app/routes/import_facturas.py` | Modified | Include `nombres_no_cache` in stats endpoint |
| `frontend/src/pages/genderize/page.tsx` | Modified | Add Exportar no-cache button + Blob download |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| TDD strict mode: uncovered edge cases in new field | Low | Existing `get_stats()` is tested; add unit test for returned list |
| `.txt` encoding on Windows | Low | Use UTF-8 BOM in Blob for Excel/Notepad compatibility |

## Rollback Plan

Revert the 3 files. No data migration — API field addition and UI only. Server-side rollback first makes the field invisible to older frontend.

## Dependencies

None.

## Success Criteria

- [ ] `get_stats()` returns `nombres_no_cache` with correct `compound_name` values
- [ ] `/api/import/facturas-stats` includes `nombres_no_cache` in response
- [ ] Button visible only when uncached names exist
- [ ] Downloaded `.txt` is comma-separated, single line, no trailing comma
- [ ] All existing tests pass (`pytest -v`)
