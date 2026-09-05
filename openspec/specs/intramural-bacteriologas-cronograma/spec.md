# Delta for intramural-bacteriologas-cronograma

No prior spec exists — this is the FULL spec describing current + new behavior.

## MODIFIED Requirements

### Requirement: get_turno_del_dia SHALL accept siglas_filter param

`get_turno_del_dia()` SHALL accept optional `siglas_filter: set[str] | None`:
- `None` (default): filter "CE" OR "PYM" in sigla (current behavior)
- `{"PYM"}`: filter only "PYM"
- `{"CE"}`: filter only "CE"
- `set()`: no filter (return all turnos)

| Scenario | siglas_filter | Sigla | Included? |
|----------|--------------|-------|-----------|
| Default CE/PYM | None | "CE/PYM" | Yes |
| Default CE/PYM | None | "CE" | Yes |
| PYM only | `{"PYM"}` | "PYM/N" | Yes |
| PYM only | `{"PYM"}` | "CE" | No |
| CE only | `{"CE"}` | "CE/N" | Yes |
| CE only | `{"CE"}` | "PYM" | No |
| Bypass | `set()` | "L" | Yes |

### Requirement: detect_bacteriologas_cronograma SHALL accept responsable_cierra

`detect_bacteriologas_cronograma()` SHALL accept `responsable_cierra: dict[str, str]`. For each factura, the system SHALL resolve the siglas filter (or bypass cronograma) based on the responsable's name, case-insensitive via `.upper().strip()`. Fallback to default CE/PYM if responsable not found or dict empty.

#### Scenario: Unknown responsable → default CE/PYM
- GIVEN a factura mapped to an unrecognizable responsable
- WHEN the detector runs
- THEN default CE/PYM filter SHALL apply

#### Scenario: Empty responsable_cierra map → default CE/PYM
- GIVEN `responsable_cierra` is `{}`
- WHEN the detector runs
- THEN all facturas SHALL use default CE/PYM filter

## ADDED Requirements

### Requirement: Chapuel → solo PYM en cronograma

When `responsable_cierra` equals "CHAPUEL CASANOVA ANGIE TATIANA" (case-insensitive), the system SHALL filter cronograma with `siglas_filter={"PYM"}`.

#### Scenario: PYM en cronograma → válida
- GIVEN responsable = "Chapuel Casanova Angie Tatiana"
- AND bacterióloga sigla contains "PYM" (e.g. "PYM/N")
- WHEN the detector validates
- THEN no error SHALL be generated

#### Scenario: Solo CE → error
- GIVEN responsable = "Chapuel Casanova Angie Tatiana"
- AND bacterióloga sigla contains only "CE"
- WHEN the detector validates
- THEN an error SHALL be generated: "no está en el cronograma del día"

### Requirement: FACTURADORES_URGENCIAS → bypass cronograma

When `responsable_cierra` is in FACTURADORES_URGENCIAS (ARIAS CULCHA ANGIE CAROLINA, ESPAÑA DIAZ LORENY ALEJANDRA, MEZA FERNANDEZ CARLOS OMAR, PAEZ YULIETH DANIELA), the system SHALL NOT consult the cronograma. Instead, it SHALL validate the professional directly against PROFESIONALES_URGENCIAS.

#### Scenario: Es BACTERIOLOGA en PROFESIONALES_URGENCIAS → válida
- GIVEN responsable in FACTURADORES_URGENCIAS
- AND `codigo_profesional` exists in PROFESIONALES_URGENCIAS with tipo="BACTERIOLOGA"
- WHEN the detector validates
- THEN no error SHALL be generated

#### Scenario: No existe en PROFESIONALES_URGENCIAS → error
- GIVEN responsable in FACTURADORES_URGENCIAS
- AND `codigo_profesional` is NOT in PROFESIONALES_URGENCIAS
- WHEN the detector validates
- THEN error: "no está en el listado de Urgencias"

#### Scenario: Existe pero no es BACTERIOLOGA → error
- GIVEN responsable in FACTURADORES_URGENCIAS
- AND `codigo_profesional` exists with tipo ≠ "BACTERIOLOGA"
- WHEN the detector validates
- THEN error: "no es una bacterióloga"

### Requirement: Tapia/Ordoñez → solo CE en cronograma

When `responsable_cierra` equals "TAPIA PERDOMO ANYI CATALEYA" or "ORDOÑEZ MEZA SILVIA ELEY" (case-insensitive), the system SHALL filter cronograma with `siglas_filter={"CE"}`.

#### Scenario: CE en cronograma → válida
- GIVEN responsable = "TAPIA PERDOMO ANYI CATALEYA"
- AND bacterióloga sigla contains "CE" (e.g. "CE/N")
- WHEN the detector validates
- THEN no error SHALL be generated

#### Scenario: Solo PYM → error
- GIVEN responsable = "ORDOÑEZ MEZA SILVIA ELEY"
- AND bacterióloga sigla contains only "PYM"
- WHEN the detector validates
- THEN error: "no está en el cronograma del día"

