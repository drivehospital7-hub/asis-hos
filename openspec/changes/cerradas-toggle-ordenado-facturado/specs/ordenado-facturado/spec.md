# Delta for Ordenado y Facturado

## ADDED Requirements

### Requirement: Cerradas Filter

The system MUST accept an optional `cerradas: bool` parameter (default `False`)
in `procesar_cruce()`. When `True`, rows with empty `Fecha Cierre` (None, `""`,
NaN) MUST be excluded from `no_facturados`. The `total_no_facturado` and
`totalizado` values MUST be recalculated after filtering. When `False`, behavior
SHALL be identical to current.

#### Scenario: Cerradas OFF — no filter applied

- GIVEN ayudas with and without `Fecha Cierre`
- WHEN `cerradas=False`
- THEN all records appear in `no_facturados`

#### Scenario: Cerradas ON — empty Fecha Cierre excluded

- GIVEN ayudas has records with empty `Fecha Cierre` (None, `""`, NaN)
- WHEN `cerradas=True`
- THEN those records are excluded from `no_facturados`

#### Scenario: Totals recalculated after filter

- GIVEN `cerradas=True` and some records are filtered
- THEN `total_no_facturado` equals `len(no_facturados)`
- AND `totalizado` row counts reflect filtered values

### Requirement: Optional Column Tolerance

`Fecha Cierre` MUST be an optional header in ayudas. If the column is absent,
the system SHALL NOT error and `cerradas` SHALL have no effect.

#### Scenario: Column missing — no error

- GIVEN ayudas lacks `Fecha Cierre` column
- WHEN `cerradas=True`
- THEN result is success with no filtering applied

## MODIFIED Requirements

### Requirement: API Contract Preserved

Each totalizado row MUST retain `{codigo, procedimiento, total_reporte,
total_ordenadas, total_no_facturado}`. The `es_notas` flag MAY appear on
Traslados rows when Notas Enfermería data is present. `procesar_cruce()` MUST
accept an optional `cerradas: bool` parameter (default `False`).

(Previously: no `cerradas` parameter)

#### Scenario: Field names stable

- GIVEN a valid request
- WHEN inspecting totalizado rows
- THEN all required fields are present

#### Scenario: Cerradas parameter accepted

- GIVEN `cerradas=True` in request
- WHEN calling `procesar_cruce()`
- THEN no error occurs and filter is applied

### Requirement: Tests

The system MUST include tests covering filtering, aggregation, deduplication,
backward compatibility, AND cerradas toggle behavior.

(Previously: no cerradas toggle tests)

#### Scenario: Visible codes filtering

- GIVEN ayudas with mixed codes
- WHEN running the service
- THEN only PROCESADOS codes appear in individual list

#### Scenario: Totalizado aggregation

- GIVEN codes from multiple categories
- THEN totalizado has aggregate rows, not per-code entries

#### Scenario: 861801 visible in OTROS

- GIVEN ayudas with 861801
- THEN code appears in individual list and OTROS totalizado row

#### Scenario: Cerradas ON filters empty dates

- GIVEN mixed `Fecha Cierre` values
- WHEN `cerradas=True`
- THEN empty-date rows excluded from `no_facturados`

#### Scenario: Cerradas OFF includes all

- GIVEN mixed `Fecha Cierre` values
- WHEN `cerradas=False`
- THEN all rows appear regardless of `Fecha Cierre`

#### Scenario: Missing Fecha Cierre tolerated

- GIVEN ayudas without `Fecha Cierre` column
- WHEN `cerradas=True`
- THEN no error, no filtering
