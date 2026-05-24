# Proposal: Admin — Usuarios y Permisos

## Intent

El sistema de autenticación actual tiene endpoints para crear y listar usuarios, pero **faltan eliminar y editar**. No hay tests de auth. El template `usuarios.html` no expone acciones de mantenimiento y tiene un bug (checkbox duplicado). La UI de `home.html` no enlaza a la administración de usuarios. El `auth.js` legacy coexiste con el sistema moderno sin integrarse. Este cambio completa el CRUD de usuarios, agrega tests, y limpia la UI sin migrar a SQLAlchemy.

## Motivation

1. **Seguridad operativa**: Sin endpoint de delete, un admin no puede desactivar usuarios que ya no deben acceder al sistema. Sin endpoint de edit, no puede ajustar permisos sin recrear el usuario.
2. **Bug existente**: El checkbox "Equipos Básicos" aparece dos veces en el formulario de creación con el mismo `value`, impidiendo seleccionar el permiso correcto (`cruce_facturas` vs `equipos_basicos`).
3. **Deuda técnica**: `users_store.delete_user()` existe pero nunca se llama desde ruta alguna. `login_requerido` y `has_permission()` existen pero no se usan. Sin tests de auth, cualquier cambio al sistema de login es un riesgo.
4. **UX**: El enlace a `/auth/usuarios` solo es accesible escribiendo la URL manualmente. El `auth.js` legacy usa una localSstorage key separada sin integrarse al sistema de eventos moderno.

## Scope

### In Scope

- `POST /auth/usuarios/<username>/editar` — Formulario con username (readonly), password (opcional), rol, permisos
- `POST /auth/usuarios/<username>/eliminar` — Eliminar usuario (POST, no DELETE HTTP, por compatibilidad con HTML forms)
- `users_store.update_user()` — Actualización parcial: password opcional (si se deja vacío no cambia), rol y permisos editables
- Protección: usuario `admin` NO eliminable, admin NO puede auto-removerse `*` sin confirmación explícita
- Mejora de `usuarios.html`: botones delete con confirmación JS, botón edit que abre modal en la misma página, fix del checkbox duplicado
- Enlace a `/auth/usuarios` en `home.html` visible solo para admin (`*`)
- Tests unitarios para `users_store.py` (CRUD completo)
- Tests de integración para rutas auth (login, logout, crear, editar, eliminar, listar)
- Refactor de `static/js/auth.js` para usar el sistema moderno de eventos `ce-auth-change`

### Out of Scope

- **NO migrar a SQLAlchemy / Flask-Login** — Se dejan modelos `User` + `UserArea` como dead code documentado. Migración sería su propio cambio SDD.
- **NO cambiar el sistema de sesión** — Sigue siendo `before_request` + `session[]`. Sin cookies JWT, sin tokens.
- **NO cambiar el schema de permisos** — Sigue siendo lista plana de strings con `:write` granularity. No se agregan relaciones muchos-a-muchos.
- **NO refactor del `base.html` inline script** (~160 líneas de fetch auth) — Solo se toca `auth.js` legacy.
- **NO agregar roles dinámicos ni nuevos permisos** — Los permisos existentes se mantienen.
- **NO tocar `models.py`** — Dead code documentado, se deja intacto.

## Capabilities

### New Capabilities

| Capability | Description |
|------------|-------------|
| `editar-usuario` | Admin puede editar username, password (opcional), rol y permisos de cualquier usuario existente |
| `eliminar-usuario` | Admin puede eliminar cualquier usuario excepto `admin` |
| `user-store-update` | `users_store.update_user()` soporta actualización parcial con password opcional |

### Modified Capabilities

| Capability | Change |
|------------|--------|
| `gestion-usuarios-ui` | `usuarios.html` ahora incluye modal de edición inline y botones de delete con confirmación |
| `admin-nav` | `home.html` muestra enlace a `/auth/usuarios` para admin |
| `permisos-form` | Checkbox duplicado corregido: se agrega `value="cruce_facturas"` (label "Cruce de Reportes") y se mantiene `value="equipos_basicos"` (label "Equipos Básicos") |

## Approach

### Arquitectura

El cambio es **aditivo y conservador**. No se modifica el flujo de autenticación existente. Se agregan:

1. **`users_store.update_user()`** — Nueva función que recibe username (identificador) + dict con campos a actualizar. Si `password` está presente y no vacío, hashea y actualiza. Rol y permisos se actualizan siempre que se envíen. Retorna `(True, msg)` o `(False, msg)`. Protege al usuario `admin` de auto-desactivación.

2. **Endpoints REST-like en `routes/auth.py`** — Dos nuevos endpoints decorados con `@admin_requerido`:
   - `POST /auth/usuarios/<username>/editar` → recibe form → llama `users_store.update_user()` → flash + redirect
   - `POST /auth/usuarios/<username>/eliminar` → recibe form → llama `users_store.delete_user()` (ya existe) con protección para `admin`

