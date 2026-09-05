# Delta for duplicados-farmacia

## ADDED Requirements

### Requirement: Shared Base Detection Function

The system MUST refactor the `duplicados_farmacia` detector to delegate its core logic to a shared base function located in `app/services/transversales/`. This base function SHALL accept parameters for column indices, filters, grouping keys, and output type_error prefix. The Urgencias detector SHALL invoke the shared function with the same parameters as the current hardcoded behavior (tarifario filter, codigo_tipo_procedimiento filter, group by factura+tipo_procedimiento, type_error "Duplicados Farmacia").

The external behavior MUST remain identical:
- Same column requirements (`tipo_factura_descripcion`, `numero_factura`, `tarifario`, `codigo_tipo_procedimiento`, `codigo`, `cantidad`)
- Same filters (tipo_factura="Urgencias", tarifario="Suministros, Medicamentos", codigo_tipo_procedimiento in {"09","12"})
- Same grouping key `(factura, codigo_tipo_procedimiento)`
- Same output format (group-level flag when ALL pairs are duplicated)
- Same type_error "Duplicados Farmacia"

#### Scenario: Refactored detector produces identical output

- GIVEN the refactored `detect_duplicados_farmacia()` using the shared base function
- WHEN run against the same data sheet
- THEN it MUST return the exact same results as before (same flags, same grouping, same format)

#### Scenario: Shared function is reusable

- GIVEN the shared base function in `app/services/transversales/`
- WHEN invoked with different filter and grouping parameters
- THEN it SHALL correctly detect duplicates for a different tipo_factura with those parameters
