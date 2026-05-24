# Tasks: Admin — Usuarios y Permisos

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~545–615 (465–495 new + 5 modified + 65 deleted) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Tasks 1–2 (store + unit tests, ~195 lines)<br>PR 2: Tasks 3–7 (routes + integration tests + templates + auth.js, ~370 lines) |
| Chain strategy | stacked-to-main |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Store layer + unit tests (Tasks 1–2) | PR 1 → main | Foundation. Ships `update_user()`, atomic write, admin protection, and all store tests. Self-contained — existing behavior unchanged. |
| 2 | Routes + integration tests + templates + JS (Tasks 3–7) | PR 2 → main | Full feature. Depends on PR 1 for store functions. Routes, templates, home link, auth.js refactor. |

---

## Dependency Graph

```
Task 1 (Store impl) ──→ Task 2 (Store tests)
     │
     ▼
Task 3 (Routes impl) ──→ Task 4 (Integration tests)
     │
     ▼
Task 5 (Template: usuarios.html)
     │
     ├── Task 6 (Template: home.html)  ← no deps
     └── Task 7 (Refactor: auth.js)     ← no deps
```

---

## Task 1: ✅ `update_user()` + Escritura Atómica + Protección Admin

**Files**: `app/constants/base.py`, `app/utils/users_store.py`
**Depends on**: none
**Risk**: Low
**TDD**: yes (write test expectations in Task 2's file, then implement)

**Acceptance criteria**:
- `update_user(username, updates)` accepts partial dict: password (None/"" → skip), rol, permisos
- `update_user()` rejects invalid rol (must be "admin"|"usuario") → `(False, "Rol inválido")`
- `update_user()` rejects invalid permiso values against `ALLOWED_PERMISOS` → `(False, "Permiso inválido: {value}")`
- `update_user()` rejects self-`*`-removal → `(False, "No puedes remover tus propios permisos de administrador")`
- `update_user()` returns `(False, "Usuario no encontrado")` for non-existent username
- `_save_users()` uses temp file + `os.replace()` for atomic write
- `delete_user("admin")` returns `(False, "No se puede eliminar el usuario admin")`
- `delete_user()` existing behavior for non-admin users unchanged (no regression)

### Implementation notes
- Add `ALLOWED_PERMISOS` as `frozenset` in `app/constants/base.py`. Include: `*`, `odontologia`, `urgencias`, `control_urgencias`, `control_urgencias:write`, `facturas_abiertas`, `facturas_abiertas:write`, `equipos_basicos`, `cruce_facturas`, `derechos`
- `update_user(username, updates)` signature — `updates` is a dict with optional keys: `password`, `rol`, `permisos`
- Self-`*`-removal check: compares current user's `permisos` (from store) against new `permisos`. If `"*"` in current AND not in new → REJECT. This is a store-level validation that applies regardless of session (the session check is at route level, Task 3)
- Atomic write: `_save_users()` write to `USERS_FILE.with_suffix(".json.tmp")` → `os.replace(tmp, USERS_FILE)`. Import `os` at top of file
- `delete_user("admin")`: add guard at the top of `delete_user()` — if username == "admin", return `(False, "No se puede eliminar el usuario admin")` BEFORE trying to find it in the list
- Keep existing `create_user()`, `check_credentials()`, `get_user()`, `list_users()` unchanged

### Test notes
- Unit tests in `tests/utils/test_users_store.py` (Task 2 covers this — write test file first as TDD)
- Mock `_load_users()` to return known data; verify `_save_users()` called with expected data
- Test all spec scenarios from R1 table

---

## Task 2: ✅ Tests Unitarios del Store

**Files**: `tests/utils/test_users_store.py` (NEW)
**Depends on**: Task 1
**Risk**: Low
**TDD**: no (tests already written in TDD phase of Task 1)

**Acceptance criteria**:
- Covers all `update_user()` scenarios: password optional, skip password None/empty, rol-only, permisos-only, non-existent user, self-`*`-removal, invalid permiso, invalid rol
- Covers `delete_user()`: normal user, admin blocked, non-existent user
- Covers atomic write: verify temp file + `os.replace()` pattern used
- Covers `create_user()`: success, duplicate rejection
- Covers `check_credentials()`: valid, invalid password, non-existent user
- Covers error path: corrupt JSON returns `[]` gracefully
- Runs without real filesystem side effects — uses `unittest.mock.patch` for `_load_users()` and `_save_users()`

### Implementation notes
- Follow existing test patterns: pytest + `unittest.mock.patch`
- Mock `_load_users()` to return a controlled list of dicts
- For atomic write test: mock `open()` and `os.replace()`, verify temp file write + replace call
- For corrupt file error path: test that `_load_users()` returns `[]` when JSON is invalid (this is existing behavior)
- Test file structure matches `tests/utils/` — same pattern as `tests/utils/test_input_data.py`

### Test notes
- Pure unit tests — no Flask app needed, no `app_client` fixture
- Each test function tests ONE scenario
- Test data: use a small fixed list of 2-3 users (admin, odontologia)

---

## Task 3: ✅ Endpoints Editar + Eliminar en `routes/auth.py`

**Files**: `app/routes/auth.py`
**Depends on**: Task 1
**Risk**: Medium
**TDD**: yes (write integration test expectations first, then implement)

**Acceptance criteria**:
- `POST /auth/usuarios/<username>/editar` decorated with `@admin_requerido`
  - Reads form: username (hidden), password (optional), rol, permisos[]
  - Route-level self-protection: if `session["username"] == username` AND `"*"` not in new permisos → flash error + redirect (rejects BEFORE calling store)
  - Delegates to `users_store.update_user(username, {...})`
  - Flashes result, redirects to `auth.listar_usuarios`
- `POST /auth/usuarios/<username>/eliminar` decorated with `@admin_requerido`
  - Route-level guard: if `username == "admin"` → flash error + redirect (rejects BEFORE calling store)
  - Delegates to `users_store.delete_user(username)`
  - Flashes result, redirects to `auth.listar_usuarios`
- Both endpoints pass through `@admin_requerido` — non-admin gets 403, unauthenticated gets 401

### Implementation notes
- Endpoint function names: `editar_usuario(username)`, `eliminar_usuario(username)` — match existing Spanish naming
- `@admin_requerido` is already imported: `from app.utils.auth import admin_requerido`
- Password field: `request.form.get("password", "")` — passes through to `update_user()` as-is. If empty string, store skips hash update
- Permisos: `request.form.getlist("permisos")` — same pattern as `crear_usuario()`
- Rol: `request.form.get("rol", "usuario")` — validate it's "admin" or "usuario"
- Response format: Flash + `redirect(url_for("auth.listar_usuarios"))` — NOT JSON
- Self-protection check is at route level (BEFORE calling store): compare `session.get("username")` with `username` from URL
- For edit route: pass `session_username=session.get("username")` to template so modal can do frontend self-check

### Test notes
- Integration tests in `tests/services/test_auth_routes.py` (Task 4 covers this)
- Test all R2 and R3 scenarios from spec: success, password empty, self-edit remove `*`, non-existent user, unauthenticated, non-admin

---

## Task 4: ✅ Tests de Integración de Rutas Auth

**Files**: `tests/services/test_auth_routes.py` (NEW)
**Depends on**: Task 3
**Risk**: Medium
**TDD**: no (tests already written in TDD phase of Task 3)

**Acceptance criteria**:
- Covers login scenarios: success, wrong password, missing fields, already authenticated redirect
- Covers logout: clears session, redirects
- Covers create user: valid, duplicate username, missing fields, admin auto-`*`-assign
- Covers edit user: password update, password empty (no change), rol change, permisos change, non-existent user
- Covers edit user self-protection: admin edits own user removing `*` → flash error, changes NOT saved
- Covers delete user: normal user deleted, admin blocked, non-existent user
- Covers unauthenticated access (no session) to all admin routes → 401 or redirect
- Covers non-admin access (session without `*`) → 403 or redirect

### Implementation notes
- Use `app_client` fixture from `tests/conftest.py` (same as `test_control_errores_integration.py`)
- Set session directly: `with app_client.session_transaction() as sess: sess["ce_authenticated"] = True; sess["permisos"] = ["*"]; sess["username"] = "admin"`
- For edit/delete: `app_client.post("/auth/usuarios/test_user/editar", data={...})`
- Assert flash messages via `response.headers` or follow redirect and check body
- Follow same pattern as `test_control_errores_integration.py` — use `app_client` directly, no mocking needed for store (tests real store with `instance/users.json` — but isolate with tmp path or mock)
- IMPORTANT: mock or temp-path the `USERS_FILE` to avoid polluting real `instance/users.json`. Use `patch("app.utils.users_store.USERS_FILE", tmp_path / "users.json")` at module level

### Test notes
- Integration tests use real Flask app + test client
- Need to handle `@admin_requerido` properly — set session with `["*"]`
- Test unauthenticated by NOT setting session keys
- Test non-admin by setting `permisos = ["odontologia"]` (no `*`)

---

## Task 5: ✅ Template `usuarios.html` — Modal, Botones, Fix Checkbox

**Files**: `app/templates/usuarios.html`, `app/routes/auth.py` (minor: pass session_username to template)
**Depends on**: Task 3 (route names for `url_for`)
**Risk**: Medium
**TDD**: no

**Acceptance criteria**:
- Edit modal (initially hidden) with form: username readonly, password optional (placeholder), rol select, permisos checkboxes
- Edit modal pre-fills from data-attributes on the `<tr>` — JS reads `JSON.parse(tr.dataset.user)`
- Click "Editar" on any row → opens modal with that user's data
- Click "Cancelar" or overlay → closes modal, no submit
- Delete button per row with `confirm()` dialog
- "admin" row has disabled delete button with `title="No se puede eliminar el usuario admin"`
- Self-edit guard: if editing own user AND unchecking `*`, show extra confirm "¿Estás seguro? Perderás acceso de administrador."
- Checkbox bug fixed: `value="cruce_facturas"` (label "Cruce de Reportes") and `value="equipos_basicos"` (label "Equipos Básicos") are distinct
- Form action set dynamically by JS: `/auth/usuarios/{username}/editar` or `/auth/usuarios/{username}/eliminar`

### Implementation notes
- Add `data-user='{{ usuario | tojson }}'` to each `<tr>` — Jinja2 `tojson` filter escapes properly
- Pass `session_username` to template: `render_template("usuarios.html", usuarios=usuarios, session_username=session.get("username"))`
- Modal HTML structure: use `<div id="editUserModal" class="modal" style="display:none">` — overlay with `.modal-content`
- Modal form method=POST, action="" (set by JS on open)
- JS for modal: `document.querySelectorAll('.btn-edit')` → onclick event reads `tr.closest('tr').dataset.user`
- Delete: `document.querySelectorAll('.btn-delete')` → onclick `confirm("¿Eliminar usuario {username}?")` → if confirmed, create temp form and POST
- Self-edit guard JS: compare `session_username` (from template JS variable `const SESSION_USERNAME = "{{ session_username }}"`) with `data-username`
- Modal checkboxes HTML exactly as spec (lines 197–238 of spec.md)
- Keep existing create user form and `togglePermisos()` function — they are working code

### Test notes
- Manual tests: open modal, fill, submit, verify flash message
- Verify "admin" row delete button is disabled with correct tooltip
- Verify self-edit confirm dialog appears only when editing own user AND `*` is unchecked
- No automated tests for JS behavior (UI template testing not established in this project)

---

## Task 6: ✅ `home.html` Enlace Admin

**Files**: `app/templates/home.html`
**Depends on**: none
**Risk**: Low
**TDD**: no

**Acceptance criteria**:
- When user has `"*"` in `session["permisos"]` → "Usuarios" link visible linking to `url_for('auth.listar_usuarios')`
- When user does NOT have `"*"` → no "Usuarios" link visible
- Link follows same card style as existing area cards in `home.html`

### Implementation notes
- Add inside `<section class="home__areas">` block, before or after existing cards
- Use `{% if '*' in permisos %}` — same pattern as all existing cards
- Use `url_for('auth.listar_usuarios')` — route already exists
- Match exact card structure: `.area-card` with icon SVG, `.area-card__content` with title "Usuarios" and description text
- Reuse an existing SVG icon or use the "settings/gear" icon for distinction
- Template context `permisos` is already set at line 6: `{% set permisos = session.get('permisos', []) %}`

### Test notes
- No test needed (trivial template change)
- Manual: login as admin → verify link visible; login as user without `*` → verify link hidden

---

## Task 7: ✅ Refactor `auth.js` — Event-Driven

**Files**: `app/static/js/auth.js`
**Depends on**: none
**Risk**: Low
**TDD**: no

**Acceptance criteria**:
- `auth.js` removes all `localStorage.getItem("admin_authenticated")` references
- `auth.js` listens to `ce-auth-change` event instead: `document.addEventListener("ce-auth-change", handler)`
- Event handler reads `e.detail.auth` (boolean) — adapts to current event format from `base.html`
- `.require-auth` elements: add/remove `is-disabled` class based on authenticated state
- `.action-icon--delete` elements: same behavior
- `.editable-cell` elements: same behavior, skip `data-field="estado"` (preserved)
- `window.addEventListener('storage', ...)` removed (redundant with event-driven model)
- Remove `const AUTH_KEY`, `isAuthenticated()`, direct DOMContentLoaded init

### Implementation notes
- Current event format from `base.html` line 93: `{ detail: { auth: authed } }` where `authed` is boolean
- The `initAuthUI()` function content stays the same — just change how it's called (from event handler instead of localStorage)
- Keep CSS class names exactly as-is: `.is-disabled`, `.require-auth`, `.action-icon--delete`, `.editable-cell`
- Keep `.editable-cell` skipping `data-field="estado"` logic
- Move `initAuthUI()` call to inside the event handler
- Also call `initAuthUI()` once on DOMContentLoaded with default false (in case `ce-auth-change` never fires)
- Remove the `window.addEventListener('storage')` block entirely

### Test notes
- Manual: login/logout while on a page that uses `.require-auth` elements (e.g., control_errores.html) — verify elements enable/disable
- Open two tabs, login in one, verify the other tab's UI updates via localStorage event behavior is now gone — this is expected since we're removing cross-tab sync
- The `base.html` inline script also writes to localStorage (`CE_AUTH_KEY`), but `auth.js` no longer reads it — verify no regression
