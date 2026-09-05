# Ordenado y Facturado Specification

## Purpose

Defines filtering rules for the "Ordenado y Facturado" cross-check. The system
compares invoice data (reporte) against diagnostic aid records (ayudas) and
detects un-invoiced records, restricted to specific code groups:
`PROCESADOS_PARTO`, `PROCESADOS_INTERCONSULTAS`, `PROCESADOS_OTROS`,
and `CODIGOS_EXCEPCION` (traslados).

## Requirements

### Requirement: Individual List Code Filter

The system MUST only include codes from `PROCESADOS_PARTO |
PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS` in the individual "no_facturados"
list. `CODIGOS_EXCEPCION` codes SHALL be excluded; they appear only via Notas
Enfermería matching.

#### Scenario: Parto code appears

- GIVEN a CUPS in `PROCESADOS_PARTO` is un-invoiced
- WHEN building the individual list
- THEN it appears as an entry

#### Scenario: OTROS code appears

- GIVEN a CUPS in `PROCESADOS_OTROS` is un-invoiced
- WHEN building the individual list
- THEN it appears as an entry

#### Scenario: Non-matching code excluded

- GIVEN a CUPS not in `PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS` is
  un-invoiced
- WHEN building the individual list
- THEN it is excluded

#### Scenario: Exception code excluded

- GIVEN a CUPS in `CODIGOS_EXCEPCION` is un-invoiced
- WHEN building the individual list
- THEN it is excluded

### Requirement: Totalizado Aggregation

The system MUST replace per-code totalizado rows with 4 aggregate category
rows. Each row SHALL sum `total_reporte`, `total_ordenadas`, and
`total_no_facturado` across its codes. The `codigo` field SHALL be the category
name.

| Category       | `codigo`          | Codes Source                                                   |
|----------------|-------------------|----------------------------------------------------------------|
| Parto          | `"PARTO"`         | `PROCESADOS_PARTO`                                             |
| Interconsultas | `"INTERCONSULTAS"`| `PROCESADOS_INTERCONSULTAS`                                    |
| Otros          | `"OTROS"`         | `PROCESADOS_OTROS`                                             |
| Traslados      | `"TRASLADOS"`     | `CODIGOS_EXCEPCION` (via Notas Enfermería)                     |

#### Scenario: All categories rendered

- GIVEN codes from all 4 categories exist
- WHEN building the totalizado
- THEN 4 rows (PARTO, INTERCONSULTAS, OTROS, TRASLADOS) appear with summed
  totals

#### Scenario: Empty category suppressed

- GIVEN a category has zero counts in reporte, ordenadas, and no_facturado
- WHEN building the totalizado
- THEN that row is omitted

### Requirement: OTROS Code Inclusion

Code `861801` is in `PROCESADOS_OTROS` and MUST appear in both the
individual list and the OTROS aggregate row.

#### Scenario: 861801 appears in OTROS

- GIVEN 861405 exists in ayudas un-invoiced
- WHEN building results
- THEN it appears in the individual list AND in the OTROS totalizado row

### Requirement: CODIGOS_TOTALIZADO Removal

The constant `CODIGOS_TOTALIZADO` and all references MUST be removed from the
service file.

#### Scenario: Constant deleted

- GIVEN the refactored service file
- WHEN searching for `CODIGOS_TOTALIZADO`
- THEN no matches exist in the codebase

### Requirement: API Contract Preserved

Each totalizado row MUST retain `{codigo, procedimiento, total_reporte,
total_ordenadas, total_no_facturado}`. The `es_notas` flag MAY appear on
Traslados rows when Notas Enfermería data is present.

#### Scenario: Field names stable

- GIVEN a valid request
- WHEN inspecting totalizado rows
- THEN all required fields are present with correct types

### Requirement: Tests

The system MUST include a test file at
`tests/services/test_ordenado_facturado_service.py` covering filtering,
aggregation, deduplication, and backward compatibility.

#### Scenario: Visible codes filtering

- GIVEN ayudas with a mix of Parto, Interconsulta, OTROS, and unrelated codes
- WHEN running the service
- THEN only Parto, Interconsulta, and OTROS codes appear in the individual list

#### Scenario: Totalizado aggregation

- GIVEN ayudas with codes from multiple categories
- WHEN running the service
- THEN the totalizado contains aggregate rows instead of per-code entries

#### Scenario: 861801 visible in OTROS

- GIVEN ayudas with 861801
- WHEN running the service
- THEN the code appears in the individual list and the OTROS totalizado row
