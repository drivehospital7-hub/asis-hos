# Delta for intramural-bacteriologas-cronograma

## ADDED Requirements

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

## Non Goals

- This change does NOT add or modify any UI, route, or API behavior
- This change does NOT modify the cronograma data, `get_turno_del_dia()`, or the siglas filter logic
- This change does NOT affect odontología, urgencias, or equipos_basicos detectors
- This change does NOT modify `FACTURADORES_URGENCIAS`, `EXCEPCIONES_BACTERIOLOGA`, or any existing constant
- The exception is hardcoded to code "02217" only — no dynamic configuration

## Open Questions

None.
