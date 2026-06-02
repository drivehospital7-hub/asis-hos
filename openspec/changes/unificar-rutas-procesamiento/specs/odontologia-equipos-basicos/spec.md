# Delta for Odontología — Equipos Básicos

## MODIFIED Requirements

### R2: Upload Process (REMOVED)

This requirement is REMOVED. The POST handler at `/odontologia-equipos-basicos/` no longer processes files. All file processing is unified at `POST /procesar/`.
(Previously: `POST /odontologia-equipos-basicos/` accepted Excel, ran EB detection, and returned processed Excel.)

#### Scenario: POST redirected

- GIVEN user with `odontologia_equipos_basicos` permiso
- WHEN POST to `/odontologia-equipos-basicos/`
- THEN response is 410 or redirect to `/procesar/` (frontend already controls the POST target)

### R5: Permission Isolation (MODIFIED)

A user with only `odontologia_equipos_basicos` MUST be able to access `POST /procesar/` (was only accessible to `urgencias` users).
(Previously: user with `odontologia_equipos_basicos` could only access EB-specific routes.)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| EB user on procesar | session has only `odontologia_equipos_basicos` | POST `/procesar/` | 200; file processed |
| EB user blocked from old routes | session has only `odontologia_equipos_basicos` | POST `/odontologia/` | 403 (unchanged) |
| Odontología user blocked from EB | session has only `odontologia` | POST `/odontologia-equipos-basicos/` | 403 (unchanged) |
