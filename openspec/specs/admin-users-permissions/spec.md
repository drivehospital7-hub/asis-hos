# Admin — Usuarios y Permisos

## Purpose

Completar el CRUD de usuarios del sistema de autenticación: agregar edición y eliminación de usuarios vía UI y API, proteger al usuario `admin` de auto-desactivación y eliminación, corregir el checkbox duplicado en el formulario de permisos, exponer el enlace de administración en `home.html`, y refactorizar `auth.js` legacy para usar el sistema moderno de eventos.

---

## Requirements

### R1: `users_store.update_user()` — Actualización Parcial y Validación de Rol Expandida

`update_user(username, updates)` MUST soportar actualización parcial: `password` (opcional), `rol`, `permisos`, `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2`.

`rol` MUST ser validado contra `["admin", "usuario", "medico", "facturador"]`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Update password | existing user, new password | `update_user("u", {"password": "new123", "rol": "usuario", "permisos": ["x"]})` | password hashed and updated; rol+permisos updated |
| Skip password | existing user, password=None | `update_user("u", {"password": None, "rol": "admin", "permisos": ["*"]})` | existing hash preserved; rol+permisos updated |
| Skip password (empty string) | existing user, password="" | `update_user("u", {"password": "", "permisos": ["y"]})` | existing hash preserved; permisos updated |
| Update rol only | existing user | `update_user("u", {"rol": "admin"})` | only rol changed; password+permisos unchanged |
| Update permisos only | existing user | `update_user("u", {"permisos": ["*"]})` | only permisos changed; password+rol unchanged |
| **Update person fields** | existing user | `update_user("u", {"primer_nombre": "Ana", "apellido_1": "López"})` | those 2 fields changed; rest preserved |
| **Person fields absent** | existing user | `update_user("u", {"rol": "admin"})` | person fields untouched |
| Non-existent user | username not in store | `update_user("ghost", {"rol": "admin"})` | returns `(False, "Usuario no encontrado")` |
| Admin self-remove `*` | admin editing own user | `update_user("admin", {"permisos": ["odontologia"]})` with session username="admin" | returns `(False, msg)` — rejects removal of `*` |
| Admin edit other user | admin editing different user | `update_user("otro", {"permisos": ["*"]})` | allowed — `*` added to other user |
| Invalid permiso | user with invalid permiso value | `update_user("u", {"permisos": ["invalid_perm"]})` | returns `(False, "Permiso inválido: invalid_perm")` |
| Atomic save | any update | `_save_users()` called | writes to temp file → `os.replace()`; no truncation on crash |
| User list unchanged post-update | existing users | any successful update | other users in store intact |
| **Update to medico** | existing user | `update_user("u", {"rol": "medico"})` | rol changed to "medico" |
| **Update to facturador** | existing user | `update_user("u", {"rol": "facturador"})` | rol changed to "facturador" |
| **Invalid rol** | existing user | `update_user("u", {"rol": "enfermero"})` | returns `(False, "Rol inválido: debe ser admin, usuario, medico o facturador")` |

### R2: `POST /auth/usuarios/<username>/editar` — Editar Usuario (extended)

The system MUST expose `POST /auth/usuarios/<username>/editar` decorated with `@admin_requerido`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Edit success | admin authenticated, valid form data | POST with password, rol, permisos | redirect `/auth/usuarios`; flash success message |
| Edit success (password empty) | admin authenticated | POST with password="" | redirect; flash success; password unchanged |
| **Edit with person fields** | admin authenticated | POST with `primer_nombre`, `apellido_1` | fields updated; redirect |
| **Edit without person fields** | admin authenticated | POST without person fields | existing fields preserved |
| Self-edit remove `*` | admin editing own user | POST removing `*` from permisos | redirect; flash error; changes not saved |
| Non-existent user | admin, non-existent username | POST to `/auth/usuarios/ghost/editar` | flash error; redirect to `/auth/usuarios` |
| Unauthenticated | no session | POST to endpoint | 401 or redirect to login |
| Non-admin user | session without `*` | POST to endpoint | 403 or redirect |

### R3: `POST /auth/usuarios/<username>/eliminar` — Eliminar Usuario

The system MUST expose `POST /auth/usuarios/<username>/eliminar` decorated with `@admin_requerido`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Delete existing user | admin authenticated, valid user | POST | user removed from store; redirect; flash success |
| Delete "admin" user | admin authenticated | POST `/auth/usuarios/admin/eliminar` | redirect; flash error; user `admin` NOT removed |
| Non-existent user | admin, non-existent username | POST | flash error; redirect to `/auth/usuarios` |
| Unauthenticated | no session | POST | 401 or redirect to login |
| Non-admin user | session without `*` | POST | 403 or redirect |