### Requirement: FACTURADORES_URGENCIAS centralized in constants

The system SHALL move FACTURADORES_URGENCIAS from `app/services/odontologia/detect_por_responsable.py` to `app/constants/urgencias.py`. The odontología module SHALL import it from `app.constants.urgencias` and SHALL NOT define it locally.

#### Scenario: Odontología imports from constants
- GIVEN `app/services/odontologia/detect_por_responsable.py`
- WHEN the module references FACTURADORES_URGENCIAS
- THEN it SHALL come from `app.constants.urgencias`
- AND the local definition SHALL be removed

### Requirement: PROFESIONALES_EXCEPTUADOS_CRONOGRAMA SHALL skip cronograma validation

The system SHALL define `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA` as a `frozenset` in `app/constants/urgencias.py` containing professional code `"02217"`.

In `detect_bacteriologas_cronograma()`, after validating that the professional exists in `PROFESIONALES_URGENCIAS` AND has `tipo="BACTERIOLOGA"` (i.e. lines ~289-306), but BEFORE the `responsable_cierra` / `siglas_filter` / cronograma resolution (lines ~308+), the system SHALL check if `codigo_prof` is in `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA`. If found, it SHALL skip the row (`continue`) — no cronograma validation, no error.

This check SHALL execute BEFORE the `FACTURADORES_URGENCIAS` bypass, BEFORE the Chapuel/Tapia/Ordoñez siglas filter, and BEFORE the `get_turno_del_dia()` call. It is the earliest exit after confirming the professional is a BACTERIOLOGA.

#### Scenario: MADROÑERO factura sin estar en cronograma → NO error

- GIVEN `codigo_profesional` = "02217"
- AND the professional IS in `PROFESIONALES_URGENCIAS` with `tipo` = "BACTERIOLOGA"
- AND she is NOT in the cronograma del día
- WHEN `detect_bacteriologas_cronograma` runs
- THEN no error SHALL be generated for this factura
- (She bypasses both the cronograma lookup and the 'no está en el cronograma' check entirely)

#### Scenario: MADROÑERO que sí está en cronograma → NO error (same behavior)

- GIVEN `codigo_profesional` = "02217"
- AND she IS in the cronograma del día
- WHEN `detect_bacteriologas_cronograma` runs
- THEN no error SHALL be generated
- (The exception skip means even if she's scheduled, no error — identical outcome)

#### Scenario: Otra bacterióloga SIN estar en cronograma → SÍ error (regression guard)

- GIVEN `codigo_profesional` = "03374" (MOLINA ALVAREZ KAROL DAYANNA, BACTERIOLOGA)
- AND NOT in `PROFESIONALES_EXCEPTUADOS_CRONOGRAMA`
- AND she is NOT in the cronograma del día
- WHEN `detect_bacteriologas_cronograma` runs
- THEN an error SHALL be generated: "no está en el cronograma del día"
- (The existing validation for non-excepted professionals SHALL remain unchanged)

#### Scenario: Profesional no BACTERIOLOGA → unchanged behavior

- GIVEN `codigo_profesional` = "02249" (PALACIOS PALACIOS FRANCISCO DARWIN, MEDICO)
- WHEN `detect_bacteriologas_cronograma` runs
- THEN the existing error SHALL be generated: "no es una bacterióloga"
- (The exception only applies to professionals who pass the BACTERIOLOGA type check)

#### Scenario: MADROÑERO con FACTURADORES_URGENCIAS como responsable → NO error (both bypasses apply)

- GIVEN `codigo_profesional` = "02217"
- AND `responsable_cierra` maps to a FACTURADORES_URGENCIAS member
- WHEN `detect_bacteriologas_cronograma` runs
- THEN no error SHALL be generated
- (The exception fires first; even if it didn't, the FACTURADORES_URGENCIAS bypass would also skip)

## Acceptance Criteria

1. ✅ Chapuel Casanova → solo bacteriólogas con sigla "PYM" en cronograma son válidas; las de solo "CE" generan error
2. ✅ FACTURADORES_URGENCIAS → bacterióloga válida si está en PROFESIONALES_URGENCIAS con tipo BACTERIOLOGA, sin importar cronograma
3. ✅ Tapia/Ordoñez → solo bacteriólogas con sigla "CE" en cronograma son válidas; las de solo "PYM" generan error
4. ✅ Otros responsables → comportamiento actual (CE o PYM), sin cambios
5. ✅ Responsable vacío o no encontrado → fallback a CE/PYM (current behavior)
6. ✅ FACTURADORES_URGENCIAS definido en `app/constants/urgencias.py`; odontología lo importa de allí
7. ✅ PROFESIONALES_EXCEPTUADOS_CRONOGRAMA → MADROÑERO (02217) bypassa completamente la validación de cronograma, factura cualquier día sin error
