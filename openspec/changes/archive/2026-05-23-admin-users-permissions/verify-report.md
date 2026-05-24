# Verification Report: admin-users-permissions

**Change**: Admin — Usuarios y Permisos  
**Mode**: openspec (file-based)  
**Date**: 2026-05-23  
**Verdict**: **PASS WITH WARNINGS**

---

## Completeness

| Task | Status | Evidence |
|------|--------|----------|
| Task 1: `update_user()` + Atomic Write + Admin Protection | ✅ COMPLETE | `users_store.update_user()` implemented, `_save_users()` atomic via tmp+os.replace, `delete_user("admin")` guarded |
| Task 2: Store Unit Tests | ✅ COMPLETE | 22 tests in `tests/utils/test_users_store.py` |
| Task 3: Endpoints Editar + Eliminar | ✅ COMPLETE | Two new POST endpoints in `routes/auth.py` with `@admin_requerido` |
| Task 4: Route Integration Tests | ✅ COMPLETE | 18 tests in `tests/services/test_auth_routes.py` |
| Task 5: Template `usuarios.html` | ✅ COMPLETE | Modal edit, delete buttons, checkbox fix, self-edit guard |
| Task 6: `home.html` Admin Link | ✅ COMPLETE | Conditional card for `'*' in permisos` |
| Task 7: Refactor `auth.js` | ✅ COMPLETE | Event-driven, no localStorage, fallback init |

**7/7 tasks complete.**

---

## Test Results

```
Ran: 304 tests in 37.30s
Result: 304 passed, 0 failed, 0 errors, 0 skipped
```

### Auth-specific tests (22 store + 18 integration = 40 tests)

All 40 new auth tests pass:

- `tests/utils/test_users_store.py` — 22/22 ✅
- `tests/services/test_auth_routes.py` — 18/18 ✅

### Regression tests (264 existing tests)

All 264 existing tests pass — zero regression.

---

## Spec Compliance Matrix

### R1: `users_store.update_user()` — Partial Update

| Scenario | Status | Test Evidence |
|----------|--------|---------------|
| Update password | ✅ PASS | `test_update_password` |
| Skip password (None) | ✅ PASS | `test_skip_password_none` |
| Skip password (empty string) | ✅ PASS | `test_skip_password_empty_string` |
| Update rol only | ✅ PASS | `test_update_rol_only` |
| Update permisos only | ✅ PASS | `test_update_permisos_only` |
| Non-existent user | ✅ PASS | `test_non_existent_user` |
| Admin self-remove `*` | ✅ PASS | `test_admin_self_remove_star` |
| Admin edit other user (add `*`) | ✅ PASS | `test_admin_other_user_add_star_allowed` |
| Invalid permiso | ✅ PASS | `test_invalid_permiso` |
| Atomic save | ✅ PASS | `test_save_users_uses_temp_file_and_replace` |
| User list unchanged post-update | ✅ PASS | `test_user_list_unchanged_after_update` |

**Validation Rules (R1)**:

| Field | Rule | Status |
|-------|------|--------|
| `username` | MUST exist in store | ✅ `"Usuario '{name}' no encontrado"` |
| `password` | If non-empty → hashed; if None/"" → skip | ✅ Lines 195-197, tests 2-3 |
| `rol` | MUST be "admin" or "usuario" | ✅ Line 202, `test_invalid_rol` |
| `permisos` | Each in `ALLOWED_PERMISOS` | ✅ Line 214, `test_invalid_permiso` |
| Self-`*` removal | Session check + `*` in current AND not in new → REJECT | ⚠️ See deviation note |

**⚠️ Deviation (R1 Validation Rules)**: The spec's validation table says self-`*` removal check should include `session["username"] == username`. The implementation at store level rejects **any** `*` removal from any user, not just self. This is **stricter** than spec and matches the design decision (store = pure persistence, route = session check). The route-level check (Task 3) adds the session-scoped protection as specified. Acceptable — defense in depth.

**⚠️ Deviation (Error Message)**: Store returns `"No puedes remover el permiso de administrador de este usuario"` instead of spec's `"No puedes remover tus propios permisos de administrador"`. The route returns the exact spec message. Pragmatic variation since store protects any admin user, not just self.

---

### R2: `POST /auth/usuarios/<username>/editar`

