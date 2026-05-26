# Tasks: Creación de usuarios con campos de persona

## Change Name

`creacion-usuarios-campos-persona`

## Summary

Add 4 string fields (`primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`) to the JSON user store, session, routes, frontend form/table, and tests. All changes are mechanical additions — no new logic, no refactoring.

## Task List

### Task 1: Backend Store — Extend Schema, CRUD Signatures, and Backfill

**File**: `app/utils/users_store.py`

**Status**: ✅ COMPLETE

**Changes**:
1. ✅ **`DEFAULT_USERS`** (lines 23–58): Add `"primer_nombre": ""`, `"segundo_nombre": ""`, `"apellido_1": ""`, `"apellido_2": ""` to each of the 4 default user dicts.
2. **`_create_default_users()`** (lines 87–104): The dict construction currently uses only `username`, `password_hash`, `rol`, `permisos`. Since `DEFAULT_USERS` now includes the 4 fields, and the loop copies `u["password"]` into a new dict, the person fields must also be copied over. Change to include the 4 fields explicitly:
   ```python
   {
       "username": u["username"],
       "password_hash": generate_password_hash(u["password"]),
       "rol": u["rol"],
       "permisos": u["permisos"],
       "primer_nombre": u.get("primer_nombre", ""),
       "segundo_nombre": u.get("segundo_nombre", ""),
       "apellido_1": u.get("apellido_1", ""),
       "apellido_2": u.get("apellido_2", ""),
   }
   ```
3. **`_load_users()`** (lines 61–70): Add backfill loop after `json.load(f)`. For each user dict, call `user.setdefault(key, "")` for each of the 4 keys. If any key was missing → call `_save_users(users)` at the end to persist the fix.
4. **`check_credentials()`** (lines 127–144): Extend the return dict to include the 4 fields from `u`:
   ```python
   return {
       "username": u["username"],
       "rol": u["rol"],
       "permisos": u["permisos"],
       "primer_nombre": u.get("primer_nombre", ""),
       "segundo_nombre": u.get("segundo_nombre", ""),
       "apellido_1": u.get("apellido_1", ""),
       "apellido_2": u.get("apellido_2", ""),
   }
   ```
5. **`list_users()`** (lines 156–162): Extend each returned dict with the 4 fields:
   ```python
   return [
       {
           "username": u["username"],
           "rol": u["rol"],
           "permisos": u["permisos"],
           "primer_nombre": u.get("primer_nombre", ""),
           "segundo_nombre": u.get("segundo_nombre", ""),
           "apellido_1": u.get("apellido_1", ""),
           "apellido_2": u.get("apellido_2", ""),
       }
       for u in users
   ]
   ```
6. **`create_user()` signature** (line 165–167): Add 4 keyword params with default `""`:
   ```python
   def create_user(
       username: str, password: str, rol: str, permisos: list,
       primer_nombre: str = "",
       segundo_nombre: str = "",
       apellido_1: str = "",
       apellido_2: str = "",
   ) -> tuple:
   ```
7. **`create_user()` body** (line 182–189): Add 4 fields to the appended dict.
8. **`update_user()`** (lines 194–262): In the merge section (before the "Reemplazar en la lista" comment), add handling for person fields:
   ```python
   for key in ("primer_nombre", "segundo_nombre", "apellido_1", "apellido_2"):
       if key in updates:
           updated[key] = updates[key]
   ```

**Verification**:
- `create_user("u", "p", "usuario", ["odonto"], "Ana", "", "López", "")` stores all 4 fields
- `update_user("u", {"primer_nombre": "Ana"})` changes only that field, others preserved
- `update_user("u", {"rol": "admin"})` leaves person fields untouched (no key in updates)
- `check_credentials("u", "p")` return dict has all 4 keys
- `list_users()` returns all 4 fields for every user
- `_load_users()` backfills missing fields for legacy JSON, persists via `_save_users()`
- `get_user()` already returns full dict; person fields are stored in it — no change needed

**Estimated lines changed**: ~55

---

### Task 2: Session — Store Person Fields on Login

**File**: `app/utils/auth_session.py`

**Status**: ✅ COMPLETE

**Changes**:
1. **`do_login()`** (line 30–36): Add 4 lines after `session["permisos"]`:
   ```python
   session["primer_nombre"] = user_data.get("primer_nombre", "")
   session["segundo_nombre"] = user_data.get("segundo_nombre", "")
   session["apellido_1"] = user_data.get("apellido_1", "")
   session["apellido_2"] = user_data.get("apellido_2", "")
   ```
2. **`do_logout()`** (line 39–42): Extend the key list to include the 4 fields:
   ```python
   for key in ("ce_authenticated", "username", "rol", "permisos",
               "primer_nombre", "segundo_nombre", "apellido_1", "apellido_2"):
       session.pop(key, None)
   ```

