# Procedimientos Contratados Specification

## Purpose

Validate that every (Cód Entidad Cobrar, Código CUPS) pair in an Excel invoice exists as a contracted relationship in PostgreSQL. This prevents glosas by catching uninsured procedures before submission.

## Requirements

### Requirement: Detect CUPS sin contrato

The system **MUST** verify that each invoice row's `Cód Entidad Cobrar` + `Código` pair exists in the contracted-procedures chain: `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`.

#### Scenario: CUPS contratado (happy path)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "878001"
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- WHEN the detector processes that row
- THEN no error is generated for that row

#### Scenario: CUPS no contratado para la entidad

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "999999"
- AND the pair ("EMSS18", "999999") does NOT exist in the contracted-procedures chain
- WHEN the detector processes that row
- THEN an error is generated with `problema` = "CUPS 999999 no contratado para EMSS18, EMSSANAR ESS E.S.S."

#### Scenario: Código de entidad no existe en DB

- GIVEN a row with `Cód Entidad Cobrar` = "NONEXIST" and `Código` = "878001"
- AND "NONEXIST" does not appear in `eps_contratado.cod_contrato`
- WHEN the detector processes that row
- THEN an error is generated with message including "CUPS 878001 no contratado para NONEXIST"

#### Scenario: CUPS no existe en procedimiento

- GIVEN a row with `Código` = "INVALID99" and `Cód Entidad Cobrar` = "EMSS18"
- AND "INVALID99" does not appear in `procedimiento.cups`
- WHEN the detector processes that row
- THEN an error is generated indicating the CUPS is not contracted

#### Scenario: DB no disponible

- GIVEN the PostgreSQL database is unreachable (connection error)
- WHEN the detector is called
- THEN it returns an empty list `[]`
- AND logs a warning — no crash

#### Scenario: Columnas faltantes

- GIVEN the Excel does not contain column `Cód Entidad Cobrar` (indices key `codigo_entidad_cobrar` is `None`)
- OR column `Código` (indices key `codigo` is `None`)
- WHEN the detector is called
- THEN it returns an empty list `[]`

#### Scenario: Tolerancia a formato (espacios, mayúsculas)

- GIVEN a row with `Cód Entidad Cobrar` = "  emss18  " and `Código` = "  878001  "
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- WHEN the detector processes that row
- THEN the values are normalized via `.strip().upper()` before comparison
- AND no error is generated for that row

### Requirement: Integración en detect_all.py de cada área

The detector **MUST** be called from every area orchestrator: Urgencias, Hospitalización, Intramural, Ambulatoria, Odontología, and Equipos Básicos.

#### Scenario: Llamado desde orquestador

- GIVEN an area `detect_all.py` that imports `detect_cups_sin_contrato` from `app.services.transversales.procedimiento_contratado`
- WHEN the area orchestrator runs
- THEN the detector result is included in the `error_groups` dict with key `"Cups Sin Contrato"`
- AND the result passes through `build_normalized_rows()`

### Requirement: Normalización a filas uniformes

The system **MUST** map each detector result to a normalized row with `tipo_error` = "Cups Sin Contrato".

#### Scenario: Normalized row output

- GIVEN a detector result `{"factura": "F001", "codigo": "999999", "procedimiento": "CONSULTA", "codigo_entidad_cobrar": "EMSS18", "entidad": "EMSSANAR ESS E.S.S.", "problema": "CUPS 999999 no contratado para EMSS18, EMSSANAR ESS E.S.S."}`
- WHEN `build_normalized_rows()` processes the error group
- THEN a row is produced with `tipo_error` = "Cups Sin Contrato", `descripcion` = the problema text, `procedimiento` = "999999 - CONSULTA", and `detalle` = "Entidad: EMSS18, EMSSANAR ESS E.S.S."
