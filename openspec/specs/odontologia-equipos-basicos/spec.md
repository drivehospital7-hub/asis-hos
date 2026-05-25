# Odontología — Equipos Básicos Specification

## Purpose

Equipos Básicos (EB) as an independent module: upload Excel files, detect billing problems, and export processed results. Only accessible to users with the `odontologia_equipos_basicos` permission.

---

## Requirements

### R1: Upload Form

`GET /odontologia-equipos-basicos/` MUST require authentication AND `odontologia_equipos_basicos` in `session["permisos"]`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Has permiso | user with `odontologia_equipos_basicos` | GET | renders upload form (200) |
| No permiso | user without permiso | GET | 403 or redirect to home |
| Unauthenticated | no active session | GET | 401 or redirect to login |

### R2: Upload Process

`POST /odontologia-equipos-basicos/` MUST accept an Excel file, validate it, run EB detection pipeline, and return a processed Excel.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Happy path | valid `.xlsx` file, user has permiso | POST | 200; response includes problem list and download URL |
| No file | empty request body | POST | flash error; re-render form |
| Invalid extension | `.csv` or `.pdf` | POST | flash error; re-render form |
| Unauthenticated | no session | POST | 401 or redirect |
| No permiso | user without `odontologia_equipos_basicos` | POST | 403 |

### R3: Detection Pipeline

On valid POST, the EB detection pipeline MUST run all EB-specific detectors (decimal, duplicate, convenio, cantidades_anomalas, centro_costo) and generate a formatted output Excel with CruceFacturas and Revisión sheets.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Clean file | no problems in data | POST processed | no problems reported; output Excel generated |
| Problems found | file has decimals, duplicates, or invalid convenios | POST processed | problems reported in UI and reflected in output Excel sheets |
| Empty data | file has headers but no data rows | POST processed | flash warning; output generated with headers only |
| Missing required columns | file missing expected headers | POST processed | flash error; output NOT generated |

### R4: Custom Constants

EB constants MUST reside in `app/constants/equipos_basicos.py` (keyset name, required columns, sheet names, allowed patterns).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Constants imported | module initializes | imports from `app.constants.equipos_basicos` | all expected constants are available |
| No hardcoded values | any EB detector | runs | references constants file, not inline values |

### R5: Permission Isolation

A user with `odontologia_equipos_basicos` MUST NOT access `/odontologia/` and vice versa.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| EB user blocked from odontología | session has only `odontologia_equipos_basicos` | GET `/odontologia/` | 403 |
| Odontología user blocked from EB | session has only `odontologia` | GET `/odontologia-equipos-basicos/` | 403 |
| No permission overlap | session has neither permiso | any EB or odontología route | 403 or redirect |

### R6: Export Output

A successful POST MUST return a download path for the processed Excel. The file MUST be accessible only to the user who generated it (or any user with the same permiso).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Download | processed file exists | user accesses download URL | file downloaded as `.xlsx` |
| Unauthorized access | different user | accesses download URL | 403 |

---

## Non-Functional Requirements

- **Security**: Route-level and permiso-level guards on every endpoint. Frontend guards are UX-only; backend is authoritative.
- **File safety**: Input files SHAll be validated for extension and readability before processing.
- **Isolation**: EB module MUST NOT import or depend on `app.services.odontologia.*` code directly.
