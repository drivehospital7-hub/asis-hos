# Tasks: Panel principal en sidebar para todos los usuarios

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 10–20 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Jinja2 sidebar

- [x] 1.1 Added standalone "Panel principal" link before `_ep_map` in the `else` branch (line 78+), wrapped in `{% if session.get('ce_authenticated') %}` — always shown for authenticated non-admin users
- [x] 1.2 Admin path (line 66) verified untouched — still iterates all `nav_items` including `home.home_react`

## Phase 2: React sidebar

- [x] 2.1 Removed `permiso: "*"` from the "Panel principal" nav item — `!item.permiso` at line 49 now shows it for all authenticated users

## Phase 3: Testing

- [x] 3.1 Added `tests/services/test_sidebar_panel_principal.py` with 3 tests: non-admin sees Panel principal, admin still sees it, unauthenticated does NOT see it
- [x] 3.2 `pytest -v` confirms 38 passed (35 baseline + 3 new), pre-existing `manifest_has_eleven_html_entries` failure unchanged