3. **Modal de edición inline** — En `usuarios.html`: un modal (JavaScript, no página separada) que se rellena con los datos del usuario vía fetch o data-attributes inline. El formulario de creación existente se mantiene como está. Consistente con el modal login existente en `base.html`.

4. **Protección de admin** — Validación en backend (`update_user()` rechaza si el usuario que se edita es `admin` y se intenta remover `"*"` del propio `session["username"]`). Validación en frontend (confirmación JS antes de submit). El delete del usuario `admin` se bloquea a nivel de store.

5. **Tests** — Se crean:
   - `tests/utils/test_users_store.py` — Unit tests para `users_store.py` (mockeando `_load_users` / `_save_users`)
   - `tests/services/test_auth_routes.py` — Integration tests con `app_client`, seteando session directo (mismo patrón que `test_control_errores_integration.py`)

6. **Refactor auth.js** — El código actual usa `localStorage.getItem('admin_authenticated')` y maneja clases `.require-auth`, `.action-icon--delete`, `.editable-cell`. Se reemplaza por escucha del evento `ce-auth-change` (disparado por el sistema moderno en `base.html`) que ya tiene el estado actualizado de la sesión.

### Decisiones de Diseño

- **POST vs DELETE HTTP**: Se usa `POST` para eliminar porque HTML forms no soportan DELETE. El endpoint podría soportar ambos en el futuro.
- **Modal vs página separada para edición**: **Modal** en la misma página. Justificación: el formulario de edición es simple (username readonly, password opcional, rol, permisos). Ya hay un modal login existente como precedente. Evita crear una página extra y mantener navegación.
- **Password opcional**: Si el campo password se envía vacío, `update_user()` no toca el hash existente. Esto permite editar rol/permisos sin requerir reseteo de password.
- **Escritura atómica**: `_save_users` actualmente escribe directo. Se puede mejorar con write-a-temp-file + rename para evitar corrupción en caso de crash.

### Flujo de Edición

```
1. Admin hace click en "Editar" → JS abre modal con datos del usuario
2. Modal carga datos desde data-attributes en el row HTML o via fetch GET /auth/usuarios/<username>/datos
3. Admin modifica campos → click "Guardar"
4. POST /auth/usuarios/<username>/editar → users_store.update_user()
5. Si el admin editó su propio usuario y removió "*":
   → Backend rechaza con flash "No puedes remover tus propios permisos de administrador"
   → Frontend muestra confirmación adicional antes de submit
6. Redirect a /auth/usuarios con flash success/error
```

### Flujo de Eliminación

```
1. Admin hace click en "Eliminar" → confirmación JS (confirm() o modal)
2. Si el usuario es "admin" → botón deshabilitado + tooltip "No se puede eliminar el usuario admin"
3. POST /auth/usuarios/<username>/eliminar → users_store.delete_user()
4. Redirect a /auth/usuarios con flash
```

## Files

| Archivo | Acción | Cambio |
|---------|--------|--------|
| `app/utils/users_store.py` | **MODIFY** | Agregar `update_user()`. Mejorar `_save_users()` con escritura atómica. Proteger `delete_user()` contra eliminar `admin`. |
| `app/routes/auth.py` | **MODIFY** | Agregar `POST /auth/usuarios/<username>/editar` y `POST /auth/usuarios/<username>/eliminar`. |
| `app/templates/usuarios.html` | **MODIFY** | Agregar modal de edición, botones delete/edit por fila, fix checkbox duplicado. |
| `app/templates/home.html` | **MODIFY** | Agregar enlace a `/auth/usuarios` condicional (`'*' in permisos`). |
| `app/static/js/auth.js` | **REFACTOR** | Reemplazar `localStorage` por evento `ce-auth-change`. Mantener clases CSS. |
| `tests/utils/test_users_store.py` | **NEW** | Tests unitarios: `update_user()`, `delete_user()` (admin protegido), `check_credentials()`, `create_user()` (duplicados), `list_users()`. |
| `tests/services/test_auth_routes.py` | **NEW** | Tests integración: login, logout, crear, editar, eliminar, listar, proteger admin, auto-desactivación. |

## No Tocar

| Módulo | Razón |
|--------|-------|
| `app/utils/auth_session.py` | `has_permission()` no usado pero no se toca — podría ser útil. |
| `app/utils/auth.py` | Decorators existentes. No se modifican. `login_requerido` sigue sin usarse. |
| `app/models.py` | Dead code SQLAlchemy. No se elimina ni modifica. Documentar como tal. |
| `app/database.py` | Conexión DB para otros features. No tocar. |
| `app/__init__.py` | `before_request` global. No tocar. |
| `app/templates/base.html` | No tocar. El refactor de `auth.js` no requiere cambios aquí. |
| `tests/conftest.py` | Se reutiliza `app_client` fixture existente. No se modifica. |

