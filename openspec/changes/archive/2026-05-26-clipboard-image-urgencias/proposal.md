# Proposal: Clipboard Image Paste Fix (Control de Novedades)

## Intent

Fix three clipboard paste bugs in Control de Novedades: duplicate image uploads, picking oldest instead of most recent image, and missing `preventDefault`. Frontend-only JS changes to one template — no backend changes.

## Scope

### In Scope
- Fix double image add when pasting in `cargaTextarea` (both handlers fire → same image uploaded twice)
- Fix image selection to pick most recent (last) clipboard image, not oldest (first)
- Add `e.preventDefault()` to suppress browser default paste text insertion
- Manual testing across Chrome, Edge, Firefox on Windows

### Out of Scope
- Backend changes (routes, storage)
- Refactoring handlers into unified architecture
- Backend image deduplication
- React version (`frontend/src/pages/control-novedades/`)

## Capabilities

### New Capabilities
None — pure bugfix, no new capability introduced.

### Modified Capabilities
None — no spec-level behavior changes.

## Approach

Three localized JS edits in `app/templates/control_errores.html`:

1. **Prevent double add** — Add `e.stopPropagation()` in textarea handler (~line 1808) so event doesn't bubble to global handler
2. **Pick last image** — Iterate clipboard items in reverse in both handlers to pick most recent instead of `break` on first match
3. **Suppress default paste** — Add `e.preventDefault()` in global handler's carga path and textarea handler

## Affected Areas

| Area | Impact | Change |
|------|--------|--------|
| `control_errores.html` ~line 1550 | Modified | Fix item order, add preventDefault |
| `control_errores.html` ~line 1808 | Modified | Add stopPropagation, fix item order, add preventDefault |

## Risks

| Risk | Like. | Mitigation |
|------|-------|------------|
| No automated tests for paste handlers | Med | Manual tests on Chrome, Edge, Firefox |
| React version may supersede Jinja2 fixes | Low | Jinja2 template is current deployed source of truth |
| Clipboard API cross-browser diff | Low | `clipboardData.items` widely supported |

## Rollback Plan

Revert the three isolated edits in `app/templates/control_errores.html`. No schema changes, data migrations, or backend rollback. Revert time: < 1 minute.

## Dependencies

None.

## Success Criteria

- [ ] Pasting in `cargaTextarea` adds the image once, not twice
- [ ] Pasting multiple images picks the most recent one (last in clipboard items)
- [ ] Browser default paste text does NOT appear alongside image upload
- [ ] Individual error paste (no modal) continues to work without regression
- [ ] Carga Masiva paste path continues to work without regression
- [ ] Manual tests pass on Chrome, Edge, and Firefox
