# Cronograma Bacteriólogas Specification

## Purpose

Panel to manage the monthly schedule of bacteriólogas (5 professionals). Users paste TSV text from Excel containing daily shift assignments (CE, PYM, N, L, D) and the system persists it as JSON, displays it as a table, and allows querying which bacterióloga is assigned to a given shift type on a given day.

## Requirements

### Requirement: TSV Paste and Parse

The system MUST accept a TSV text paste from Excel with the following structure:
- First row: header with column names (starting with "DIA"/"DÍA")
- Subsequent rows: day number (1-31) followed by shift-type column values
- Shift-type columns: CE, PYM, N, L, D (each cell contains a bacterióloga's first name, or is empty)
- The system MUST normalize line endings and handle multi-line quoted fields

#### Scenario: Happy path — parse valid TSV with all columns

- GIVEN a TSV paste with headers `DIA\tCE\tPYM\tN\tL\tD` and 30 data rows with valid day numbers and first names in cells
- WHEN the user clicks "Parsear y Guardar"
- THEN the system returns a JSON array of 30 `{dia, CE, PYM, N, L, D}` objects
- AND all first names are trimmed of whitespace

#### Scenario: Error — TSV without DIA header

- GIVEN a TSV paste that does not contain "DIA" or "DÍA" as the first column header
- WHEN the user attempts to parse
- THEN the system MUST return an error indicating the header row was not found

#### Scenario: Error — invalid day number

- GIVEN a TSV paste where a data row has a non-numeric or out-of-range (not 1-31) day value
- WHEN the user attempts to parse
- THEN the system MUST skip that row and NOT include it in the result
- AND the system SHOULD log the skipped row

#### Scenario: Edge — shift cell is empty

- GIVEN a TSV paste where some shift cells are empty (e.g., `1\tKAREN\t\t\tLISBETH\t`)
- WHEN the user parses
- THEN the empty cells MUST be stored as empty strings `""`
- AND the parse MUST succeed

### Requirement: First Name Matching

The system MUST resolve short first names from the TSV cells to full bacterióloga names via a `NOMBRE_MAP` constant. The mapping MUST include at least 5 bacteriólogas.

#### Scenario: Happy — match "KAREN" to full name

- GIVEN a TSV with cell value "KAREN"
- WHEN the system processes the parsed schedule
- THEN "KAREN" MUST be resolved to "MADROÑERO BURBANO KAREN LIZETH" (or the corresponding full name in `NOMBRE_MAP`)

#### Scenario: Edge — unknown name not in NOMBRE_MAP

- GIVEN a TSV cell value that does not match any key in `NOMBRE_MAP`
- WHEN the system processes the parsed schedule
- THEN the original unrecognized value MUST be kept as-is

### Requirement: Persist Schedule (POST /cronograma-bacteriologas/api)

The system MUST persist the parsed schedule to `app/data/cronograma_bacteriologas.json` with the current month and year.

#### Scenario: Happy — save schedule for the first time

- GIVEN a list of 30 `{dia, CE, PYM, N, L, D}` objects
- WHEN `POST /api` receives `{"dias": [...]}`
- THEN the system writes a JSON file with `mes` (current month), `anio` (current year), `columnas` (["CE", "PYM", "N", "L", "D"]), `dias` (the array), and `total_dias` (30)
- AND returns `status: "success"` with the saved data

#### Scenario: Error — empty data

- GIVEN an empty dias array
- WHEN `POST /api` receives `{"dias": []}`
- THEN the system MUST return `status: "error"` with error message "No hay datos para guardar"

#### Scenario: Edge — overwrite existing file

- GIVEN an existing `cronograma_bacteriologas.json` from a previous save
- WHEN `POST /api` saves a new schedule
- THEN the existing file MUST be overwritten with the new data for the current month

### Requirement: Retrieve Schedule (GET /cronograma-bacteriologas/api)

The system MUST return the persisted schedule for the current month. If the saved data is from a different month or does not exist, return empty data.

#### Scenario: Happy — schedule exists for current month

- GIVEN a saved schedule for the current month
- WHEN `GET /api` is called
- THEN the system returns `status: "success"` with `data.horario` containing the full JSON object and `data.total_dias` with the day count

#### Scenario: Edge — no schedule file

- GIVEN no `cronograma_bacteriologas.json` file exists
- WHEN `GET /api` is called
- THEN the system returns `status: "success"` with `data.horario: null` and `data.total_dias: 0`

#### Scenario: Edge — schedule from a different month

- GIVEN a saved schedule from a previous month
- WHEN `GET /api` is called
- THEN the system MUST treat it as empty and return `data.horario: null`

### Requirement: Delete Schedule (DELETE /cronograma-bacteriologas/api)

The system MUST allow deletion of the schedule file.

#### Scenario: Happy — delete existing file

- GIVEN an existing schedule file
- WHEN `DELETE /api` is called
- THEN the file MUST be removed
- AND the system returns `status: "success"`

### Requirement: Shift Detection

Given a day number, the system MUST return which bacteriólogas are assigned to the shifts CE, PYM, or CE/PYM on that day.

#### Scenario: Happy — detect CE and PYM on day 5

- GIVEN a schedule where day 5 has `CE: "KAREN"`, `PYM: "VALENTINA"`
- WHEN the shift detection is invoked for day 5
- THEN the result MUST show MADROÑERO BURBANO KAREN LIZETH for CE and the full name for VALENTINA for PYM

#### Scenario: Edge — day has no CE/PYM assignment

- GIVEN a schedule where day 15 has empty values for CE and PYM
- WHEN the shift detection is invoked for day 15
- THEN the result MUST indicate no bacterióloga assigned for those shifts

#### Scenario: Edge — day does not exist in schedule

- GIVEN a schedule that has no entry for day 31
- WHEN the shift detection is invoked for day 31
- THEN the system MUST return empty results

### Requirement: Admin-Only Access

All endpoints MUST require the `*` (admin) permission. Non-admin users MUST be rejected.

#### Scenario: Happy — admin accesses panel

- GIVEN a user with `*` in their permisos list
- WHEN they call any API endpoint or load the page
- THEN the system responds with the expected data (200)

#### Scenario: Error — non-admin access

- GIVEN a user without `*` permission
- WHEN they call the API endpoints
- THEN the system returns 401 or 403

### Requirement: Sidebar Entry

The sidebar MUST show "Cronograma Bacteriólogas" only for users with `*` permission.

#### Scenario: Happy — admin sees the entry

- GIVEN a user with admin permissions
- WHEN the sidebar renders
- THEN the nav item with label "Cronograma Bacteriólogas", href `/cronograma-bacteriologas`, and icon `CalendarClock` (or similar) MUST be visible

#### Scenario: Error — non-admin does not see the entry

- GIVEN a user without `*` permission
- WHEN the sidebar renders
- THEN the nav item MUST NOT be visible

### Requirement: Vite Entry Registration

The system MUST register the page as a Vite entry point in `frontend/vite.config.ts` under `rollupOptions.input`.

#### Scenario: Happy — entry builds

- GIVEN `frontend/src/pages/cronograma-bacteriologas/index.html` exists
- WHEN `npm run build` is executed
- THEN the output manifest MUST include the entry

### Requirement: Valid Shift Types

The only valid shift-type column values in the schedule MUST be: CE, PYM, CE/PYM, N, L, D, or empty string. Any other value SHOULD be flagged.

#### Scenario: Happy — all valid types present

- GIVEN a fully populated schedule row with values CE, PYM, N, L, D in their respective columns
- WHEN the system processes the data
- THEN no validation errors are produced

#### Scenario: Edge — CE/PYM combined in one column

- GIVEN a column cell containing "CE/PYM"
- WHEN the system processes the data
- THEN "CE/PYM" MUST be accepted as a valid value