| Scenario | Status | Test Evidence |
|----------|--------|---------------|
| Edit success | ✅ PASS | `test_edit_success` |
| Edit success (password empty) | ✅ PASS | `test_edit_password_empty` |
| Self-edit remove `*` | ✅ PASS | `test_edit_self_remove_star` |
| Non-existent user | ✅ PASS | `test_edit_non_existent_user` |
| Unauthenticated | ✅ PASS | `test_edit_unauthenticated` (401) |
| Non-admin user | ✅ PASS | `test_edit_non_admin` (403/redirect) |

**Response contracts**: ✅ Match spec. Flash + redirect to `auth.listar_usuarios`.

---

### R3: `POST /auth/usuarios/<username>/eliminar`

| Scenario | Status | Test Evidence |
|----------|--------|---------------|
| Delete existing user | ✅ PASS | `test_delete_existing_user` |
| Delete "admin" user | ✅ PASS | `test_delete_admin_blocked` |
| Non-existent user | ✅ PASS | `test_delete_non_existent_user` |
| Unauthenticated | ✅ PASS | `test_delete_unauthenticated` (401) |
| Non-admin user | ✅ PASS | `test_delete_non_admin` (403/redirect) |

**Delete guard rules**: ✅
- `username == "admin"` → `(False, "No se puede eliminar el usuario admin")` at store level
- `username` not found → `(False, "Usuario '{name}' no encontrado")`

---

### R4: Modal de Edición Inline

| Scenario | Status | Evidence |
|----------|--------|----------|
| Open modal pre-filled | ✅ PASS | `openEditModal()` reads data attributes from button, fills form |
| Save via modal | ✅ PASS | POST to `/auth/usuarios/{username}/editar`, flash result |
| Cancel edit | ✅ PASS | Cancel button + overlay click — `closeEditModal()` |
| Modal for "admin" user | ✅ PASS | Extra JS confirm when unchecking `*` on own user |

**Implementation details**:
- Modal ID: `editUserModal` ✅
- Username readonly: `id="edit-username" readonly` ✅
- Password optional: placeholder "Dejar vacío para no cambiar" ✅
- Rol select: usuario/admin options ✅
- Permisos checkboxes: distinct `cruce_facturas`/`equipos_basicos` ✅

---

### R5: Delete Button con Confirmación

| Scenario | Status | Evidence |
|----------|--------|----------|
| Confirm delete | ✅ PASS | `confirm()` dialog → POST on confirmation |
| Cancel delete | ✅ PASS | `e.preventDefault()` on cancel |
| Delete for "admin" | ✅ PASS | Button `disabled`, title `"No se puede eliminar el usuario admin"` |

---

### R6: Fix Checkbox Duplicado

| Scenario | Status | Evidence |
|----------|--------|----------|
| Create form | ✅ PASS | Lines 115-118: `value="cruce_facturas"` / `value="equipos_basicos"` |
| Edit modal | ✅ PASS | Lines 230-237: Same distinct checkboxes |

Both `value="cruce_facturas"` (label "Cruce de Reportes") and `value="equipos_basicos"` (label "Equipos Básicos") are distinct in BOTH forms. Bug fixed.

---

### R7: Enlace Admin en `home.html`

| Scenario | Status | Evidence |
|----------|--------|----------|
| Admin user | ✅ PASS | `{% if '*' in permisos %}` → card visible |
| Regular user | ✅ PASS | No `*` → no card |

Template: `home.html` lines 132-151. Uses `{% set permisos = session.get('permisos', []) %}`. Card matches existing area card pattern.

---

### R8: Refactor `auth.js` — Event-Driven

| Scenario | Status | Evidence |
|----------|--------|----------|
| Auth change event | ✅ PASS | `document.addEventListener('ce-auth-change', handler)` |
| Auth change event (logout) | ✅ PASS | Handler reads `e.detail.auth` (boolean), `false` → hide elements |
| Legacy localStorage | ✅ PASS | No `localStorage.getItem("admin_authenticated")` references |
| CSS classes preserved | ✅ PASS | `.require-auth`, `.action-icon--delete`, `.editable-cell` all handled |
| Fallback init | ✅ PASS | `initAuthUI(false)` on DOMContentLoaded if event never fires |

**⚠️ WARNING (Spec contract mismatch)**: The spec's pseudo-code (lines 299-321) defines the event contract as `e.detail.authenticated` (boolean). The actual `base.html` dispatches `{ detail: { auth: authed } }` (line 93). The implementation correctly reads `e.detail.auth` to match the actual codebase event. The spec contract should be updated to `auth` instead of `authenticated`. No functional impact — `auth.js` works correctly with the actual event.

