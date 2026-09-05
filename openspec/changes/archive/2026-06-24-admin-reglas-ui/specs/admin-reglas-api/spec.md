# admin-reglas-api Specification

## Purpose

RESTful API for managing the rule engine lifecycle: CRUD of rules with automatic versioning on update, exception management, evidence/audit query, and dry-run simulation. All endpoints MUST return the canonical response envelope: `{"status": "success"|"error", "data": {...}, "errors": [...]}`. All mutation endpoints SHALL be transactional — commit or rollback as a single unit.

---

## ADDED Requirements

### R1: List Rules

`GET /api/reglas` MUST return a paginated list of rules. The endpoint SHALL accept optional query parameters `?dominio=`, `?estado=`, and `?activo=` to filter results. Each rule in the list MUST include: `id`, `nombre`, `dominio`, `estado`, `version`, `prioridad`, `severidad`, `activo`, `creado_en`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List all | 10 rules in DB | `GET /api/reglas` | 10 rules returned with envelope `{status: "success", data: [...], errors: []}` |
| Filter by dominio | 5 odontología, 3 urgencias | `GET /api/reglas?dominio=odontologia` | only 5 odontología rules returned |
| Filter by estado | 8 active, 2 draft | `GET /api/reglas?estado=active` | only 8 active rules returned |
| Filter by activo | 7 activo=true, 3 activo=false | `GET /api/reglas?activo=true` | only 7 rules where activo=true returned |
| Empty result | no rules match filter | `GET /api/reglas?dominio=farmacia` | empty list returned, not an error |

### R2: Get Rule Detail

`GET /api/reglas/<id>` MUST return the full rule object including its condition tree (nested JSON, not flat list) and all exceptions. If the rule does not exist, the endpoint SHALL return `status: "error"` with a 404.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Full detail | rule R1 with 4-level condition tree AND > OR > (eq, gt) and 2 exceptions | `GET /api/reglas/1` | nested tree returned as-is, exceptions array included |
| Not found | no rule with id=999 | `GET /api/reglas/999` | `status: "error"`, errors[0] contains "not found" |

### R3: Create Rule

`POST /api/reglas` MUST create a new rule with estado=draft and version=1. The request body SHALL accept: `nombre`, `descripcion`, `dominio`, `severidad`, `prioridad`, `condiciones` (nested tree JSON), `excepciones` (optional array), `parametros`. The response MUST return the created rule with its generated `id`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create with conditions | valid full payload with AND/OR tree | `POST /api/reglas` with JSON body | rule created, id returned, estado=draft, version=1 |
| Create with exceptions | payload includes 2 exceptions | `POST /api/reglas` with exceptions array | rule + 2 exceptions persisted, ids returned |
| Missing required field | payload without `nombre` | `POST /api/reglas` | `status: "error"`, validation error for nombre |
| Invalid dominio | payload with dominio="invalido" | `POST /api/reglas` | `status: "error"`, dominio not in allowed set |

### R4: Update Rule (Auto-Versioning)

`PUT /api/reglas/<id>` SHALL implement auto-versioning: the current active rule MUST be marked as `estado=deprecated` and a NEW rule version SHALL be created with `estado=active` and incremented `version`. The operation SHALL be transactional — if either deprecate or create fails, BOTH MUST roll back. Partial updates SHALL be supported (only changed fields in body). The response MUST return `{old_rule_id, new_rule_id, old_version, new_version}`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Auto-version active rule | R1 v3 active | `PUT /api/reglas/1` with changed `nombre` | R1 v3 → deprecated, R1 v4 → active with new nombre, response contains both ids |
| Partial update | R2 active, only `prioridad` sent | `PUT /api/reglas/2` with `{"prioridad": 5}` | new version created with prioridad=5, other fields unchanged |
| Update deprecated rule | R1 v3 is deprecated | `PUT /api/reglas/1` | `status: "error"` — cannot modify deprecated rule |
| Transaction rollback | DB error after deprecating old | `PUT /api/reglas/1` | old rule remains active, no new version created |
| No changes | PUT with same data as current | `PUT /api/reglas/1` | `status: "success"`, no new version created, same IDs returned |

### R5: Delete Rule (Soft)

`DELETE /api/reglas/<id>` MUST set `estado=retired` (soft delete). Hard deletion SHALL NOT occur. A retired rule SHALL NOT be returned by default queries.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Soft delete | R1 active | `DELETE /api/reglas/1` | R1 now has estado=retired, not in default list |
| Already retired | R2 retired | `DELETE /api/reglas/2` | `status: "error"` — rule already retired |
| Not found | id=999 | `DELETE /api/reglas/999` | `status: "error"`, not found |