### R4: Modal de Edición Inline (`usuarios.html`)

The UI MUST provide an edit modal inline (not separate page) that opens when clicking "Editar" on a user row.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Open modal | admin on `/auth/usuarios` | clicks "Editar" on a row | modal opens pre-filled with username (readonly), rol, permisos checkboxes |
| Save via modal | modal open, changes made | clicks "Guardar" | POST to `/auth/usuarios/<username>/editar`; flash result |
| Cancel edit | modal open | clicks "Cancelar" or overlay | modal closes; no changes submitted |
| Modal for "admin" user | modal open for admin | admin sees warning | if unchecking `*`, additional JS confirmation shown |

### R5: Delete Button con Confirmación

Each user row MUST have a delete button. Clicking SHALL show a JS confirmation dialog before submitting.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Confirm delete | admin on `/auth/usuarios` | clicks "Eliminar", confirms | POST to `/auth/usuarios/<username>/eliminar` |
| Cancel delete | admin on `/auth/usuarios` | clicks "Eliminar", cancels | no request sent; user not deleted |
| Delete for "admin" | admin on `/auth/usuarios` | sees "admin" row | delete button disabled; tooltip "No se puede eliminar el usuario admin" |

### R6: Fix Checkbox Duplicado

The permisos form MUST have distinct checkboxes for `cruce_facturas` (label: "Cruce de Reportes") and `equipos_basicos` (label: "Equipos Básicos") in BOTH the create form and the edit modal.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Create form | admin on `/auth/usuarios` | views permisos section | `value="cruce_facturas"` and `value="equipos_basicos"` are distinct checkboxes with correct labels |
| Edit modal | admin editing user | views edit modal | same distinct checkboxes as create form |

### R7: Enlace Admin en `home.html`

