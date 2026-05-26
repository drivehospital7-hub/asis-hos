# Tasks: Fix sidebar permission mapping for `control_urgencias`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1 (+1 for test, ~2 total) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Fix endpoint mapping

- [x] 1.1 In `app/templates/base.html` line 84, change `control_errores.control_errores_react` → `control_errores.control_errores_page`

## Phase 2: Verify with test

- [x] 2.1 Add a test confirming that a user with `control_urgencias` permission sees "Control de Novedades" link rendered in the sidebar

## Implementation Order

Phase 1 is the fix itself (1 char change). Phase 2 adds a regression guard. Order between phases doesn't matter since they touch different files, but 1.1 must precede test validation for 2.1 to pass.