### R6: Version History

`GET /api/reglas/<id>/versiones` MUST return all versions of a rule (matched by `rule_base_id`), ordered by version DESC. Each version MUST include `version`, `estado`, `creado_en`, `parametros`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Version list | R1 has 4 versions (v1 retired, v2 deprecated, v3 active, v4 active) | `GET /api/reglas/1/versiones` | 4 versions returned, ordered v4→v3→v2→v1, with estado badges |

### R7: Manual Version Creation

`POST /api/reglas/<id>/versionar` MUST clone the current active version as a new draft with incremented version. The original active version SHALL remain active. Returns the new version id.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Clone as draft | R1 v3 active | `POST /api/reglas/1/versionar` | R1 v4 created as draft, R1 v3 remains active, new version id returned |

### R8: List Exceptions

`GET /api/reglas/<id>/excepciones` MUST list all exceptions for a rule.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| List exceptions | R1 has 3 exceptions | `GET /api/reglas/1/excepciones` | 3 exceptions returned with tipo_efecto, condicion_json, activo |

### R9: Create Exception

`POST /api/reglas/<id>/excepciones` MUST create a new exception for the rule. Body: `{tipo_efecto, condicion_json, activo}`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create exception | valid payload | `POST /api/reglas/1/excepciones` | exception created, id returned, linked to rule |
| Missing tipo_efecto | payload without tipo_efecto | `POST /api/reglas/1/excepciones` | `status: "error"`, validation error |

### R10: Query Evidence

`GET /api/evidencias` MUST query the EvidenceRepository with pagination. Query params: `?regla_id=`, `?factura=`, `?dominio=`, `?desde=`, `?hasta=`, `?limit=`, `?offset=`. Response MUST include the result array AND a `total` count for pagination.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| By regla_id | 200 evidence records for R1 | `GET /api/evidencias?regla_id=1&limit=50` | 50 records returned, total=200 |
| By factura and time range | evidence for factura F001 between dates | `GET /api/evidencias?factura=F001&desde=2026-06-01&hasta=2026-06-07` | matching records only |
| No results | no matching evidence | `GET /api/evidencias?factura=NONEXISTENT` | empty data array, total=0 |
| Default pagination | 500 records, no limit/offset | `GET /api/evidencias` | first 100 records (default limit), total=500 |

### R11: Query Audit Results

`GET /api/auditoria` MUST query audit results with pagination. Query params: `?regla_id=`, `?factura=`, `?resultado=`, `?desde=`, `?hasta=`, `?limit=`, `?offset=`. Paginated response with `total`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| By resultado | 30 MATCH, 70 NO_MATCH | `GET /api/auditoria?resultado=MATCH` | 30 results returned with total=30 |
| Multi-filter | audit for R1, factura F001 | `GET /api/auditoria?regla_id=1&factura=F001` | matching filtered results |
| Paginated | 1000 results | `GET /api/auditoria?limit=20&offset=40` | results 41-60, total=1000 |

### R12: Dry-Run Simulator

`POST /api/reglas/simular` MUST accept a multipart form with an Excel file and optional `rule_id` override. The service SHALL run the engine against the uploaded Excel (first 100 rows) and return a comparison diff: `{"engine_results": [...], "legacy_results": [...], "diff": {...}}`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Full diff | Excel with 50 rows, no rule override | `POST /api/reglas/simular` (multipart) | engine_results and legacy_results both populated, diff shows matches/mismatches |
| Rule override | Excel with rule_id=2 | `POST /api/reglas/simular` with rule_id=2 | only rule 2 simulated |
| Excel > 100 rows | Excel with 500 rows | `POST /api/reglas/simular` | only first 100 rows processed, response notes truncation |
| Invalid file | PDF uploaded instead of Excel | `POST /api/reglas/simular` | `status: "error"`, invalid file format |

---

## Acceptance Criteria

- [ ] All 12 endpoints return the canonical `{"status", "data", "errors"}` envelope
- [ ] PUT auto-versioning is transactional: old deprecated + new created atomically, rollback on any failure
- [ ] No rule is ever hard-deleted — only estado transitions to retired
- [ ] Evidence and audit endpoints support pagination with `total` count
- [ ] Simulator processes max 100 rows and returns both engine + legacy results
- [ ] All error responses include human-readable messages in `errors[]`
