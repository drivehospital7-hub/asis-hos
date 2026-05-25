# Schedule Management Specification

## Purpose

Schedule management handles CRUD operations for the monthly work schedule (cronograma) displayed on the Abiertas Urgencias page. It includes loading, parsing, saving, deleting, and clipboard-copying schedule data — all gated by the `can_write` permission.

## Requirements

### Requirement: Load Schedule on Mount

The system MUST fetch the current schedule from `GET /abiertas-urgencias/api/schedule` on page mount.

#### Scenario: Schedule data found

- GIVEN the server has a stored schedule with 22 days
- WHEN the page mounts
- THEN the status bar shows "Horario cargado — 22 días"
- AND a 4-column table renders with Día, Mañana (07:00-13:00), Tarde (13:00-19:00), Noche (19:00-07:00)

#### Scenario: No schedule exists

- GIVEN the server returns `status: "error"` or no `data.horario`
- WHEN the page mounts
- THEN the status bar shows "Falta cargar horario"
- AND the table renders an empty state with "Sin datos de horario"

### Requirement: Parse Schedule Text

The system MUST provide a pure function `parseScheduleText(text: string)` that normalizes line endings, joins multi-line quoted fields, finds the header row by "DIA"/"DÍA" keyword, and parses tab-separated rows into `{dia, manana, tarde, noche}` objects.

#### Scenario: Happy path with headers

- GIVEN input text with a "DÍA" header row followed by two data rows with tabs
- WHEN `parseScheduleText` is called
- THEN it returns an array of 2 objects with numeric `dia` and trimmed `manana`, `tarde`, `noche` strings

#### Scenario: Multi-line quoted fields

- GIVEN a cell value spans two lines wrapped in double quotes
- WHEN `parseScheduleText` processes it
- THEN the quoted field is merged into a single value before tab-splitting

#### Scenario: No header row found

- GIVEN input text without "DIA", "DÍA", or "DI" in any row's first column
- WHEN `parseScheduleText` is called
- THEN it returns `null`

### Requirement: Save Schedule via POST

The system MUST POST parsed schedule data as JSON `{dias: [...]}` to `/abiertas-urgencias/api/schedule` when the user clicks "Parsear y Guardar".

#### Scenario: Successful save

- GIVEN parsed schedule data with 22 days
- WHEN the user clicks "Parsear y Guardar"
- THEN a POST request is sent with the JSON body
- AND on success the status bar updates, the table re-renders, and the textarea clears

#### Scenario: Empty input

- GIVEN the textarea is empty
- WHEN the user clicks "Parsear y Guardar"
- THEN the system shows a toast "Pegá el texto del horario primero."
- AND no POST request is made

### Requirement: Delete Schedule via DELETE

The system MUST send `DELETE /abiertas-urgencias/api/schedule` with a confirmation dialog.

#### Scenario: Confirm and delete

- GIVEN a loaded schedule exists
- WHEN the user clicks the delete button and confirms the dialog
- THEN a DELETE request is sent
- AND on success the status bar shows empty state and the table clears

#### Scenario: Cancel delete

- GIVEN a loaded schedule exists
- WHEN the user clicks the delete button and cancels the dialog
- THEN no DELETE request is made

### Requirement: Copy Schedule to Clipboard

The system MUST provide a `copiarHorario()` function that copies the schedule table as TSV with headers `Día\t07:00-13:00\t13:00-19:00\t19:00-07:00`.

#### Scenario: Schedule loaded

- GIVEN the schedule table has rows
- WHEN the user clicks "CopiarHorario"
- THEN TSV text is written to the clipboard
- AND a toast shows "{N} filas copiadas al portapapeles"

### Requirement: Auth Gating

All mutation actions (save, delete, edit) MUST be disabled when `can_write` is `false`.

#### Scenario: Read-only user

- GIVEN `can_write` is `false`
- WHEN the page renders
- THEN the "Parsear y Guardar" button and delete/Edit buttons are disabled
- AND the "Cargar" toggle shows "Iniciá sesión para modificar" tooltip
