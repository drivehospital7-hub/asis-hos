# Proposal: Fix Jinja2 sidebar endpoint for `control_urgencias` permission

## Intent

Users with `control_urgencias` permission cannot see "Control de Novedades" in the legacy Jinja2 sidebar because `base.html` maps it to a nonexistent endpoint (`control_errores.control_errores_react`). The actual route is `control_errores.control_errores_page`. This is a 1-character-fix bug.

## Scope

### In Scope
- Fix the `endpoint_map` entry in `app/templates/base.html` (line 84): change `'control_errores.control_errores_react'` → `'control_errores.control_errores_page'`

### Out of Scope
- Migrating `/control-errores` page to React shell pattern (deferred)
- Updating the dead React page at `frontend/src/pages/control-novedades/`
- Any broader permissions audit

## Capabilities

### New Capabilities
None — this is a config bugfix. No new spec-level behavior is introduced.

### Modified Capabilities
None — the intended behavior (show nav item for users with `control_urgencias`) was always the goal. The code had a wrong endpoint name; this fix aligns implementation with existing requirements. No spec changes needed.

## Approach

Correct the endpoint string in `base.html` line 84 from `'control_errores.control_errores_react'` to `'control_errores.control_errores_page'`. The endpoint exists and serves the Jinja2 template; the React sidebar is unaffected.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/templates/base.html` | Modified (1 char) | Fix `endpoint_map` value for key `control_urgencias` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Typo in endpoint name | Low | Verify `control_errores.control_errores_page` exists (confirmed in exploration) |
| Regression on React sidebar | None | React sidebar is independent — it reads `ALL_NAV` from React state, not from Jinja2 `endpoint_map` |

## Rollback Plan

Revert the single-line change: `'control_errores.control_errores_page'` → `'control_errores.control_errores_react'`.

## Dependencies

None.

## Success Criteria

- [ ] User with only `control_urgencias` permission sees "Control de Novedades" in legacy Jinja2 sidebar
- [ ] Admin (`*`) still sees all nav items
- [ ] React sidebar navigation is unchanged (no regressions)
