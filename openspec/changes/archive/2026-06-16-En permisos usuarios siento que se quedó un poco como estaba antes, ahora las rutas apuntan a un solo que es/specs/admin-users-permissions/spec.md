# Delta for Admin — Usuarios y Permisos (Unificación /procesar + Cronogramas)

## ADDED Requirements

### R12: New Permisos in ALLOWED_PERMISOS

`ALLOWED_PERMISOS` MUST include `procesar`, `procesar:write`, `cronograma_bacteriologas`, and `cronograma_urgencias`. The old area-specific permisos `odontologia`, `urgencias`, and `odontologia_equipos_basicos` SHALL be removed.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| New permisos accepted | `procesar` in user permisos list | `update_user("u", {"permisos": ["procesar"]})` | accepted |
| Cronograma bacteriologas | `cronograma_bacteriologas` in list | `update_user("u", {"permisos": ["cronograma_bacteriologas"]})` | accepted |
| Cronograma urgencias | `cronograma_urgencias` in list | `update_user("u", {"permisos": ["cronograma_urgencias"]})` | accepted |
| Old perm rejected | `odontologia` in list | `update_user("u", {"permisos": ["odontologia"]})` | returns `(False, "Permiso inválido: odontologia")` |
| Mutual exclusion | both `procesar` and `procesar:write` | `update_user("u", {"permisos": ["procesar", "procesar:write"]})` | returns `(False, msg)` |

### R13: Permission Migration (Backfill)

`_load_users()` MUST migrate legacy permisos: old `odontologia` → `procesar`, old `urgencias` → `procesar`, old `odontologia_equipos_basicos` → `procesar`. Legacy `equipos_basicos` SHALL remain unchanged.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Migrate odontologia | user has `"odontologia"` | migration runs | replaced with `"procesar"` |
| Migrate urgencias | user has `"urgencias"` | migration runs | replaced with `"procesar"` |
| Migrate odontologia_equipos_basicos | user has permiso | migration runs | replaced with `"procesar"` |
| Preserve equipos_basicos | user has `"equipos_basicos"` | migration runs | preserved unchanged |

### R14: DEFAULT_USERS Updated

`DEFAULT_USERS` includes `admin` (`"*"`), `procesar` (`["procesar"]`), and `procesar_full` (`["procesar", "control_urgencias", "facturas_abiertas"]`).

### R15: PERMISO_MUTUAL_EXCLUSION

`procesar` / `procesar:write` pair added to `PERMISO_MUTUAL_EXCLUSION`.

### R16: ALL_PERMISOS (Frontend) Updated

Frontend `ALL_PERMISOS` includes the new values: `procesar` (label: "Procesar (lectura)"), `procesar:write` (label: "Procesar (modificar)"), `cronograma_bacteriologas` (label: "Cronograma Bacteriólogas"), `cronograma_urgencias` (label: "Cronograma Urgencias").

## MODIFIED Requirements

### R6: Checkbox Permisos Template

The permisos checkboxes MUST use the new unified list. Old area-specific checkboxes (`odontologia`, `urgencias`) replaced by `procesar` and `procesar:write`. New cronograma checkboxes added. Labels updated: `equipos_basicos` → "Ordenado y Facturado". Write variants added for `control_urgencias:write` and `facturas_abiertas:write`.

## REMOVED Requirements

- Old `odontologia` permiso (no longer in ALLOWED_PERMISOS)
- Old `urgencias` permiso (no longer in ALLOWED_PERMISOS)
- Old `odontologia_equipos_basicos` permiso (no longer in ALLOWED_PERMISOS)

---

## Acceptance Criteria (Additions)

- [ ] `procesar`, `procesar:write`, `cronograma_bacteriologas`, `cronograma_urgencias` in `ALLOWED_PERMISOS`
- [ ] `odontologia`, `urgencias`, `odontologia_equipos_basicos` removed from `ALLOWED_PERMISOS`
- [ ] `PERMISO_MUTUAL_EXCLUSION` includes `procesar`/`procesar:write`
- [ ] `_load_users()` migration maps old perms → `procesar`
- [ ] `DEFAULT_USERS` updated with new users
- [ ] Frontend ALL_PERMISOS reflects new values
