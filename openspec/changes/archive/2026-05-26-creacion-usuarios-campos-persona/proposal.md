# Proposal: Creación de usuarios con campos de persona

## Intent

Add person name fields (`primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`) to the user model so users are identifiable by full name, not just username. The user confirmed: **extend JSON store only** — no DB, no Persona table.

## Scope

### In Scope
- Add 4 fields to `users_store.py` schema: create, update, list, get functions
- Add fields to `auth_session.py` session data (stored, not used for auth)
- Accept fields in `crear_usuario()` / `editar_usuario()` routes
- Add fields to React form (create + edit modal) and table in `page.tsx`
- Add constants for person field names in `constants/` (optional — field keys only)
- Migrate `DEFAULT_USERS` and `instance/users.json` defaults to include empty person fields
- Update existing tests for `users_store` and auth routes

### Out of Scope
- Database migration or ORM model
- Separate Persona entity/table
- Persona search or autocomplete by name
- Persona fields as auth credentials (login remains username+password)

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `admin-users-permissions`: User model extended with 4 mandatory person name fields. Create, edit, list, get operations now include these fields.

## Approach

1. Add field name constants to `app/constants/base.py` (e.g., `USER_PRIMER_NOMBRE`, etc.)
2. Extend `users_store.py`:
   - `DEFAULT_USERS` + `_create_default_users()`: add empty `""` values for 4 fields
   - `create_user()`: accept and store 4 fields
   - `update_user()`: accept and merge 4 fields
   - `list_users()`: include fields in output dict
   - `get_user()`: already returns full dict — no change needed
3. `auth_session.do_login()`: store fields in session
4. `auth.py` routes: extract fields from `request.form` in `crear_usuario()` / `editar_usuario()`
5. React `page.tsx`: add 4 inputs to create form + edit modal, add columns to table, extend `Usuario` interface
6. Update `test_users_store.py` and `test_auth_routes.py` for new field expectations
7. No migration script — existing users auto-populate with `""` on next save

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/base.py` | New | Field name constants (optional) |
| `app/utils/users_store.py` | Modified | Schema + CRUD functions |
| `app/utils/auth_session.py` | Modified | Session data extension |
| `app/routes/auth.py` | Modified | Form handling + validation |
| `frontend/src/pages/usuarios/page.tsx` | Modified | Form fields + table columns |
| `tests/utils/test_users_store.py` | Modified | Expect new fields |
| `tests/services/test_auth_routes.py` | Modified | Expect new fields |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing `users.json` lacks fields | High | Backfill `""` on read in `_load_users()`; atomic write on first save |
| Frontend form gets too long | Low | Fields inline below username/password row; compact layout |
| Legacy `check_credentials` return misses fields | Low | Extend return dict in `check_credentials()` |

## Rollback Plan

Restore `instance/users.json` from backup. Revert files changed in `app/utils/`, `app/routes/`, `frontend/src/pages/usuarios/`. No DB migration to reverse.

## Dependencies

- None

## Success Criteria

- [ ] Create user form has 4 person name fields; values persist in `users.json`
- [ ] Edit user form shows and updates person name fields
- [ ] `list_users()` returns person name fields for each user
- [ ] Table shows full name columns
- [ ] Default users auto-populate with empty `""` values
- [ ] All existing tests pass with new field expectations
- [ ] No regression in login, logout, or permission checks