**Verification**:
- After `do_login(user_data_with_fields)`, session has all 4 keys with correct values
- After `do_logout()`, all 4 keys removed from session
- No breakage: existing session reads of `username`/`rol`/`permisos` still work

**Estimated lines changed**: ~10

---

### Task 3: Routes — Extract Person Fields from Forms

**File**: `app/routes/auth.py`

**Status**: ✅ COMPLETE

**Changes**:
1. **`usuarios_react()`** (lines 78–100): No change needed — `list_users()` already returns the 4 fields as part of the user dicts, and they're passed through `initial_data["usuarios"]` unchanged.
2. **`crear_usuario()`** (lines 211–232): Extract 4 fields from `request.form` and pass to `create_user()`:
   - After `permisos_raw = request.form.getlist("permisos")`, add 4 `.get()` calls
   - Update the `create_user()` call to include them as keyword args:
     ```python
     ok, msg = users_store.create_user(
         username, password, rol, permisos,
         primer_nombre=request.form.get("primer_nombre", ""),
         segundo_nombre=request.form.get("segundo_nombre", ""),
         apellido_1=request.form.get("apellido_1", ""),
         apellido_2=request.form.get("apellido_2", ""),
     )
     ```
3. **`editar_usuario()`** (lines 235–259): Extract 4 fields and add to `updates` dict:
   - After `updates = {"rol": rol, "permisos": permisos_raw}`, add:
     ```python
     for key in ("primer_nombre", "segundo_nombre", "apellido_1", "apellido_2"):
         val = request.form.get(key)
         if val is not None:
             updates[key] = val
     ```
     Using `request.form.get(key)` (without second arg) — returns `None` if the field wasn't submitted, so absent fields are omitted from `updates` and existing values preserved.

**Verification**:
- POST `/auth/usuarios/crear` with 4 person fields → stored via `create_user`
- POST `/auth/usuarios/{u}/editar` with `primer_nombre="Ana"` → only that field updated
- POST `/auth/usuarios/{u}/editar` without person fields → existing fields preserved (form.get returns None, omitted from updates)
- Backward compatible: existing form POSTs without person fields still work

**Estimated lines changed**: ~15

---

### Task 4: Frontend — Add Person Fields to Form and Table

**File**: `frontend/src/pages/usuarios/page.tsx`

**Status**: ✅ COMPLETE

**Changes**:
1. **`Usuario` interface** (line 14–18): Add 4 string fields.
2. **Form state**: Add 4 `useState` hooks for person fields (after line 66):
   ```typescript
   const [formPrimerNombre, setFormPrimerNombre] = useState("");
   const [formSegundoNombre, setFormSegundoNombre] = useState("");
   const [formApellido1, setFormApellido1] = useState("");
   const [formApellido2, setFormApellido2] = useState("");
   ```
3. **`openCreate()`** (line 72–79): Reset the 4 new state variables to `""`.
4. **`openEdit()`** (line 81–93): Set the 4 fields from `user`:
   ```typescript
   setFormPrimerNombre(user.primer_nombre ?? "");
   setFormSegundoNombre(user.segundo_nombre ?? "");
   setFormApellido1(user.apellido_1 ?? "");
   setFormApellido2(user.apellido_2 ?? "");
   ```
5. **`handleSubmit()`** (line 163–182): Append 4 fields to `FormData`:
   ```typescript
   form.append("primer_nombre", formPrimerNombre);
   form.append("segundo_nombre", formSegundoNombre);
   form.append("apellido_1", formApellido1);
   form.append("apellido_2", formApellido2);
   ```
6. **Inline create card form** (after the password input, before Rol label, ~line 234): Add a 2×2 grid with 4 inputs:
   ```tsx
   <div className="grid grid-cols-2 gap-4 mb-4">
     <div>
       <label>Primer Nombre</label>
       <input ... value={formPrimerNombre} onChange={...} />
     </div>
     <div>
       <label>Segundo Nombre</label>
       <input ... value={formSegundoNombre} onChange={...} />
     </div>
     <div>
       <label>Apellido 1</label>
       <input ... value={formApellido1} onChange={...} />
     </div>
     <div>
       <label>Apellido 2</label>
       <input ... value={formApellido2} onChange={...} />
     </div>
   </div>
   ```
7. **Edit modal form** (after the password input, before Rol label, ~line 404): Same 2×2 grid.
8. **Table** (after the "Usuario" `<th>`, line 304): Add `<th>Nombre</th>` header. In the `<td>` for each row (after `{user.username}`, line 315–316), add a `<td>` showing the full name:
   ```tsx
   <td className="py-3 px-4 text-sm" style={{ color: "oklch(0.55 0.04 160)" }}>
     {[user.primer_nombre, user.segundo_nombre, user.apellido_1, user.apellido_2]
       .filter(Boolean).join(" ") || "—"}
   </td>
   ```

