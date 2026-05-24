# Proposal: Control Urgencias — Realtime Refresh & Inline Editing Fixes

## Intent

The Control Urgencias page has critical race conditions between its 3-second polling mechanism and inline editing. Users lose edits mid-edit when polling re-renders the table, PUT requests silently swallow errors (fire-and-forget fetch with no error checking), and the full-table re-render causes pagination resets and flicker. This change fixes the three most critical race conditions in the existing mechanism.

## Scope

### In Scope
- Guard polling to skip re-render when an inline editor is active
- Make `updateBackend` properly async with error handling (revert cache on failure)
- Handle 404/403/500 PUT responses gracefully and show user feedback
- Revert optimistic cache updates on backend failure

### Out of Scope
- Version-based optimistic locking (deferred to future change)
- Partial/diff-based table updates (deferred)
- WebSocket or SSE push replacement (deferred)
- Server-side `lastUpdate` from response timestamp
- AddNewRow race condition fix (deferred — same root cause, lower priority)

## Capabilities

### New Capabilities

None — this is a refinement of existing behavior, not a new capability.

### Modified Capabilities

None — no spec-level requirements change. All changes are implementation-only fixes to the existing polling and editing mechanism. The existing `control_errores` spec (permission model) is unaffected.

## Approach

Follow **Approach 1 (Minimal Fix)** from the exploration:

1. **Poll guard**: Before `loadErrores()` in the poll handler, check `if (currentEditId || isAdding) return;`. The poll silently skips that cycle. `lastUpdate` is NOT modified — the next poll cycle picks up pending changes once the edit completes.
2. **Async PUT with error handling**: Convert `updateBackend()` to `async/await`. On non-2xx response, revert the optimistic update in `cachedErrores`, show a toast/alert with the error, and do NOT clear `lastUpdate` so next poll re-fetches correct data.
3. **Graceful 404/403 handling**: 404 → remove the row from `cachedErrores` and notify the user. 403 → revert the field to its pre-edit value and show "Permission denied" message.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/templates/control_errores.html` | Modified | Add poll guard, make `updateBackend` async, add error handling + revert logic |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Poll guard delays external sync during long edits | Low | 3-second poll retries every cycle; max delay is edit duration |
| Toast/alert UX may be jarring | Low | Use non-blocking toast (existing pattern in the codebase) |
| Revert logic could race with next poll | Low | On error, do NOT update `lastUpdate` — poll re-fetches fresh data |

## Rollback Plan

Revert the single template file `app/templates/control_errores.html` to its previous commit. No schema changes, no DB migrations, no API contract changes — single-file revert.

## Dependencies

None.

## Success Criteria

- [ ] Poll does not re-render during active edit (verified with two browser windows)
- [ ] Failed PUT restores the original value in the cache within same render cycle
- [ ] 404 from deleted row removes the row from cache and shows notification
- [ ] 403 from permission change reverts value and shows "Permission denied"
- [ ] Existing spec tests for permission model still pass