`home.html` MUST show a "Usuarios" link to `/auth/usuarios` when the user has `"*"` in `session["permisos"]`. It MUST be hidden for users without `"*"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Admin user | session has `["*"]` | renders home.html | "Usuarios" link visible |
| Regular user | session has `["odontologia"]` | renders home.html | no "Usuarios" link |

### R8: Refactor `auth.js` — Event-Driven

`static/js/auth.js` MUST listen to `ce-auth-change` events instead of reading `localStorage.getItem("admin_authenticated")`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Auth change event | `ce-auth-change` fires with `{auth: true}` | event received | elements with `.require-auth` shown; items with `.action-icon--delete` and `.editable-cell` visibility updated |
| Auth change event (logout) | `ce-auth-change` fires with `{auth: false}` | event received | `.require-auth` elements hidden; delete/edit actions hidden |
| Legacy localStorage | `admin_authenticated` key exists | any auth change | NOT read — only `ce-auth-change` event used |
| CSS classes preserved | any auth change | event received | `.require-auth`, `.action-icon--delete`, `.editable-cell` behavior matches legacy |

### R9: Person Fields in Store (`create_user()`, `list_users()`, `check_credentials()`)

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

### R12: React Usuarios Page — Rol Select con 4 Opciones

The React usuarios page (`frontend/src/pages/usuarios/page.tsx`) role `<select>` MUST list 4 options: Usuario, Admin, Médico, Facturador.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Render create form | admin navigates to `/auth/usuarios` (React view) | inspect create form `<select name="rol">` | options include "Médico" and "Facturador" |
| Render edit modal | admin edits a user | inspect edit modal `<select name="rol">` | options include "Médico" and "Facturador" |

---

## Validation Rules

### R1: `update_user()` — Field Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| `username` | MUST exist in store | `"Usuario no encontrado"` |
| `password` | If non-empty string → MUST be hashed. If `None` or `""` → SKIP (keep existing) | — |
| `rol` | MUST be `"admin"`, `"usuario"`, `"medico"`, or `"facturador"` | `"Rol inválido: debe ser admin, usuario, medico o facturador"` |
| `permisos` | MUST be a list. Each element MUST be in `ALLOWED_PERMISOS` (defined in constants) | `"Permiso inválido: {value}"` |
| Self-`*` removal | Store: si `"*"` está en permisos actuales Y no está en los nuevos → REJECT (protege cualquier usuario, no solo sesión actual) | `"No puedes remover el permiso de administrador de este usuario"` |
| Self-`*` removal (route) | Ruta: si `session["username"] == username` Y `"*"` no está en nuevos permisos → flash error + redirect (antes de llamar al store) | `"No puedes remover tus propios permisos de administrador"` |

### R2: `delete_user()` — Guard Rules

| Scenario | Rule |
|----------|------|
| `username == "admin"` | MUST return `(False, "No se puede eliminar el usuario admin")` |
| `username` not found | MUST return `(False, "Usuario no encontrado")` |

### R3: Person Fields — Data Rules

| Field | Rule | Notes |
|-------|------|-------|
| `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2` | SHOULD accept any string. Default: `""` | No regex required. Stored as-is. |

---

## Acceptance Criteria

- [ ] `users_store.update_user()` implemented with partial update (password optional)
- [ ] `update_user()` rejects any removal of `*` from any user (store-level, session-agnostic)
- [ ] Route `editar_usuario()` adds session-level check: self-removal of `*` is rejected before calling store
- [ ] `update_user()` rejects invalid permisos against allowed list
- [ ] `update_user()` validates rol as `"admin"`, `"usuario"`, `"medico"`, or `"facturador"`
- [ ] `update_user()` accepts `"medico"` and `"facturador"` as valid roles
- [ ] `update_user()` rejects unknown roles with descriptive message including all 4 valid options
- [ ] `create_user()` accepts new roles without error
- [ ] React usuarios page dropdown shows 4 role options (Usuario, Admin, Médico, Facturador)
- [ ] `update_user()` uses atomic write (temp file + `os.replace()`)
- [ ] `POST /auth/usuarios/<username>/editar` creates, validates, calls update, flashes, redirects
- [ ] `POST /auth/usuarios/<username>/eliminar` blocks delete of `admin`, flashes error
- [ ] Both new endpoints require `@admin_requerido`
- [ ] `usuarios.html` has edit modal pre-filled with user data (username readonly)
- [ ] `usuarios.html` has delete button per row with JS confirm
- [ ] `usuarios.html` "admin" row has disabled delete button with tooltip
- [ ] Edit modal warns when unchecking `*` on own user (additional JS confirm)
- [ ] Checkbox `cruce_facturas` (label "Cruce de Reportes") and `equipos_basicos` (label "Equipos Básicos") are distinct
- [ ] `home.html` shows "Usuarios" link only when `"*"` in permisos
- [ ] `auth.js` reads `ce-auth-change` event, not `localStorage`
- [ ] `.require-auth`, `.action-icon--delete`, `.editable-cell` CSS classes retain behavior
- [ ] All tests pass (unit + integration) with no regression
- [ ] `create_user()` stores `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2` (default `""`)
- [ ] `list_users()` returns all 4 person fields per user
- [ ] `check_credentials()` returns all 4 person fields per user
- [ ] `update_user()` merges person fields partially (only fields present in `updates`)
- [ ] `do_login()` stores person fields in session; `do_logout()` removes them
- [ ] `POST /auth/usuarios/crear` extracts person fields from form
- [ ] `POST /auth/usuarios/<username>/editar` extracts person fields from form
- [ ] `DEFAULT_USERS` includes `""` for all 4 person fields
- [ ] `_load_users()` backfills legacy users missing person fields

---

## Response Contracts

### `POST /auth/usuarios/<username>/editar`

```python
# Success → HTTP 302 redirect to /auth/usuarios
flash("Usuario actualizado correctamente", "success")
return redirect(url_for("auth.listar_usuarios"))

# Error → HTTP 302 redirect to /auth/usuarios
flash("No puedes remover tus propios permisos de administrador", "error")
return redirect(url_for("auth.listar_usuarios"))

# Unauthenticated → handled by before_request → 401 or redirect to login
# Unauthorized (non-admin) → handled by @admin_requerido → 403 or redirect
```

### `POST /auth/usuarios/<username>/eliminar`

```python
# Success → HTTP 302 redirect to /auth/usuarios
flash("Usuario eliminado correctamente", "success")
return redirect(url_for("auth.listar_usuarios"))

# Error (admin) → HTTP 302 redirect to /auth/usuarios
flash("No se puede eliminar el usuario admin", "error")
return redirect(url_for("auth.listar_usuarios"))

