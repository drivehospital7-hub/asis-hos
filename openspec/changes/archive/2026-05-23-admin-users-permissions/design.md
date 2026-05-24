# Design: Admin — Usuarios y Permisos

## Technical Approach

Extensión aditiva del JSON store + routes auth existentes. Sin migrar a DB, sin cambiar session auth. Dos endpoints nuevos (editar, eliminar), modal inline en `usuarios.html`, escritura atómica en `_save_users()`, tests para todo CRUD.

---

## Architecture Decisions

### Decision: Modal data source — data-attributes vs fetch endpoint

| Option | Tradeoff |
|--------|----------|
| **data-attributes on `<tr>`** | Sin roundtrip extra. Datos ya disponibles en template. El HTML se serializa en Jinja2 con `tojson` filter. |
| `GET /auth/usuarios/<username>/datos` | Endpoint adicional que mantener. Latencia extra en apertura de modal. |

**Decision**: data-attributes. Cada `<tr>` lleva `data-user='{{ usuario | tojson }}'`. JS lee `JSON.parse(tr.dataset.user)` para llenar el modal. Cero endpoints extra.

### Decision: Self-protection layer

| Capa | Responsabilidad |
|------|----------------|
| **Route (`auth.py`)** | Antes de llamar `update_user()`: si `session["username"] == username` y `"*"` not in nuevos permisos → flash error + redirect. |
| **Store (`users_store.py`)** | `delete_user("admin")` → `(False, msg)`. `update_user()` no valida sesión — es pura persistencia. |
| **Frontend** | Modal muestra confirmación extra si editando propio usuario. Botón delete deshabilitado para `admin`. |

### Decision: Atomic write in `_save_users()`

Escribir a `users.json.tmp` → `os.replace(tmp, target)`. `os.replace()` es atómico en Windows (misma partición). El `.tmp` se ignora en lecturas — si hay crash, `users.json` original queda intacto.

### Decision: POST for delete

HTML forms no soportan DELETE. Usar `POST /auth/usuarios/<username>/eliminar` con campo oculto `_method` para futura compatibilidad REST si se migra a JS fetch. Sin cambiar `csrf.exempt` porque no hay CSRF middleware.

---

## Component Design

### `users_store.update_user(username, **kwargs) → tuple[bool, str]`

```
Input:  username (str), password (str|None), rol (str), permisos (list)
Logic:
  1. _load_users()
  2. Find user by username → if not found → (False, "no encontrado")
  3. Build updated dict from current user data
  4. If "password" in kwargs AND kwargs["password"] is truthy:
     → update password_hash via generate_password_hash()
  5. If "rol" in kwargs → update rol
  6. If "permisos" in kwargs → update permisos
  7. _save_users(users) (atomic write)
  8. Return (True, "actualizado")

Edge cases:
  - password="" or None → no hash change (skip key)
  - username no existe → (False, msg)
  - write falla → exception propaga a route (500)
```

### Atomic `_save_users(users)` — refactor

```python
def _save_users(users: list) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    os.replace(tmp, USERS_FILE)
```

Import `os` añadido. `os.replace()` == atómico en misma partición.

### Endpoints in `routes/auth.py`

```
POST /auth/usuarios/<username>/editar  → @admin_requerido
  Form: username(readonly, hidden), password(opcional), rol, permisos[]
  1. Validate password optional → call update_user(username, password=..., rol=..., permisos=...)
  2. Self-protection: if session["username"] == username and "*" not in permisos:
       flash("No puedes remover tus propios permisos de administrador", "error")
       redirect to listar_usuarios
  3. flash result, redirect

POST /auth/usuarios/<username>/eliminar → @admin_requerido
  1. If username == "admin": flash("No se puede eliminar el usuario admin", "error")
  2. Call delete_user(username)
  3. flash result, redirect
```

### Template: `usuarios.html` — Modal structure

- Cada `<tr>` gana `data-user='...'` (Jinja2 `tojson`), `data-username="{{ usuario.username }}"`
- Botones: "Editar" `<button class="btn-edit">`, "Eliminar" `<button class="btn-delete">`
- Modal HTML (inicialmente oculto, `display:none`):
  - Form action dinámico: `/auth/usuarios/<username>/editar`
  - Campos: username readonly, password (vacío, placeholder "Dejar vacío para no cambiar"), rol select, permisos checkboxes (mismos que crear)
  - Botón guardar + cancelar
- JS: `querySelectorAll('.btn-edit')` → onclick lee `tr.dataset.user` → llena modal → `modal.style.display='block'`
- Delete: `confirm("¿Eliminar usuario X?")` → POST al form
- Confirmación extra si editando propio usuario (comparar username con `session.username` de una variable en template)

### Fix checkbox duplicado

