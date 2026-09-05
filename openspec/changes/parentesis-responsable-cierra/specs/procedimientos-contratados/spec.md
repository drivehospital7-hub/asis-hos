# Delta for Procedimientos Contratados

## MODIFIED Requirements

### Requirement: Detect CUPS sin contrato

The system **MUST** verify that each invoice row's `Cód Entidad Cobrar` + `Código` pair exists in the contracted-procedures chain: `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`.

**Exception**: When the column `Responsable Cierra Facturar` matches a value in `FACTURADORES_URGENCIAS` (defined in `app/constants/urgencias.py`), the validation **MUST** use only procedures linked to `nota_hoja id=1` ("OTRAS EPB SOLO URGENCIAS") instead of the entity's contractual chain.

(Previously: validated against the entity's contractual chain for ALL rows, no exception)

#### Scenario: CUPS contratado (happy path — unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "878001"
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- WHEN the detector processes that row
- THEN no error is generated for that row

#### Scenario: CUPS no contratado para la entidad (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "999999"
- AND the pair ("EMSS18", "999999") does NOT exist in the contracted-procedures chain
- AND `Responsable Cierra Facturar` is NOT in `FACTURADORES_URGENCIAS`
- WHEN the detector processes that row
- THEN an error is generated with `problema` = "CUPS 999999 no contratado para EMSS18, EMSSANAR ESS E.S.S."

#### Scenario: CUPS no contratado pero responsable urgencias lo exime

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND `Responsable Cierra Facturar` = "ARIAS CULCHA ANGIE CAROLINA" (in `FACTURADORES_URGENCIAS`)
- AND "965201" exists in `nota_hoja id=1` procedures
- WHEN the detector processes that row
- THEN no error is generated — the urgencias exception applies

#### Scenario: CUPS no contratado + responsable urgencias + CUPS no está en nota_hoja id=1

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "999999"
- AND `Responsable Cierra Facturar` = "ESPAÑA DIAZ LORENY ALEJANDRA" (in `FACTURADORES_URGENCIAS`)
- AND "999999" does NOT exist in `nota_hoja id=1` procedures
- WHEN the detector processes that row
- THEN an error IS generated — the exception does not apply because the CUPS is not in nota_hoja id=1

#### Scenario: Responsable urgencias con nota_hoja id=1 vacía

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND `Responsable Cierra Facturar` = "MEZA FERNANDEZ CARLOS OMAR" (in `FACTURADORES_URGENCIAS`)
- AND `nota_hoja id=1` has NO linked procedures (empty set)
- WHEN the detector processes that row
- THEN an error is generated — empty set means nothing is valid, failing closed

#### Scenario: Columna Responsable Cierra Facturar no existe en Excel

- GIVEN the Excel does NOT contain "Responsable Cierra Facturar" (`indices["responsable_cierra"]` is `None`)
- AND a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND ("EMSS18", "965201") does NOT exist in `pares_validos`
- WHEN the detector processes that row
- THEN an error is generated — missing column means the exception branch is skipped, standard validation applies

#### Scenario: Código de entidad no existe en DB (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "NONEXIST" and `Código` = "878001"
- AND "NONEXIST" does not appear in `eps_contratado.cod_contrato`
- WHEN the detector processes that row
- THEN an error is generated with message including "CUPS 878001 no contratado para NONEXIST"

#### Scenario: CUPS no existe en procedimiento (unchanged)

- GIVEN a row with `Código` = "INVALID99" and `Cód Entidad Cobrar` = "EMSS18"
- AND "INVALID99" does not appear in `procedimiento.cups`
- WHEN the detector processes that row
- THEN an error is generated indicating the CUPS is not contracted

#### Scenario: DB no disponible (unchanged)

- GIVEN the PostgreSQL database is unreachable (connection error)
- WHEN the detector is called
- THEN it returns an empty list `[]`
- AND logs a warning — no crash

#### Scenario: Columnas faltantes (unchanged)

- GIVEN the Excel does not contain column `Cód Entidad Cobrar` (indices key `codigo_entidad_cobrar` is `None`)
- OR column `Código` (indices key `codigo` is `None`)
- WHEN the detector is called
- THEN it returns an empty list `[]`

#### Scenario: Tolerancia a formato (espacios, mayúsculas) (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "  emss18  " and `Código` = "  878001  "
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- WHEN the detector processes that row
- THEN the values are normalized via `.strip().upper()` before comparison
- AND no error is generated for that row
