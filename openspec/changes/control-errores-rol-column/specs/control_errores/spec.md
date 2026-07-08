# Delta for control_errores

## ADDED Requirements

### R12: Rol Column Display

The system MUST inject `responsable_rol` into each error record via `get_errores()` using `get_facturadores()` as the role source. The Rol column SHALL appear between "Responsable" and "Pendiente" in the HTML table and CSV export. When no role data is available, the cell MUST display `-`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Role populated | `get_facturadores()` maps `"Juan Pérez"` to `"facturador"` | `get_errores()` processes record with `responsable: "Juan Pérez"` | `responsable_rol` is `"facturador"` |
| Empty fallback | `get_facturadores()` has no entry for the responsable user | `get_errores()` processes record | `responsable_rol` is `"-"` |
| CSV sync | CSV export triggered | inspect header and rows | `"Rol"` column present between `"Responsable"` and `"Pendiente"` with correct values |

## MODIFIED Requirements

### R10: Validador — Read-Only Column in Template

The Validador column MUST render as the FIRST `<th>` in the Jinja2 table (`control_errores.html`). Each validador `<td>` MUST be read-only — no `editable-cell` class, no click handler. Every `colspan` attribute in the template SHALL be `9`.
(Previously: colspan was `8`)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First column | page rendered | inspect `<th>` order | first `<th>` is Validador |
| Read-only cell | any novedad row | inspect `<td>` | no `editable-cell` class, no click binding |
| colspan updated to 9 | template rendered | check all `colspan` attributes | every `colspan` = `9` |
