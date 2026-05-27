# Intramural — Detección de Facturas

## Purpose

Nueva área "Intramural" para upload de Excel de facturación médica y detección de problemas usando **únicamente** reglas transversales existentes (decimales, tipo documento, código entidad, tipo usuario). Sin reglas de negocio propias del área.

---

## Requirements

### R1: Blueprint GET `/intramural/` — React Shell

The system MUST expose `GET /intramural/` decorated with `@permiso_requerido("intramural")` that renders the React shell template (SPA entry point).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| GET renders Shell | authenticated user with `intramural` permiso | `GET /intramural/` | renders `intramural.html` (React SPA) with title "Intramural" |

### R2: Blueprint POST `/intramural/` — Upload + Detección

The system MUST expose `POST /intramural/` decorated with `@permiso_requerido("intramural")`. It SHALL validate the uploaded file (Excel format, single sheet), extract column indices, and call `detect_all_problems_intramural()`. The response MUST follow the standard `{status, data, errors}` format.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid Excel uploaded | authenticated user, valid `.xlsx` file | `POST /intramural/` with file | returns JSON with detection results including transversales problems only |
| Invalid file type | user uploads `.pdf` | `POST /intramural/` | returns 400 `errors: ["Formato no soportado"]` |
| No file provided | POST without file | `POST /intramural/` | returns 400 `errors: ["No se envió ningún archivo"]` |
| Missing required columns | Excel without required columns | `POST /intramural/` | returns detection result; area-specific columns MAY show 0 problems |

### R3: Orquestador `detect_all_problems_intramural()`

The system MUST provide `detect_all_problems_intramural(data_sheet, indices)` in `app/services/intramural/detect_all.py`. It SHALL call ONLY transversales detectores: `detect_decimales`, `detect_tipo_documento_edad`, `detect_codigo_entidad`, `detect_tipo_usuario`. It MUST NOT call any detection from odontologia, urgencias, or equipos_basicos.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| All transversales called | valid data_sheet and indices | `detect_all_problems_intramural(...)` | result includes problems from all 4 transversales detectores |
| No area-specific rules | any Excel | called | result contains ZERO problems from area-specific detectores |
| Empty result | clean Excel | called | returns `{"problemas": [], "totales": {"problemas": 0}, "area": "intramural"}` |

### R4: Normalizador `normalized_rows_intramural()`

The system MUST provide `normalized_rows_intramural(data_sheet, indices)` that returns iterable of dicts with keys matching the transversales column contract (`numero_factura`, `identificacion`, `vlr_subsidiado`, `vlr_procedimiento`, `tipo_identificacion`, `fec_nacimiento`, `codigo_entidad_cobrar`, `tipo_usuario`). Normalization SHALL skip rows with null `numero_factura`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Rows normalized | Excel with 10 valid rows | `normalized_rows_intramural(...)` | returns 10 dicts with required keys |
| Null factura skipped | row with empty Número Factura | `normalized_rows_intramural(...)` | that row omitted from result |
| Missing column | required column not in indices | function with None index | returns empty list (transversales will also return 0 problems) |

### R5: Constantes `app/constants/intramural.py`

The system MUST create `app/constants/intramural.py` with `AREA_INTRAMURAL = "intramural"` and NO business rule constants. All thresholds and validation values SHALL be sourced from `app/constants/base.py`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Area constant defined | module imported | `from app.constants.intramural import AREA_INTRAMURAL` | value is `"intramural"` |
| No business rules | any context | `dir(app.constants.intramural)` | does NOT contain any threshold or validation constants |

### R6: Dispatcher en `exporter.py`

The exporter MUST include a branch for `AREA_INTRAMURAL` that applies only transversales formatting — no area-specific highlight rules.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Dispatch intramural | exporter called with `area="intramural"` | export flow | transversales highlights applied; no odontologia/urgencias/eb rules run |

### R7: Entry Point Vite

The Vite config MUST include `frontend/src/pages/intramural/main.tsx` in `rollupOptions.input`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Build succeeds | Vite config updated | `npx vite build` | output includes `assets/intramural-*.js` |
| Missing entry | config without intramural | build | MUST NOT affect other entries (odontologia, urgencias) |
