# Delta for Procedimientos Contratados

## MODIFIED Requirements

### Requirement: Detect CUPS sin contrato

The system **MUST** verify that each invoice row's `Cód Entidad Cobrar` + `Código` pair exists in the contracted-procedures chain: `eps_contratado → eps_nota → nota_hoja → notas_tecnicas → procedimiento`.

**Exception 1 (Urgencias)**: When `Responsable Cierra Facturar` is in `FACTURADORES_URGENCIAS`, validation **MUST** use procedures linked to `nota_hoja id=1` ("OTRAS EPB SOLO URGENCIAS").

**Exception 2 (CAP + ESS118)**: When `Número Factura` starts with `"CAP"` AND `cod_entidad = "ESS118"`, validation **MUST** use procedures linked to `nota_hoja id=3` ("EMSSANAR CAPITA").

**Exception 3 (CAP + EPSS41)**: When `Número Factura` starts with `"CAP"` AND `cod_entidad = "EPSS41"`, validation **MUST** use procedures linked to `nota_hoja id=2` ("NUEVA EPS CAPITA").

(Previously: Only exception 1 existed. CAP invoices were validated via standard contractual chain, producing false positives.)

#### Scenario: CUPS contratado (happy path — unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "878001"
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- AND `Número Factura` does NOT start with "CAP"
- AND `Responsable Cierra Facturar` is NOT in `FACTURADORES_URGENCIAS`
- WHEN the detector processes that row
- THEN no error is generated

#### Scenario: CUPS no contratado para la entidad (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "999999"
- AND the pair ("EMSS18", "999999") does NOT exist in the contracted-procedures chain
- AND `Responsable Cierra Facturar` is NOT in `FACTURADORES_URGENCIAS`
- AND `Número Factura` does NOT start with "CAP"
- WHEN the detector processes that row
- THEN an error with `problema` = "CUPS 999999 no contratado para EMSS18, EMSSANAR ESS E.S.S."

#### Scenario: CUPS no contratado pero responsable urgencias lo exime (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND `Responsable Cierra Facturar` = "ARIAS CULCHA ANGIE CAROLINA" (in `FACTURADORES_URGENCIAS`)
- AND "965201" exists in `nota_hoja id=1` procedures
- WHEN the detector processes that row
- THEN no error — the urgencias exception applies

#### Scenario: CUPS no contratado + responsable urgencias + CUPS no está en nota_hoja id=1 (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "999999"
- AND `Responsable Cierra Facturar` = "ESPAÑA DIAZ LORENY ALEJANDRA" (in `FACTURADORES_URGENCIAS`)
- AND "999999" does NOT exist in `nota_hoja id=1` procedures
- WHEN the detector processes that row
- THEN an error IS generated

#### Scenario: Responsable urgencias con nota_hoja id=1 vacía (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND `Responsable Cierra Facturar` = "MEZA FERNANDEZ CARLOS OMAR" (in `FACTURADORES_URGENCIAS`)
- AND `nota_hoja id=1` has NO linked procedures
- WHEN the detector processes that row
- THEN an error is generated — empty set fails closed

#### Scenario: Columna Responsable Cierra Facturar no existe (unchanged)

- GIVEN the Excel does NOT contain "Responsable Cierra Facturar" (`indices["responsable_cierra"]` is `None`)
- AND a row with `Cód Entidad Cobrar` = "EMSS18" and `Código` = "965201"
- AND ("EMSS18", "965201") does NOT exist in `pares_validos`
- WHEN the detector processes that row
- THEN an error is generated — missing column skips the exception branch

#### Scenario: Código de entidad no existe en DB (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "NONEXIST" and `Código` = "878001"
- AND "NONEXIST" does not appear in `eps_contratado.cod_contrato`
- WHEN the detector processes that row
- THEN an error with message including "CUPS 878001 no contratado para NONEXIST"

#### Scenario: CUPS no existe en procedimiento (unchanged)

- GIVEN a row with `Código` = "INVALID99" and `Cód Entidad Cobrar` = "EMSS18"
- AND "INVALID99" does not appear in `procedimiento.cups`
- WHEN the detector processes that row
- THEN an error indicating the CUPS is not contracted

#### Scenario: DB no disponible (unchanged)

- GIVEN the PostgreSQL database is unreachable (connection error)
- WHEN the detector is called
- THEN it returns `[]` and logs a warning

#### Scenario: Columnas faltantes (unchanged)

- GIVEN the Excel does not contain "Cód Entidad Cobrar" (indices key `codigo_entidad_cobrar` is `None`)
- OR "Código" (indices key `codigo` is `None`)
- WHEN the detector is called
- THEN it returns `[]`

#### Scenario: Tolerancia a formato (unchanged)

- GIVEN a row with `Cód Entidad Cobrar` = "  emss18  " and `Código` = "  878001  "
- AND the pair ("EMSS18", "878001") exists in the contracted-procedures chain
- WHEN the detector processes that row
- THEN values are normalized via `.strip().upper()` and no error is generated

---

### NEW scenarios for CAP exceptions

#### Scenario: CAP + ESS118 + CUPS en nota_hoja id=3 (happy path)

- GIVEN a row with `Número Factura` = "CAP-2024-001", `Cód Entidad Cobrar` = "ESS118", and `Código` = "878001"
- AND "878001" exists in `nota_hoja id=3` procedures ("EMSSAR CAPITA")
- WHEN the detector processes that row
- THEN no error is generated — the CAP exception applies

#### Scenario: CAP + EPSS41 + CUPS en nota_hoja id=2 (happy path)

- GIVEN a row with `Número Factura` = "CAP-2024-002", `Cód Entidad Cobrar` = "EPSS41", and `Código` = "965201"
- AND "965201" exists in `nota_hoja id=2` procedures ("NUEVA EPS CAPITA")
- WHEN the detector processes that row
- THEN no error is generated — the CAP exception applies

#### Scenario: CAP + ESS118 + CUPS NO en nota_hoja id=3 (validation fails)

- GIVEN a row with `Número Factura` = "CAP-2024-003", `Cód Entidad Cobrar` = "ESS118", and `Código` = "999999"
- AND "999999" does NOT exist in `nota_hoja id=3` procedures
- WHEN the detector processes that row
- THEN an error is generated — the CUPS is not in the capitado set

#### Scenario: CAP + EPSS41 + CUPS NO en nota_hoja id=2 (validation fails)

- GIVEN a row with `Número Factura` = "CAP-2024-004", `Cód Entidad Cobrar` = "EPSS41", and `Código` = "888888"
- AND "888888" does NOT exist in `nota_hoja id=2` procedures
- WHEN the detector processes that row
- THEN an error is generated — the CUPS is not in the capitado set

#### Scenario: CAP + ESS118 + nota_hoja id=3 vacía (fails closed)

- GIVEN a row with `Número Factura` = "CAP-2024-005", `Cód Entidad Cobrar` = "ESS118", and `Código` = "878001"
- AND `nota_hoja id=3` has NO linked procedures (empty set)
- WHEN the detector processes that row
- THEN an error is generated — empty set means nothing is valid

#### Scenario: Factura NO-CAP + ESS118 (no exception applies)

- GIVEN a row with `Número Factura` = "FAC-2024-001", `Cód Entidad Cobrar` = "ESS118", and `Código` = "878001"
- AND the pair ("ESS118", "878001") does NOT exist in the contracted-procedures chain
- AND `Responsable Cierra Facturar` is NOT in `FACTURADORES_URGENCIAS`
- WHEN the detector processes that row
- THEN an error is generated — standard validation without exceptions