Line 99-100: cambiar `value="equipos_basicos"` a `value="cruce_facturas"`, mantener label "Cruce de Reportes". Line 103-104: mantener `value="equipos_basicos"`, label "Equipos Básicos".

### `home.html` — Admin link

Agregar card para `/auth/usuarios` condicional con `{% if '*' in permisos %}`. Mismo patrón que las cards de área existentes.

### `auth.js` — Refactor

Reemplazar:
- `const AUTH_KEY = 'admin_authenticated'` → listener `window.addEventListener('ce-auth-change', handler)`
- `initAuthUI()` llamado desde el handler del evento, no desde `DOMContentLoaded`
- Mantener lógica de clases `.is-disabled` exactamente igual
- Remover `localStorage.getItem/setItem`
- Remover `window.addEventListener('storage', ...)` (redundante con evento moderno)

---

## Data Flow

### Edit flow

```
Admin click "Editar" → JS lee data-user del <tr>
    → llena modal (username readonly, password vacío, rol+permisos preseleccionados)
    → Admin modifica campos → click "Guardar"
    → JS (opcional): validar que si edita propio user y removió "*", confirmación extra
    → POST /auth/usuarios/{username}/editar
    → Route: self-protection check → update_user() → _save_users() atomic write
    → Flash + redirect a /auth/usuarios
```

### Delete flow

```
Admin click "Eliminar" → confirm("¿Eliminar a {username}?")
    → (si username == "admin", botón disabled, no clickeable)
    → POST /auth/usuarios/{username}/eliminar
    → Route: block if "admin" → delete_user() → _save_users() atomic write
    → Flash + redirect a /auth/usuarios
```

---

## State Changes

| State | Where | Change |
|-------|-------|--------|
| `session["permisos"]` | Flask session | **No cambia** — el admin editado debe logout/login para ver cambios propios. Solo se protege que no se remueva `*` del propio session actual. |
| `instance/users.json` | Disco | Escritura atómica vía tempfile+replace. Contenido igual schema actual. |
| `localStorage` | Browser | `auth.js` refactor elimina uso de `admin_authenticated` key. |

---

## Error Handling

| Component | Error | Behavior |
|-----------|-------|----------|
| `update_user()` | Username no existe | `(False, "Usuario 'X' no encontrado")` |
| `update_user()` | Archivo corrupto al leer | `_load_users()` retorna `[]` — `get_user()` no encuentra → `(False, msg)`. Logger error. |
| `update_user()` | Falla escritura (permisos, disco lleno) | Excepción `OSError` propaga → Flask 500. Logger exception. |
| `delete_user("admin")` | Protección hardcoded | `(False, "No se puede eliminar el usuario administrador")` |
| Route editar | Self-removing `*` | Flash error + redirect. No llama al store. |
| Route editar | Password vacío | `update_user()` recibe `password=""` → no toca hash existente. |
| Route eliminar | Username `admin` | Flash error + redirect. No llama al store. |

---

## Testing Strategy

| Layer | File | What | Approach |
|-------|------|------|----------|
| **Unit** | `tests/utils/test_users_store.py` | `update_user()` (password opcional, admin protection, edge cases), `delete_user()` (admin blocked), `_load_users()` corrupt file, `check_credentials()`, `create_user()` (duplicates) | Mock `_load_users`/`_save_users` internals via `unittest.mock.patch`. No real JSON files. |
| **Integration** | `tests/services/test_auth_routes.py` | Login (success/fail), logout, create (valid/dup), edit (password opcional, self-protection), delete (admin blocked, normal user), list | `app_client` fixture (same as `test_control_errores_integration.py`). Set session directly for auth bypass. Test flash messages and redirects. |
| **Security** | Integration | Self-protection: admin edits own user removing `*` → 403 flash. Delete `admin` → blocked. | Session set as admin, POST with form data, assert flash + redirect. |

**Strict TDD**: tests first (RED) → implement (GREEN) → refactor. No implementation before tests for `update_user()` and endpoints.

---

## Security Considerations

1. **Admin-only endpoints**: `@admin_requerido` verifica `"*"` en session permisos.
2. **Self-protection**: Route valida que admin no se remueva `"*"` a sí mismo. Store protege `delete_user("admin")`. Frontend deshabilita botón delete para `admin` + confirmación extra.
3. **Password optional**: Si se envía vacío, no se actualiza el hash. No hay riesgo de resetear password accidentalmente.
4. **No CSRF**: El sistema no usa CSRF tokens actualmente. Las rutas son POST-only y requieren session auth. Riesgo aceptado para ~1-2 admins internos.
5. **Atomic write**: Previene corrupción de `users.json` por crash. No resuelve concurrencia (último escritor gana — aceptado).
6. **No session invalidation**: Editar permisos propios no invalida la sesión actual — el admin debe logout/login. Esto es intencional: permite revertir si se cometió un error.