# Error (not found) → HTTP 302 redirect to /auth/usuarios
flash("Usuario no encontrado", "error")
return redirect(url_for("auth.listar_usuarios"))
```

### `session` after update (same session, JS event)

```python
# If admin edited OWN user and permiso list changed:
# JS event ce-auth-change fires (handled by auth.js)
# Session is NOT modified server-side — only JSON store is updated.
# But if admin changed own permisos, next page load reflects new data.
```

---

## Template Specs

### `usuarios.html` — Edit Modal Structure

```html
<!-- Modal overlay (hidden by default, shown by JS) -->
<div id="editUserModal" class="modal">
  <div class="modal-content">
    <h2>Editar Usuario</h2>
    <form id="editUserForm" method="POST" action="">
      <!-- action set by JS per user -->

      <!-- Username: READONLY text input -->
      <label>Usuario</label>
      <input type="text" name="username" id="edit-username" readonly />

      <!-- Password: OPTIONAL, placeholder "Dejar vacío para no cambiar" -->
      <label>Contraseña</label>
      <input type="password" name="password" id="edit-password"
             placeholder="Dejar vacío para no cambiar" />

      <!-- Rol: select or radio -->
      <label>Rol</label>
      <select name="rol" id="edit-rol">
        <option value="usuario">Usuario</option>
        <option value="admin">Admin</option>
        <option value="medico">Médico</option>
        <option value="facturador">Facturador</option>
      </select>

      <!-- Permisos: checkboxes (same as create form, distinct cruce_facturas/equipos_basicos) -->
      <fieldset>
        <legend>Permisos</legend>
        <label><input type="checkbox" name="permisos" value="odontologia" /> Odontología</label>
        <label><input type="checkbox" name="permisos" value="urgencias" /> Urgencias</label>
        <label><input type="checkbox" name="permisos" value="control_urgencias" /> Control Urgencias</label>
        <label><input type="checkbox" name="permisos" value="facturas_abiertas" /> Facturas Abiertas</label>
        <label><input type="checkbox" name="permisos" value="cruce_facturas" /> Cruce de Reportes</label>
        <label><input type="checkbox" name="permisos" value="equipos_basicos" /> Equipos Básicos</label>
        <label><input type="checkbox" name="permisos" value="derechos" /> Derechos</label>
      </fieldset>

      <!-- Buttons -->
      <button type="submit" class="btn btn-primary">Guardar</button>
      <button type="button" class="btn btn-secondary" id="cancelEdit">Cancelar</button>
    </form>
  </div>
</div>
```

### Table Row Buttons

```html
<!-- Per user row in the table -->
<td class="actions">
  <button class="btn btn-sm btn-edit" data-username="{{ user.username }}"
          data-rol="{{ user.rol }}" data-permisos="{{ user.permisos | join(',') }}">
    Editar
  </button>

  {% if user.username == "admin" %}
    <button class="btn btn-sm btn-delete" disabled
            title="No se puede eliminar el usuario admin">
      Eliminar
    </button>
  {% else %}
    <button class="btn btn-sm btn-delete action-icon--delete"
            data-username="{{ user.username }}">
      Eliminar
    </button>
  {% endif %}
</td>
```

### JS Modal Behavior (Pseudo-code Contract)

```javascript
// Opening modal:
// 1. Click "Editar" button
// 2. Read data-username, data-rol, data-permisos from button's row (or fetch from server)
// 3. Set form action to /auth/usuarios/{username}/editar
// 4. Pre-fill: username (readonly), rol, permisos checkboxes
// 5. Show modal

// Self-edit guard:
// 1. If editing own user (data-username matches current session username)
// 2. AND permisos includes "*" currently being unchecked
// 3. Show extra confirmation: "¿Estás seguro? Perderás acceso de administrador."
// 4. If user cancels, re-check "*" checkbox

// Delete confirmation:
// 1. Click "Eliminar"
// 2. window.confirm("¿Eliminar usuario {username}? Esta acción no se puede deshacer.")
// 3. If confirmed, POST to /auth/usuarios/{username}/eliminar
```

### `home.html` — Conditional Link

```html
{% if '*' in session.get('permisos', []) %}
  <a href="{{ url_for('auth.listar_usuarios') }}" class="nav-link">
    <span class="icon">👥</span> Usuarios
  </a>
{% endif %}
```

### `auth.js` — Event Listener Contract

```javascript
// BEFORE: localStorage.getItem("admin_authenticated") → used for CSS class behavior
// AFTER: document.addEventListener("ce-auth-change", handler)

document.addEventListener("ce-auth-change", function(e) {
  var authed = e.detail && e.detail.auth;  // { auth: boolean }

  // .require-auth elements: show when authenticated
  document.querySelectorAll(".require-auth").forEach(function(el) {
    el.style.display = authed ? "" : "none";
  });

  // .action-icon--delete elements: show when authenticated
  document.querySelectorAll(".action-icon--delete").forEach(function(el) {
    el.style.display = authed ? "" : "none";
  });

  // .editable-cell elements: similar behavior
  document.querySelectorAll(".editable-cell").forEach(function(el) {
    el.classList.toggle("editable", authed);
  });
});
```

---

## Non-Functional Requirements

- **Security**: Backend is the authoritative gate for all delete/edit operations. Frontend guards exist for UX only.
- **Atomicity**: `_save_users()` SHALL write to a temp file and `os.replace()` to prevent corruption.
- **Compatibility**: All existing routes, templates, and behavior for non-auth modules SHALL remain unchanged.
- **Testing**: Every requirement MUST have at least one automated test (unit or integration).
- **TDD Strict Mode**: New tests MUST be written before implementation code.