## Implementation Plan

| Fase | Qué | Depende de | Riesgo |
|------|-----|-----------|--------|
| **1. `users_store.update_user()`** | Nueva función + escritura atómica + protección admin | — | **Bajo** |
| **2. Tests unitarios `users_store`** | `tests/utils/test_users_store.py` cubriendo update, delete admin, escritura atómica | Fase 1 | Bajo |
| **3. Endpoints editar + eliminar** | `POST /auth/usuarios/<username>/editar` y `POST /auth/usuarios/<username>/eliminar` en `routes/auth.py` | Fase 1 | Medio |
| **4. Tests integración rutas auth** | `tests/services/test_auth_routes.py` cubriendo login, CRUD, protecciones | Fase 3 | Medio |
| **5. Template `usuarios.html`** | Modal edición, botones delete, fix checkbox duplicado. Validación frontend. | Fase 3 | Medio |
| **6. `home.html` enlace admin** | Link condicional a `/auth/usuarios` para admin | — | **Bajo** |
| **7. Refactor `auth.js`** | Reemplazar localStorage key por evento `ce-auth-change` | — | Bajo |

**Orden recomendado**: Fases 1→2→3→4→5→6→7. Las fases 1-4 son la columna vertebral (store + routes + tests). Las fases 5-6 son UI. La fase 7 es un refactor independiente del JS legacy.

## Risks

| Riesgo | P | I | Mitigación |
|--------|---|---|------------|
| **Eliminar admin por accidente** | Baja | **Crítico** | Bloquear en `users_store.delete_user()` si username == "admin". Bloquear en frontend (botón deshabilitado). |
| **Admin se auto-desactiva** | Media | **Crítico** | Si admin edita su propio usuario y remueve `"*"`, queda sin acceso. Validar en `update_user()`: si `session["username"]` coincide con el username editado y los nuevos permisos no contienen `"*"`, rechazar con error explícito. |
| **Regresión en login** | Media | Alto | No hay tests de auth existentes. Los tests de la Fase 2 y 4 cubren el store y las rutas. Correr tests completos antes de merge. |
| **Corrupción de users.json** | Baja | Alto | `_save_users()` actualmente escribe directo. Implementar escritura atómica (write a temp file → `os.replace()`) en la Fase 1. |
| **Concurrencia** | Baja | Medio | Dos admins editando simultáneamente — el último escritor gana. No crítico para ~1-2 admins. Aceptado como trade-off del JSON store. |

## Rollback Plan

1. **Por fase**: Cada fase es un commit independiente y reversible.
2. **`users_store.py`**: La nueva función `update_user()` es aditiva — no rompe nada existente. Revertir solo ese commit si hay problemas.
3. **Endpoints nuevos**: Rutas nuevas no afectan las existentes. Revertir commit de rutas si es necesario.
4. **Templates**: `usuarios.html` es el único template modificado. Revertir commit de template. `home.html` es un cambio trivial.
5. **auth.js**: El refactor es puramente JS cliente. Si algo falla, revertir el commit.
6. **Comando**: `git revert <commit-hash>` del paso problemático. Sin dependencias entre fases no secuenciales (5, 6, 7 pueden revertirse independientemente).

## Success Criteria

- [ ] Admin puede crear, editar y eliminar usuarios desde la UI
- [ ] Usuario `admin` NO puede ser eliminado (backend + frontend)
- [ ] Admin NO puede auto-removerse `*` sin confirmación (backend rechaza)
- [ ] Password es opcional en edición — si se deja vacío, no cambia
- [ ] Checkbox "Cruce de Reportes" y "Equipos Básicos" son dos checkboxes distintos con distintos `value`
- [ ] Enlace a `/auth/usuarios` visible en `home.html` para admin, invisible para usuarios sin `*`
- [ ] `auth.js` usa `ce-auth-change` event en lugar de localStorage key separada
- [ ] Tests unitarios de `users_store.py` pasan (update, delete, admin protection, atomic write)
- [ ] Tests de integración de rutas auth pasan (login, CRUD, session permissions, edge cases)
- [ ] `models.py` no se modifica (dead code documentado)
- [ ] Todos los tests existentes siguen pasando (sin regresión)

## Effort

| Métrica | Valor |
|---------|-------|
| Archivos creados | 2 (test_users_store.py, test_auth_routes.py) |
| Archivos modificados | 5 (users_store.py, auth.py, usuarios.html, home.html, auth.js) |
| Archivos eliminados | 0 |
| Líneas nuevas | ~450 (estimado: 100 store + 150 tests unitarios + 100 tests integración + 100 templates + 30 auth.js) |
| Líneas eliminadas | ~65 (auth.js legacy reemplazado) |
| Complejidad | **BAJA-MEDIA** — cambios aditivos, sin refactor de infraestructura existente |
| Fases | 7 secuenciales, cada una con tests |