---

## Design Coherence

| Design Decision | Status | Evidence |
|----------------|--------|----------|
| Modal: data-attributes on `<tr>` | ✅ MATCH | `data-user='{{ usuario | tojson }}'` on `<tr>` + button data attrs |
| Self-protection: 3 layers | ✅ MATCH | Route (session check), Store (block any `*` removal), Frontend (JS confirm) |
| Atomic write: tmp + os.replace | ✅ MATCH | `_save_users()` writes to `.json.tmp` → `os.replace()` |
| POST for delete | ✅ MATCH | `POST /auth/usuarios/{username}/eliminar` |
| `update_user(**kwargs)` | ✅ MATCH | `update_user(username, updates)` with partial dict |
| Password optional | ✅ MATCH | Empty/None → skip hash update |
| `ALLOWED_PERMISOS` in constants | ✅ MATCH | Frozenset in `app/constants/base.py` |

---

## Edge Cases Checked

| Edge Case | Result | Evidence |
|-----------|--------|----------|
| Corrupt users.json | ✅ HANDLED | `_load_users()` returns `[]` on JSONDecodeError, doesn't crash |
| Atomic write crash safety | ✅ HANDLED | Temp file + os.replace pattern; original intact if crash after tmp write |
| Duplicate username (create) | ✅ HANDLED | `(False, "ya existe")` — existing behavior |
| Non-existent user (edit) | ✅ HANDLED | `(False, "no encontrado")` |
| Non-existent user (delete) | ✅ HANDLED | `(False, "no encontrado")` |
| Admin user delete blocked | ✅ HANDLED | Store + Route both guard |
| Admin self-remove `*` (route) | ✅ HANDLED | Route blocks before calling store |
| Admin self-remove `*` (store) | ✅ HANDLED | Store blocks any `*` removal from any user |
| Password empty (edit) | ✅ HANDLED | Existing hash preserved |
| Invalid rol value | ✅ HANDLED | `(False, "Rol inválido")` |
| Invalid permiso value | ✅ HANDLED | `(False, "Permiso inválido: {value}")` |
| Unauthenticated to admin routes | ✅ HANDLED | 401 via `before_request` |
| Non-admin to admin routes | ✅ HANDLED | 403/redirect via `@admin_requerido` |
| Other users intact after update | ✅ HANDLED | `test_user_list_unchanged_after_update` |

---

## Issues

### CRITICAL (0)
None.

### WARNINGS (2)

| # | Component | Issue | Recommendation |
|---|-----------|-------|----------------|
| W1 | `spec.md` (R8) | Event contract says `e.detail.authenticated`, actual `base.html` fires `e.detail.auth`. `auth.js` correctly reads `auth` but spec pseudo-code is misleading. | Update spec lines 299-321 to use `auth` instead of `authenticated`, or align `base.html` event to spec contract. |
| W2 | `spec.md` (R1) | Validation rules table says store-level self-`*`-removal check uses `session["username"]`. Implementation rejects ANY `*` removal (stricter). Design and tasks explicitly state store doesn't check session. | Update spec validation rules to match the actual 2-layer protection: (1) store blocks any `*` removal, (2) route blocks self-session `*` removal. |

### SUGGESTIONS (1)

| # | Component | Suggestion |
|---|-----------|------------|
| S1 | Tests | No explicit integration test for logout route. Add `test_logout_clears_session` to `test_auth_routes.py` for completeness. |

---

## Overall Verdict

**PASS WITH WARNINGS**

- ✅ All 7 tasks complete
- ✅ All 40 new auth tests pass
- ✅ All 264 existing tests pass (zero regression)
- ✅ All spec scenarios covered by passing tests
- ✅ All design decisions implemented correctly
- ✅ Edge cases handled (corrupt JSON, non-existent users, admin protection, atomic write)
- ⚠️ 2 minor spec documentation mismatches (W1, W2) — no functional impact

The implementation is complete and correct. The two warnings are documentation inaccuracies in the spec (`authenticated` vs `auth` in event contract, and validation rules table not matching the actual 2-layer protection design). Neither affects correctness or security of the implementation.

**Ready for archive after spec documentation updates (W1, W2).**
