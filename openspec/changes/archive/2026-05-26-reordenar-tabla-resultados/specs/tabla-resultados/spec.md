# Tabla de Resultados — Presentación

## Purpose

Define the column layout and rendering behavior of the results table shared by the odontología, urgencias, and equipos básicos modules. This is a presentation-level spec — no detection pipeline logic is affected.

## Scope

Applies to three React pages:
- `frontend/src/pages/odontologia/page.tsx`
- `frontend/src/pages/urgencias/page.tsx`
- `frontend/src/pages/odontologia-equipos-basicos/page.tsx`

---

## Requirements

### R1: Fec. Factura as First Column

The results table MUST display **"Fec. Factura"** as its first (leftmost) column.

The datum MUST be the invoice date (`fec_factura`) obtained by mapping each `factura` (invoice number) from the normalized row back to the raw Excel sheet.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Date available | raw sheet contains `Factura`→`Fec Factura` mapping | row renders | first cell shows `fec_factura` |
| Date missing | `factura` not found in raw sheet mapping | row renders | first cell shows empty string |
| Factura is blank/null | row has no `factura` | row renders | first cell shows empty string |

### R2: Acción Column Removed

The results table MUST NOT render an **"Acción"** column or any **"Controlar"** button.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| No Acción header | any results data | `<table>` renders | no `<th>Acción</th>` present |
| No Controlar button | same | `<table>` renders | no `<Button>Controlar</Button>` present in any row |

### R3: Backend Response — Column Consistency

The JSON response from each area's route MUST include the key `fec_factura` in every element of `all_items`, and the string `"Fec. Factura"` as the first entry of the `columnas` array.

The `columnas` array length MUST equal the number of columns rendered in the `<thead>`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Columnas includes Fec. Factura | route returns JSON | inspected | `"Fec. Factura"` is first in `columnas` |
| All items include fec_factura | route returns JSON | inspected | each `all_items` entry has a `fec_factura` key |
| Counts match | response available | rendered | `<th>` count === `columnas.length` |

### R4: Non-Regression — No Other Columns Changed

No other table columns (existing order, names, or rendering) are affected by this change. The three columns that follow `Fec. Factura` are `Factura`, `Valor Factura`, and the remaining area-specific columns — all SHALL remain as-is.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Existing columns intact | any results data | table renders | columns after `Fec. Factura` match current order |
| Excel export unaffected | processed Excel generated | CruceFacturas sheet | sheet columns unchanged by this change |

---

## Non-Functional Requirements

- **Resilience**: Missing `fec_factura` data SHALL produce an empty string, never crash the page.
- **Consistency**: All three modules (odontología, urgencias, equipos básicos) MUST share the same column layout behavior defined here.