**Design decisions from frontend-stack skill**:
- `interface Usuario` — use `interface` not `type` (skill rule: "Use `interface` not `type` for props unless union types")
- Hooks at the top before conditional logic (skill rule)
- One component per file — `UsuariosPage` is already the single export, no change needed
- Tailwind composition: `grid grid-cols-2 gap-4` for the 2×2 layout

**Verification**:
- Create form shows 4 inputs in 2×2 grid
- Edit modal shows 4 inputs pre-filled with user's values
- Table shows combined name column (or "—" if all empty)
- Submit creates/updates user with person fields

**Estimated lines changed**: ~75

---

### Task 5: Tests — Update Existing + Add Person Field Tests

**Files**: `tests/utils/test_users_store.py`, `tests/services/test_auth_routes.py`

**Status**: ✅ COMPLETE

**Changes to `tests/utils/test_users_store.py`**:

1. **`SAMPLE_USERS`** (lines 22–41): Add `""` for all 4 fields to each user.
2. **New test class `TestCreateUserPersonFields`**:
   - `test_create_user_with_person_fields`: Call `create_user` with all 4 fields; verify stored
   - `test_create_user_default_empty`: Call `create_user` without person fields; verify stored as `""`
3. **New test class `TestUpdateUserPersonFields`**:
   - `test_update_person_fields_partial`: Update only `primer_nombre` and `apellido_1`; verify those 2 changed, other 2 preserved
   - `test_update_without_person_fields`: Update rol only; verify person fields untouched
4. **New test class `TestCheckCredentialsPersonFields`**:
   - `test_check_credentials_returns_person_fields`: Verify return dict has all 4 keys
5. **New test class `TestLoadUsersBackfill`**:
   - `test_backfill_legacy_users`: Provide users JSON without person fields; verify `_load_users()` adds `""` and calls `_save_users()`
6. **New test class `TestDefaultUsersHavePersonFields`**:
   - `test_default_users_include_empty_person_fields`: Assert each `DEFAULT_USERS` entry has all 4 keys with `""`
7. **Update `TestCreateUser.test_create_user_success`**: Add `primer_nombre=""` etc. to the existing assertion pattern, or at minimum ensure backward compatibility.

**Changes to `tests/services/test_auth_routes.py`**:

1. **`_seed_users()`** (lines 20–42): Add `""` for all 4 fields to each user.
2. **New scenarios in `TestCrearUsuario`**:
   - `test_create_user_with_person_fields`: POST with 4 fields; verify via `get_user()`
3. **New scenarios in `TestEditarUsuario`**:
   - `test_edit_person_fields`: POST with `primer_nombre="Ana"` and `apellido_1="López"`; verify only those changed
   - `test_edit_without_person_fields`: POST without person fields; verify existing values preserved

**Verification**:
- `pytest tests/utils/test_users_store.py` — all existing + new tests pass
- `pytest tests/services/test_auth_routes.py` — all existing + new tests pass
- No regression: existing test scenarios that don't touch person fields still pass

**Estimated lines changed**: ~90

---

## Dependency Graph

```
Task 1 (store) ──► Task 2 (session)
                      │
                      ▼
                   Task 3 (routes) ──► Task 4 (frontend)
                      │
                      ▼
                   Task 5 (tests)
```

Tasks MUST be applied in order. Each task depends on the output of the previous ones.

---

## Review Workload Forecast

| Task | File(s) | Est. Lines Changed | Complexity | Risk |
|------|---------|-------------------|------------|------|
| T1 | `app/utils/users_store.py` | ~55 | Low | Low — mechanical, pattern repeats 4× |
| T2 | `app/utils/auth_session.py` | ~10 | Low | Low — 4 lines store, 4 lines pop |
| T3 | `app/routes/auth.py` | ~15 | Low | Low — trivial form.get() |
| T4 | `frontend/src/pages/usuarios/page.tsx` | ~75 | Low | Low — mechanical UI additions |
| T5 | `tests/utils/test_users_store.py`, `tests/services/test_auth_routes.py` | ~90 | Low | Low — standard test additions |
| **Total** | **6 files** | **~245** | **Low** | **Low** |

**Budget Risk**: None. All changes are mechanical additions with no new logic, no refactoring, and no architectural changes.

**Chained PRs**: Not needed. The total change is ~245 lines across 6 files with clear dependency ordering. Each task can be reviewed as a single commit.

**Delivery Strategy**: `ask-always` — confirm before applying each task.
