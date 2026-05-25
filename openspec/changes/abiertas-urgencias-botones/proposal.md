# Proposal: Abiertas Urgencias — Port legacy JS to React

## Intent

The React page at `frontend/src/pages/abiertas-urgencias/page.tsx` is a static UI shell — "Cargar", "Editar", and "Asignar" buttons have no onClick handlers, textareas have no state binding, and there's no schedule fetching or results table. The legacy Jinja2 template (`app/templates/abiertas_urgencias.html`) has ~870 lines of working inline JavaScript. Port all client-side logic to React, extract pure utility functions, and consolidate UI into maintainable component patterns — without touching backend endpoints.

## Scope

### In Scope
- Schedule view (GET / load, dynamic table, clipboard copy)
- Parse & save schedule (textarea → pure TS parser → POST)
- Delete schedule (DELETE with confirm dialog)
- Asignar Responsable (facturas textarea, autoDetectColumns, calcularResponsable)
- Results table (9-column, vencida styling >4 days post-egreso, clipboard)
- Envío a Control per row (POST, 3-state button, duplicate preloading)
- Toast notification overlay (auto-dismiss)
- Auth gating via `can_write` prop on all mutation actions

### Out of Scope
- Backend API changes (endpoints exist and work unchanged)
- Legacy template deletion (keep until React is validated in production)
- Loading skeletons or error boundaries (defer to separate change)
- CSS rewrite beyond Tailwind parity with legacy layout

## Capabilities

### New Capabilities
- `schedule-management`: Schedule CRUD — GET/POST/DELETE endpoints, `parseScheduleText()` pure function, dynamic table with clipboard, gated by `can_write`
- `responsible-assignment`: Facturas textarea → `autoDetectColumns()` → `calcularResponsable()` (using `NOMBRE_MAP`) → 9-column results table with vencida row styling → per-row Envío a Control with 3-state button (add/exists/sent)

### Modified Capabilities
- None — `control_errores` API unchanged (the page only consumes the existing POST endpoint)

## Approach

**Architecture**: Single page component (abiertas-urgencias/page.tsx) with `useState`/`useEffect` for all state. Pure TS functions in `utils.ts`, constants (`NOMBRE_MAP`, column labels) in `constants.ts`. Inline `fetch` with try/catch + toast — consistent with OdontologiaPage pattern.

**Build order**: (1) Extract pure functions + constants, (2) Schedule CRUD + status bar, (3) Responsable assignment + results + send-to-control, (4) Toast cross-cutting, (5) Auth gating.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modified | Static shell → fully wired component |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | New | Pure functions: parseScheduleText, autoDetectColumns, calcularResponsable |
| `frontend/src/pages/abiertas-urgencias/constants.ts` | New | NOMBRE_MAP, column label constants |
| `app/templates/abiertas_urgencias.html` | Unchanged | Keep as reference until React is validated |
| `frontend/src/pages/abiertas-urgencias/main.tsx` | Unchanged | Entry point, already passes can_write |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Business rule mismatch (night shift crossover, 30-min reception rule, "vencida" calendar-day calc) | Medium | Port one unit at a time, compare output against legacy template with real data |
| parseScheduleText() CSV edge cases (quoted fields, multi-line) | Medium | Test with real schedule exports before deploy |
| Toast UX difference confuses operators | Low | Match legacy timing (3s auto-dismiss) and positioning exactly |

## Rollback Plan

Revert `frontend/src/pages/abiertas-urgencias/page.tsx`, `utils.ts`, and `constants.ts` to the previous commit. The legacy Jinja2 template (`app/templates/abiertas_urgencias.html`) remains untouched and continues to serve as fallback via Flask routing — no deployment coordination needed.

## Dependencies

- Existing Flask endpoints: `GET/POST/DELETE /abiertas-urgencias/api/schedule`, `GET/POST /api/control-errores`
- `can_write` boolean prop already passed from `main.tsx`

## Success Criteria

- [ ] All buttons and textareas have working handlers with state binding (no dead UI)
- [ ] Schedule CRUD (load/parse/delete) matches legacy behavior with real schedule data
- [ ] `calcularResponsable()` assigns the same responsible as legacy for identical inputs
- [ ] Envío a Control shows correct 3-state behavior: add (green), exists (yellow/confirm), sent (disabled)
- [ ] "Vencida" highlighting matches legacy: >4 calendar days from egreso, not 96 hours
- [ ] Auth gating disables Cargar/Editar/Eliminar when `can_write=false`
- [ ] All existing tests pass (`pytest -v`)
- [ ] Page loads without console errors
