# Responsible Assignment Specification

## Purpose

Pasted billing TSV is auto-parsed into a 9-column results table with responsible assignment per schedule, vencida highlighting, and per-row Envío a Control — gated by `can_write`.

## Requirements

### Requirement: Auto-Detect Columns

The system MUST provide `autoDetectColumns(headers, primeraFila)` returning indexes for fechaCrea, fechaEgreso, factura, area, paciente, estado, hcPendiente, and fechaCierre — by header label first, then by value pattern.

#### Scenario: Headers present

- GIVEN a header row with "Fecha Crea", "Fecha Egreso", "N° Factura"
- WHEN `autoDetectColumns` is called
- THEN it returns correct column indexes

#### Scenario: Detect by pattern

- GIVEN no header row, with two `dd/mm/yyyy hh:mm:ss` columns and a `FEV`-prefixed value
- WHEN `autoDetectColumns` is called
- THEN first date → `fechaCrea`, second → `fechaEgreso`, `FEV` column → `factura`

#### Scenario: FEV standalone prefix

- GIVEN a column contains only "FEV" and the next column has only digits
- WHEN processed
- THEN `factura` index points to the "FEV" column

### Requirement: Calculate Responsible

The system MUST provide `calcularResponsable(fechaCreaStr, fechaEgresoStr, cronograma)` that determines shift by egreso time and maps via `NOMBRE_MAP`.

#### Scenario: Mañana shift (06:30-12:29)

- GIVEN egreso at `10:15:00`, schedule has `CARLOS` for `manana`
- WHEN called
- THEN returns `"CARLOS OMAR"`

#### Scenario: Night shift crosses midnight

- GIVEN egreso at `03:00:00` (<06:30) on day 5
- WHEN called
- THEN looks up `noche` in day 4's entry

#### Scenario: No egreso or egreso before creación

- GIVEN `fechaEgresoStr` is null OR egreso < creación
- WHEN called
- THEN returns `"Sin Egreso"`

### Requirement: Detect Vencida Rows

The system MUST add CSS class `resp-row--vencida` when `estado` is "Abierta" and egreso is >4 calendar days before today (`Math.floor` of date diff, NOT 96 hours).

#### Scenario: >4 days

- GIVEN egreso 6 days ago, estado "Abierta"
- WHEN rendering
- THEN row has `resp-row--vencida`

#### Scenario: Exactly 4 days

- GIVEN egreso exactly 4 days ago, estado "Abierta"
- WHEN rendering
- THEN row does NOT have `resp-row--vencida`

### Requirement: Per-Row Envío a Control

The system MUST provide a button per row that POSTs to `/api/control-errores` with `tipo_error: "Factura Abierta"`, factura, observación, and responsable. Buttons have 3 states.

#### Scenario: First send

- GIVEN factura not in Control de Errores
- WHEN the "+" button is clicked and confirmed
- THEN POST is sent; on success button becomes "✓ Enviado"

#### Scenario: Duplicate

- GIVEN factura exists in Control de Errores
- WHEN the "⚠+" button is clicked and duplicate is confirmed
- THEN a POST is sent with the same data

#### Scenario: Already sent

- GIVEN factura was sent this session
- WHEN the page renders
- THEN button shows "✓ Enviado" (non-interactive)

### Requirement: Pre-load Existing Records

The system MUST fetch `GET /api/control-errores` before rendering results to pre-populate the existing-factura set.

#### Scenario: Existing factura

- GIVEN `FEV416009` exists in Control de Errores
- WHEN rendering
- THEN its button shows "⚠+" instead of "+"

### Requirement: Copy Results to Clipboard

The system MUST provide `copiarResultados()` that copies the results as TSV with a 9th "Envío" column (value: "Enviado", "Ya existe", or empty).

#### Scenario: Results with mixed states

- GIVEN 5 rows with various Envío states
- WHEN user clicks "Copiar a Excel"
- THEN TSV with headers and 5 rows is written to clipboard
