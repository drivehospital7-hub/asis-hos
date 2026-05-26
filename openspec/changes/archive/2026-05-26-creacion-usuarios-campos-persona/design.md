# Design: Creación de usuarios con campos de persona

## Technical Approach

Extend the JSON user schema with 4 string fields (`primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`) with default `""`. Backfill legacy users on read via `_load_users()`. Frontend renders 4 inputs in a compact 2×2 grid inline below username/password. Session stores fields for display but never uses them for auth. Follows the existing partial-update pattern in `update_user()`.

## Architecture Decisions

### Decision: Person Fields Stored as Flat JSON Keys

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Flat keys on user dict | Simple, no schema change, matches existing pattern | **Chosen** — consistent with current `users.json` layout |
| Nested `persona: {...}` sub-object | Cleaner separation but breaks every existing access pattern | Rejected — unnecessary complexity for 4 fields |

### Decision: Backfill via `_load_users()` (Read-Time)

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Read-time backfill in `_load_users()` | Lazy — no migration script needed; fields appear on next read | **Chosen** — the store auto-repairs on first access after deploy |
| Migration script | Explicit but requires manual execution per env | Rejected — extra operational burden with no benefit for JSON store |

The backfill loop checks each user dict for missing keys (any of the 4), sets them to `""`, and writes the repaired list back via `_save_users()`.

### Decision: No Constants File for Field Names

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Add `USER_PRIMER_NOMBRE = "primer_nombre"` etc. in `constants/base.py` | Centralized string refs but adds indirection with no real benefit | **Rejected** — the keys are only used in one module (`users_store.py`). Adding constants violates YAGNI. |
| Use string literals directly | Simple, local, no import overhead | **Chosen** — keys appear only in `users_store.py` as dict keys and in `auth.py` as `request.form.get()` calls |

### Decision: Inline Form Layout (2×2 Grid Below Username/Password)

The 4 person fields go directly below the username/password row in both the create card and the edit modal. No separate section or accordion — this matches the existing compact pattern.

## Data Flow

```
Create User (React form)
  │  POST /auth/usuarios/crear
  ▼
auth.py: crear_usuario()
  │  request.form.get("primer_nombre", "")
  │  request.form.get("segundo_nombre", "")
  │  request.form.get("apellido_1", "")
  │  request.form.get("apellido_2", "")
  ▼
users_store.create_user(username, password, rol, permisos,
                        primer_nombre, segundo_nombre,
                        apellido_1, apellido_2)
  ▼
users.json  ←  atomic write via _save_users()

Edit User (React modal)
  │  POST /auth/usuarios/{username}/editar
  ▼
auth.py: editar_usuario()
  │  request.form.get("primer_nombre", ...) → updates dict
  ▼
users_store.update_user(username, updates)
  │  partial merge: if key in updates, update it
  ▼
users.json

Login
  │  POST /auth/login
  ▼
check_credentials(username, password)
  │  return dict now includes 4 person fields
  ▼
auth_session.do_login(user_data)
  │  session["primer_nombre"] = user_data["primer_nombre"]
  │  session["segundo_nombre"] = ...
  │  session["apellido_1"] = ...
  │  session["apellido_2"] = ...
  ▼
Session available in templates/React initial_data
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/utils/users_store.py` | Modify | Add 4 fields to schema: `DEFAULT_USERS`, `_create_default_users()`, `create_user()` sig, `update_user()` merge, `check_credentials()` return, `list_users()` output, `_load_users()` backfill |
| `app/utils/auth_session.py` | Modify | `do_login()` stores 4 fields in session; `do_logout()` clears them |
| `app/routes/auth.py` | Modify | `crear_usuario()` extracts 4 fields from form; `editar_usuario()` extracts 4 fields and passes to updates dict; `usuarios_react()` includes fields in `initial_data` |
| `frontend/src/pages/usuarios/page.tsx` | Modify | Extend `Usuario` interface with 4 strings; add 4 inputs in create card + edit modal; add "Nombre Completo" column in table; include fields in `FormData` in `handleSubmit()`; pre-fill in `openEdit()` |
| `tests/utils/test_users_store.py` | Modify | Extend `SAMPLE_USERS` with 4 fields; add tests for person field create/update/backfill |
| `tests/services/test_auth_routes.py` | Modify | Extend `_seed_users()` with 4 fields; add tests for person field create/edit via routes |

## Interfaces / Contracts

### `users_store.create_user()` — Extended Signature

```python
def create_user(
    username: str,
    password: str,
    rol: str,
    permisos: list,
    primer_nombre: str = "",
    segundo_nombre: str = "",
    apellido_1: str = "",
    apellido_2: str = "",
) -> tuple:
```

### `users_store.update_user()` — Extended Partial Update

New accepted keys in `updates` dict: `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`. If absent → field preserved. If present as `str` → stored verbatim (no validation, no regex).

### `check_credentials()` — Extended Return

```python
{
    "username": "admin",
    "rol": "admin",
    "permisos": ["*"],
    "primer_nombre": "Ana",
    "segundo_nombre": "",
    "apellido_1": "López",
    "apellido_2": "",
}
```

### `auth_session.do_login()` — Extended Session

```python
session["primer_nombre"] = user_data["primer_nombre"]
session["segundo_nombre"] = user_data["segundo_nombre"]
session["apellido_1"] = user_data["apellido_1"]
session["apellido_2"] = user_data["apellido_2"]
```

### `Usuario` Interface (Frontend)

```typescript
interface Usuario {
  username: string;
  rol: string;
  permisos: string[];
  primer_nombre: string;
  segundo_nombre: string;
  apellido_1: string;
  apellido_2: string;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `create_user()` with person fields | Mock `_load_users`/`_save_users`, assert 4 fields stored correctly |
| Unit | `update_user()` partial: update person fields only | Assert only specified fields change, others preserved |
| Unit | `update_user()` without person fields in `updates` | Assert existing fields untouched |
| Unit | `check_credentials()` returns person fields | Assert return dict has all 4 keys |
| Unit | `_load_users()` backfill for legacy dicts missing fields | Patch `USERS_FILE` to a JSON without person fields; assert `""` added |
| Unit | `DEFAULT_USERS` and `_create_default_users()` | Assert new users created via defaults have `""` for all 4 |
| Integration | `POST /auth/usuarios/crear` with person fields | Submit form with 4 fields; verify via `get_user()` |
| Integration | `POST /auth/usuarios/{u}/editar` with person fields | Submit partial person field update; verify |
| Frontend | Form renders 4 inputs | Manual/visual; inputs visible in create card and edit modal |
| Frontend | Table shows person name | Manual/visual; column displays full name |

## Migration / Rollout

No migration required. The backfill in `_load_users()` handles legacy `users.json` automatically on first read after deploy. Existing sessions (already logged in users) won't have person fields until they log out and log back in — acceptable tradeoff.

## Open Questions

- None. All decisions are resolved by the spec (proposal + delta spec).
