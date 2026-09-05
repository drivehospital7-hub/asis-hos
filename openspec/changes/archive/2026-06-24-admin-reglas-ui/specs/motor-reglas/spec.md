# Delta for motor-reglas

## MODIFIED Requirements

### R5: Versioning and State Machine (with Auto-Versioning)

Rules MUST have a version (integer, auto-incremented on modification). States SHALL follow: draft → active → deprecated → retired. Only `active` rules are evaluated by default. `deprecated` rules MAY be evaluated when overridden by an active exception.
(Previously: Modification to an active rule creates a new version; the previous version is archived)

**AUTO-VERSIONING**: When the REST API (`PUT /api/reglas/<id>`) modifies an active rule, the system SHALL atomically: (1) mark the current version as `deprecated`, (2) create a new version with `estado=active` and `version = previous + 1`. Both operations SHALL be transactional — if either fails, both roll back. Partial updates SHALL be supported (only changed fields in body). If no fields have changed, no new version SHALL be created.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Active only | R1 v3 active, R1 v2 archived | resolver loads | only v3 returned |
| Draft activation | R2 draft → set state=active | next evaluation | R2 is now evaluated |
| Deprecation | R3 active → deprecated | next evaluation | R3 excluded unless exception overrides |
| Retired terminal | R4 retired | any action | R4 cannot transition to any other state |
| **Auto-version on PUT** | R1 v3 active, content changed | `PUT /api/reglas/1` | R1 v3 → deprecated, R1 v4 → active, both persisted atomically |
| **Partial update** | R2 active, only `prioridad` sent | `PUT /api/reglas/2` with `{"prioridad": 5}` | new version created with prioridad=5, other fields unchanged |
| **No-op update** | PUT with same data as current | `PUT /api/reglas/1` | no new version created, old stays active |
| **Rollback** | DB error after deprecating old | `PUT /api/reglas/1` | old rule remains active, no orphan version created |
