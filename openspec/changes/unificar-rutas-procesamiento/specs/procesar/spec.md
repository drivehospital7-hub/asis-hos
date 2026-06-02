# Procesar Specification

## Purpose

Unified processing endpoint that replaces the separate POST handlers for urgencias, odontología, and odontología-equipos-básicos. Accepts an Excel file plus optional domain-specific parameters, dispatches to the correct detection pipeline via the `area` parameter, and returns JSON with detected problems.

---

## Requirements

### R1: Unified POST — Happy Path

`POST /procesar/` MUST accept an Excel file, validate it, run the detection pipeline for the requested `area`, and return JSON with detected problems.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Urgencias file | valid `.xlsx` with urgencias data, `area=urgencias` | POST with file | 200; JSON response with grouped errors, `status: "success"` |
| Odontología file | valid `.xlsx` with odontología data, `area=odontologia` | POST with file | 200; JSON response with grouped errors, `status: "success"` |
| Equipos Básicos file | valid `.xlsx` with EB data, `area=equipos_basicos` | POST with file | 200; JSON response with grouped errors, `status: "success"` |
| No file | empty request body | POST | 400; `status: "error"`, `errors: ["Debes seleccionar un archivo"]` |
| Invalid extension | `.csv` file | POST | 400; `status: "error"`, `errors` with validation message |
| Missing required columns | file lacks expected headers | POST | 200; `status: "error"`, `errors` with list of missing columns, `missing_columns` array |
| Unauthenticated | no active session | POST | 401; `status: "error"`, `errors: ["No autenticado"]` |
| No permiso | user without any qualifying permiso | POST | 403; `status: "error"`, `errors: ["Permiso denegado"]` |

### R2: Odontología Parameters

`POST /procesar/` MUST accept `profesional`, `dias_seleccionados`, `todos_profesionales_dias`, and `validar_centro_costo` form fields when `area=odontologia` and pass them to `detect_problems_only`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Single professional + days | `area=odontologia`, `profesional=DOC001`, `dias_seleccionados=1,3,5` | POST | `detect_problems_only` called with `profesional="DOC001"`, `dias=[1,3,5]` |
| All professionals from UI | `area=odontologia`, `todos_profesionales_dias={"DOC001":[1,2],"DOC002":[3,4]}` | POST | `detect_problems_only` called with `todos_profesionales_dias` dict |
| Centro costo validation | `area=odontologia`, `validar_centro_costo=on` | POST | `detect_problems_only` called with `validar_centro_costo=True` |
| No parameters | `area=odontologia`, no profesional/dias params | POST | `detect_problems_only` called with defaults (`profesional=""`, `dias=[]`, etc.) |

### R3: Response Format

The endpoint MUST return the project's standard JSON envelope: `{"status": "success"|"error", "data": {...}, "errors": [...]}`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Success status | processing succeeds with problems | POST | `"status": "success"`, `"errors": []`, `"data.errores"` is array of grouped errors |
| Error status | no file or invalid input | POST | `"status": "error"`, `"errors"` with messages, `"data": {}` |
| Error grouping | multiple problem types found | POST | errors grouped by `tipo_error`, each with `tipo`, `cantidad`, `facturas` |
| Column list included | success response | POST | `"data.columnas"` contains 6 column names for the frontend table |

### R4: Rate Limiting

`POST /procesar/` MUST apply `@rate_limit(1, 120, admin_exempt=True)` — at most 1 POST per 120-second sliding window per session. Admin users (permiso `*`) are exempt.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| First request | no prior POST in window | POST | 200; request processed |
| Rate exceeded | session has 1 POST < 120s ago | 2nd POST | 429; `"errors": ["Demasiadas solicitudes. Espere {N} segundos."]` |
| Admin bypass | admin session (`*`) | multiple rapid POSTs | 200 each; not rate-limited |
| Window expired | 1 POST > 120s ago | POST | 200; old timestamp pruned |

### R5: Permission Guard

`POST /procesar/` MUST require `permiso_requerido("urgencias", "odontologia", "odontologia_equipos_basicos")` — any one of the three suffices.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Urgencias user | session has `urgencias` | POST | 200 |
| Odontología user | session has `odontologia` | POST | 200 |
| EB user | session has `odontologia_equipos_basicos` | POST | 200 |
| No qualifying permiso | session has only `control_urgencias` | POST | 403 |
| Admin bypass | session has `*` | POST | 200 (admin passes any permiso check) |

### R6: Concurrency Semaphore

Processing MUST acquire the global `threading.Semaphore` (max 3 concurrent tasks). Timeout after 30 seconds returns 503.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Under capacity | ≤ 3 tasks active | POST | semaphore acquired; processing proceeds |
| At capacity | 3 tasks active | POST | 503 after 30s timeout |
| Exception safety | task raises exception | POST | semaphore released in `finally` |

---

## Non-Functional Requirements

- **Logging**: Each processing request SHALL log area, filename, and profesional (when applicable).
- **JSON-only**: POST handler SHALL return JSON for all responses — never render an HTML template.
- **Temp cleanup**: Temp Excel files SHALL be cleaned up in a `finally` or equivalent block before returning, even on error.
- **Response consistency**: Error grouping format SHALL match the existing urgencias/odontologia POST handlers output (grouped by `tipo_error`, limited to 50 items per group).
