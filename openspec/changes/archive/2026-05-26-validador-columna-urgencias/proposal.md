# Proposal: Validador Column in Control de Novedades

## Intent

Add a read-only "Validador" column as the first column in the Control de Novedades table (Urgencias). The field auto-fills server-side with `primer_nombre + apellido_1` of the user creating the record, exactly like the existing "Creado" (fecha) field — set on creation, never editable.

## Scope

### In Scope
- Add `validador` field to the JSON storage model in `errores_storage.py`
- Auto-populate from Flask session in `control_errores_service.py`
- Render read-only Validador column in the Jinja2 template (`control_errores.html`): `<th>` first column, read-only `<td>` per row, `colspan` 7→8 throughout
- Handle backward compatibility for existing novedades (no `validador` → show `-`)

### Out of Scope
- React page (`frontend/src/pages/control-novedades/page.tsx`) — not yet wired, update deferred until route switch
- Route changes, permission changes, API schema changes — all validador logic is server-side
- New API fields or DB migrations — JSON storage is additive

## Capabilities

### New Capabilities
None — no new domain being introduced.

### Modified Capabilities
- `control_errores`: Requirements that MUST be added — validador auto-fill on creation (from session), read-only rendering in Jinja2 template, backward-compatible display for existing entries without validador. Delta will go in `openspec/changes/validador-columna-urgencias/specs/control_errores/spec.md`.

## Approach

Follow **Approach 1** (backend + Jinja2 only) from exploration:

1. `errores_storage.py::crear_error()` — add `validador: str = ""` param, store in JSON dict
2. `control_errores_service.py::add_error()` — compose `validador = f"{session['primer_nombre']} {session['apellido_1']}".strip()`, pass to `crear_error()`
3. `control_errores.html` — Validador as first `<th>`, read-only `<td>` per row (no `editable-cell`), `colspan` 7→8 everywhere, `addNewRow()` gets static validador cell with current user's name or `-`
4. Existing entries without `validador` → render `e.validador || '-'` in the template

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/utils/errores_storage.py` | Modified | `crear_error()` gets `validador` param; `update_error()` leaves it untouched |
| `app/services/control_errores_service.py` | Modified | `add_error()` reads session, passes composed validador |
| `app/templates/control_errores.html` | Modified | New `<th>` (first col), read-only `<td>` per row, `colspan` 7→8 everywhere, new-row validador cell |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing novedades lack `validador` | High (all current data) | Template renders `novedad.validador or '-'` — safe fallback for missing key |
| React page gap when wired later | Medium | Deferred to route-switch task; documented in exploration.md |
| User confuses validador with editable cells | Low | Validador cell has no `editable-cell` class, no click handler — visually distinct |

## Rollback Plan

1. **Revert code**: `git revert` the commit(s) — restores storage, service, and template to pre-Validador state
2. **Data**: No migration needed — removing `validador` from code leaves the JSON field orphaned (harmless). If needed, run a one-off script to `del n["validador"]` on all entries
3. **Deploy**: Same deploy path as the original change — no infra changes

## Dependencies

- `flask.session` must have `primer_nombre` and `apellido_1` keys (already set by `do_login()` — no changes needed)
- `app/utils/errores_storage.py` `crear_error()` is the only write path for new entries (no secondary creation points)

## Success Criteria

- [ ] New novedad created via POST `/api/control-errores` stores `primer_nombre + apellido_1` in `validador` field
- [ ] Jinja2 table shows Validador as first column with read-only value, no edit interaction
- [ ] Existing novedades (without `validador`) show `-` in the Validador cell
- [ ] All seven existing `colspan="7"` values in `control_errores.html` updated to `8`
- [ ] `pytest` passes (existing tests + new test for validador field on creation)
