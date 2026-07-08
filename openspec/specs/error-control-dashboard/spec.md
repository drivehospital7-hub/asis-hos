# Error Control Dashboard Specification

## Purpose

The `error-control-dashboard` capability governs table rendering, column layout, and CSV export on the control-errores page. It defines column order, width allocation, overflow behavior, and export consistency.

## Requirements

### D1: Column Order

The HTML table and CSV export SHALL render columns in the exact order: Validador, Tipo Error, Descripción, Factura, Responsable, Rol, Pendiente, Estados Cita, Observación. The Rol column SHALL be dynamically enriched from `get_facturadores()`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Correct order | page rendered | inspect `<th>` elements | order matches all 9 columns |
| CSV does not desync | any CSV export | inspect header and row builder | columns match HTML order exactly |

### D2: Column Widths and Overflow

CSS column widths SHALL be: Descripción 30%, Responsable 10%, Rol 8%. The remaining 52% SHALL be distributed among other columns. The table container SHALL have `overflow-x: auto` with a visible scrollbar when content overflows.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Widths applied | page rendered | inspect CSS width rules | Descripción=30%, Responsable=10%, Rol=8% |
| Horizontal overflow | viewport narrower than table | inspect container | `overflow-x: auto` set; scrollbar visible |
