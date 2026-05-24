# Tasks: Control Urgencias — Realtime Refresh & Inline Editing Fixes

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~100–200 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Poll guard + Async PUT + Error handling + Testing | PR 1 | Single file (`control_errores.html`); all changes fit in one PR |

## Phase 1: Poll Guard

- [x] 1.1 Add `if (currentEditId || isAdding) return;` at the top of the poll `setInterval` handler, before `loadErrores()` call
- [x] 1.2 Verify `lastUpdate` is NOT modified on poll skip — next cycle picks up pending changes once edit completes

## Phase 2: Async PUT with Cache Revert

- [x] 2.1 Convert `updateBackend()` from fire-and-forget `fetch(...)` to `async/await` with response checking
- [x] 2.2 On non-2xx response: restore original value from `cachedErrores`, do NOT clear `lastUpdate`
- [x] 2.3 Show user-facing error notification (toast) matching existing codebase pattern

## Phase 3: Graceful HTTP Error Handling

- [x] 3.1 Handle 404: remove row from `cachedErrores`, notify user with "Row was deleted by another user"
- [x] 3.2 Handle 403: revert field to pre-edit value in `cachedErrores`, show "Permission denied" toast
- [x] 3.3 Handle 5xx: show generic "Server error, your change was not saved" toast, revert cache

## Phase 4: Testing

- [x] 4.1 Manual verification with two browser windows: poll does not re-render during active edit, failed PUT reverts cache, 404 removes row, 403 shows permission denied
- [x] 4.2 Run `tests/services/test_control_errores_service.py` and `test_control_errores_integration.py` — verify all existing permission tests still pass

## Implementation Order

Phase 1 is the poll guard — it directly protects the editor from being destroyed by re-renders. Phase 2 and 3 happen together since the async error handling is the same code path (check response → revert cache → show toast). Phase 4 verifies everything end-to-end. No interdependencies between phases 1, 2–3, or 4 — but Phases 2–3 should be done as one logical block since error handling per status code is a switch/case inside the same async function.

## Next Step

Ready for `sdd-apply`. All tasks modify a single file (`app/templates/control_errores.html`). Estimated ~100–200 lines, well under the 400-line budget.
