# Delta for admin-users-permissions

## ADDED Requirements

### R9: `create_user()`, `list_users()`, `check_credentials()` — Person Fields

All store functions MUST handle `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2` (default `""`).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| create_user | new user | `create_user("u","p","usuario",["odonto"],"Ana","","López","")` | 4 fields stored |
| list_users | user has fields | `list_users()` | each dict has all 4 fields |
| check_credentials | valid login | `check_credentials("u","p")` | return dict has all 4 fields |

### R10: Session + Routes — Person Fields

`do_login()` MUST store person fields in session; routes MUST extract fields from `request.form`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Login | user_data with fields | `do_login(user_data)` | `session["primer_nombre"]` etc. set |
| Logout | session has fields | `do_logout()` | fields removed |
| POST crear | admin, form with 4 names | POST `/auth/usuarios/crear` | user stored with all 4 values |
| POST editar | admin, form with name fields | POST with `primer_nombre`, `apellido_1` | user updated |

### R11: Backfill — Default + Legacy Users

`DEFAULT_USERS` MUST include `""` for all 4 fields. `_load_users()` MUST backfill legacy users.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Default users | no `users.json` | first `_load_users()` | each default user has `""` for all 4 |
| Legacy JSON | `users.json` missing fields | `_load_users()` | missing fields added as `""`; existing preserved |

---

## MODIFIED Requirements

### R1: `users_store.update_user()` — Actualización Parcial (extended)

`update_user(username, updates)` MUST soportar actualización parcial: `password` (opcional), `rol`, `permisos`, `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`.
(Previously: accepted password, rol, permisos only)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Update password | existing user, new password | `update_user("u", {"password":"new123","rol":"usuario","permisos":["x"]})` | password hashed; rol+permisos updated |
| Skip password | existing user, password=None | `update_user("u", {"password":None,"rol":"admin","permisos":["*"]})` | existing hash preserved |
| Skip password (empty) | existing user, password="" | `update_user("u", {"password":"","permisos":["y"]})` | existing hash preserved |
| Update rol only | existing user | `update_user("u", {"rol":"admin"})` | only rol changed |
| Update permisos only | existing user | `update_user("u", {"permisos":["*"]})` | only permisos changed |
| **Update person fields** | existing user | `update_user("u", {"primer_nombre":"Ana","apellido_1":"López"})` | those 2 fields changed; rest preserved |
| **Person fields absent** | existing user | `update_user("u", {"rol":"admin"})` | person fields untouched |
| Non-existent user | username not in store | `update_user("ghost", {"rol":"admin"})` | returns `(False, "Usuario no encontrado")` |
| Admin self-remove `*` | admin editing own user | `update_user("admin", {"permisos":["odontologia"]})` | returns `(False, msg)` |
| Admin edit other user | admin editing different user | `update_user("otro", {"permisos":["*"]})` | allowed |
| Invalid permiso | invalid permiso value | `update_user("u", {"permisos":["invalid"]})` | returns `(False, "Permiso inválido: invalid")` |
| Atomic save | any update | `_save_users()` called | temp file → `os.replace()` |
| List unchanged | existing users | any successful update | other users intact |

### R2: `POST /auth/usuarios/<username>/editar` — Editar Usuario (extended)

The system MUST expose `POST /auth/usuarios/<username>/editar` decorated with `@admin_requerido`.
(Previously: same endpoint, now also extracts person fields from form and passes to `update_user`)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Edit success | admin authenticated, valid form | POST with password, rol, permisos | redirect; flash success |
| Edit password empty | admin authenticated | POST with password="" | redirect; password unchanged |
| **Edit with person fields** | admin authenticated | POST with `primer_nombre`, `apellido_1` | fields updated; redirect |
| **Edit without person fields** | admin authenticated | POST without person fields | existing fields preserved |
| Self-edit remove `*` | admin editing own user | POST removing `*` | redirect; flash error |
| Non-existent user | admin, ghost username | POST | flash error; redirect |
| Unauthenticated | no session | POST | 401 or redirect to login |
| Non-admin user | session without `*` | POST | 403 or redirect |

---

## Validation Rules (ADDED)

| Field | Rule | Notes |
|-------|------|-------|
| `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2` | SHOULD accept any string. Default: `""` | No regex required. Stored as-is. |
