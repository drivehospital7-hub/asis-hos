# Delta for control_errores — Validador Column

## ADDED Requirements

### R9: Validador — Auto-Fill on Creation

The system MUST auto-populate `validador` with `primer_nombre + " " + apellido_1` from the Flask session when creating a novedad via POST `/api/control-errores`. The system MUST NOT accept `validador` from client payloads — server-side only.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Full name populated | session has `primer_nombre="Juan"`, `apellido_1="Pérez"` | POST valid payload | stored `validador` = `"Juan Pérez"` |
| Client payload ignored | session has valid user | POST with `{"validador":"hacker"}` | stored `validador` uses session, not payload |
| Session keys guaranteed | `do_login()` has run | any authenticated POST | `session["primer_nombre"]` and `session["apellido_1"]` exist (no KeyError) |

### R10: Validador — Read-Only Column in Template

The Validador column MUST render as the FIRST `<th>` in the Jinja2 table (`control_errores.html`). Each validador `<td>` MUST be read-only — no `editable-cell` class, no click handler. Every `colspan` attribute in the template SHALL be `8`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First column | page rendered | inspect `<th>` order | first `<th>` is Validador |
| Read-only cell | any novedad row | inspect `<td>` | no `editable-cell` class, no click binding |
| colspan updated | template rendered | check all `colspan` | every `colspan` = `8` |

### R11: Validador — Backward Compatibility

Existing novedades (stored before this change) that lack a `validador` field, or have it set to empty string, MUST display `-` in the Validador cell.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Missing key | novedad dict has no `validador` key | row rendered | cell displays `-` |
| Empty value | novedad has `validador: ""` | row rendered | cell displays `-` |
