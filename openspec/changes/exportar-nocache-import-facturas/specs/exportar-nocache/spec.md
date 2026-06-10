# Exportar No-Cache Specification

## Purpose

After genderize cache verification in `/import-facturas`, users see hit/miss counts but cannot extract **which** patient names missed cache. This spec defines the behavior for exporting uncached `compound_name` values as a single-line, comma-separated `.txt` file.

## Requirements

### Requirement: Expose uncached names in stats response

The `POST /api/import/facturas-stats` endpoint MUST include a `nombres_no_cache` field in its JSON response containing the list of `compound_name` values that were **not** found in the genderize cache during token estimation.

Each name MUST use `compound_name` format:
- If the patient has both `primer_nombre` and `segundo_nombre`, use `"{primer_nombre} {segundo_nombre}"` (single space separator).
- If the patient has only `primer_nombre`, use that value alone.
- Names MUST appear in the same order as they appear in the source file.

The system MUST NOT spend additional API calls to determine cache misses — the list SHALL be derived from the existing `get_stats()` iteration.

#### Scenario: Happy path — partial cache miss

- GIVEN `get_stats()` has completed and identified 3 uncached names out of 20 total
- WHEN the frontend receives the `facturas-stats` response
- THEN `response.nombres_no_cache` SHALL be a non-empty array of strings
- AND each string SHALL be a valid `compound_name`

#### Scenario: All names cached

- GIVEN `get_stats()` found all names in cache (0 misses)
- WHEN `facturas-stats` responds
- THEN `response.nombres_no_cache` SHALL be an empty array `[]`

#### Scenario: All names uncached

- GIVEN `get_stats()` found no names in cache (100% misses)
- WHEN `facturas-stats` responds
- THEN `response.nombres_no_cache` SHALL contain every name from the file in source order

### Requirement: Export button visibility

The GenderizePage (React) MUST render an "Exportar no-cache" button **only** after a successful `facturas-stats` response where `nombres_no_cache` is a non-empty array.

The button MUST be hidden when:
- No stats estimation has been performed yet
- `nombres_no_cache` is empty (all names cached)
- The `/facturas-stats` request is in flight or failed

#### Scenario: Button appears after stats

- GIVEN the user has clicked "Ver estimación" and received a response with `nombres_no_cache.length = 3`
- WHEN the page re-renders
- THEN the "Exportar no-cache" button SHALL be visible

#### Scenario: Button hidden when all cached

- GIVEN `facturas-stats` returned `nombres_no_cache = []`
- WHEN the page re-renders
- THEN the "Exportar no-cache" button SHALL NOT be visible

#### Scenario: Button hidden before first estimation

- GIVEN the page was just loaded and no stats request has been made
- WHEN the page renders
- THEN no "Exportar no-cache" button SHALL appear

### Requirement: Download format

When the user clicks "Exportar no-cache", the system SHALL generate a `.txt` file download with the following format:

- Content: `compound_name` values separated by `, ` (comma + single space).
- The file SHALL contain exactly one line (no trailing newline).
- The file SHALL NOT have a trailing comma after the last name.
- Encoding SHALL be UTF-8 with BOM (`\uFEFF`) for Windows/Excel compatibility.
- The filename SHOULD be `nombres_no_cache.txt` or include a timestamp for uniqueness.

The download MUST NOT require a round-trip to the server — it SHALL be constructed client-side from the already-received `nombres_no_cache` array.

#### Scenario: Download produces correct format

- GIVEN `nombres_no_cache = ["Nicolas", "Johan Matias", "Angela", "Emilin Sofia", "Derly"]`
- WHEN the user clicks "Exportar no-cache"
- THEN a `.txt` file is downloaded containing exactly `Nicolas, Johan Matias, Angela, Emilin Sofia, Derly`
- AND the file encoding is UTF-8 with BOM
- AND no server request was made
