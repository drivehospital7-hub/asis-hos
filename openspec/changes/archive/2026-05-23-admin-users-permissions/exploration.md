# Exploration: Admin — Usuarios y Permisos

## Current State

### Arquitectura de Autenticación

El sistema usa **sesiones Flask** (no Flask-Login). Flujo completo:

```
Request → before_request (app/__init__.py)
           ├── endpoint en PUBLIC_ENDPOINTS? → OK (login, logout, status, static)
           ├── session["ce_authenticated"]? → OK
           └── no autenticado → 401 JSON o render_template("unauthorized.html")

Route → @permiso_requerido("odontologia") o @admin_requerido
         ├── session["permisos"] contiene "*"? → OK (admin)
         ├── session["permisos"] contiene alguno de los requeridos? → OK
         └── no → 403 JSON o redirect(home)
```

La sesión guarda 4 claves:
| Clave | Tipo | Descripción |
|-------|------|-------------|
| `ce_authenticated` | `bool` | Flag de autenticación |
| `username` | `str` | Nombre de usuario |
| `rol` | `str` | `"admin"` o `"usuario"` |
| `permisos` | `list[str]` | Lista plana de permisos |

**No hay cookies JWT, no hay tokens, no hay DB involucrada.**

---

### User Store (`app/utils/users_store.py`)

Persistencia via archivo JSON en `instance/users.json`. Se crea con 4 usuarios por defecto al primer acceso:

| Usuario | Password | Rol | Permisos |
|---------|----------|-----|----------|
| `admin` | `admin123` | `admin` | `["*"]` |
| `odontologia` | `odonto123` | `usuario` | `["odontologia"]` |
| `urgencias` | `urgencias123` | `usuario` | `["urgencias", "control_urgencias", "facturas_abiertas"]` |
| `auditor` | `auditor123` | `usuario` | `["control_urgencias", "control_urgencias:write", "facturas_abiertas", "facturas_abiertas:write", "equipos_basicos"]` |

**Schema del JSON** (tras hashear):
```json
{
  "username": "admin",
  "password_hash": "<werkzeug-scrypt-hash>",
  "rol": "admin",
  "permisos": ["*"]
}
```

**Operaciones disponibles en `users_store.py`:**

| Operación | ¿Exportada? | ¿Usada en routes? | Estado |
|-----------|-------------|-------------------|--------|
| `check_credentials()` | ✅ | ✅ (`auth.login`, `auth.api_login`) | Activa |
| `get_user()` | ✅ | ❌ No usada en routes | Potencialmente útil |
| `list_users()` | ✅ | ✅ (`auth.listar_usuarios`) | Activa |
| `create_user()` | ✅ | ✅ (`auth.crear_usuario`) | Activa |
| `delete_user()` | ✅ | ❌ **NO USADA** — no hay endpoint | **Orphaned** |

**⚠️ Bug en template `usuarios.html`:** El checkbox "Equipos Básicos" aparece dos veces (líneas 99-100 y 103-104), ambos con `value="equipos_basicos"`. `value="equipos_basicos"` se muestra como "Cruce de Reportes" y también "Equipos Básicos" — probablemente un copy-paste donde debía ser `value="cruce_facturas"` para uno de ellos.

---

### Sistema de Permisos

**Definición:** Lista plana de strings. Semántica actual:

| Permiso | Significado | ¿Write granularity? |
|---------|-------------|---------------------|
| `*` | Admin total (pasa todo) | N/A |
| `odontologia` | Acceso a odontología | No |
| `urgencias` | Acceso a urgencias | No |
| `control_urgencias` | Control urgencias (lectura) | No |
| `control_urgencias:write` | Control urgencias (modificar) | Sí — `:write` suffix |
| `facturas_abiertas` | Facturas abiertas (lectura) | No |
| `facturas_abiertas:write` | Facturas abiertas (modificar) | Sí — `:write` suffix |
| `equipos_basicos` | Cruce de reportes / equipos básicos | No |
| `derechos` | Derechos | No |

**Mecanismos de verificación:**

1. **`@permiso_requerido(*permisos)`** — Decorator. Verifica que session["permisos"] contenga AL MENOS UNO de los strings pasados. Admin (`*`) pasa todo automáticamente.
2. **`@admin_requerido`** — Decorator. Solo pasa si `"*"` está en session["permisos"].
3. **`@login_requerido`** — Decorator. Verifica `ce_authenticated`. **Definido pero NO usado en ninguna ruta actual** — el `before_request` global cubre este caso.
4. **`auth_session.has_permission()`** — Función programática (no decorator). **Definida pero NO usada en ningún lado.**
5. **`before_request` en `app/__init__.py`** — Middleware global. Solo verifica autenticación (ce_authenticated), NO permisos.

**Uso actual de decoradores por archivo:**

| Archivo | Decorador | Valor |
|---------|-----------|-------|
| `routes/excel_headers.py` | `@permiso_requerido` | `"odontologia"` |
| `routes/urgencias.py` | `@permiso_requerido` | `"urgencias"` |
| `routes/ordenado_facturado.py` | `@permiso_requerido` | `"equipos_basicos"` |
| `routes/control_errores.py` | `@permiso_requerido` | `"control_urgencias"` o `"control_urgencias:write"` |
| `routes/abiertas_urgencias.py` | `@permiso_requerido` | `"facturas_abiertas"` o `"facturas_abiertas:write"` |
| `routes/auth.py` | `@admin_requerido` | (solo admin) |

---

### Routes de Administración (`app/routes/auth.py`)

Blueprint `auth_bp` con url_prefix `/auth`:

| Endpoint | Método | Decorador | Función | ¿Funciona? |
|----------|--------|-----------|---------|------------|
| `/auth/login` | GET, POST | — | Form login + redirect | ✅ |
| `/auth/logout` | GET | — | Limpia sesión | ✅ |
| `/auth/api/login` | POST | — | JSON login | ✅ |
| `/auth/api/logout` | POST | — | JSON logout | ✅ |
| `/auth/api/status` | GET | — | JSON status | ✅ |
| `/auth/usuarios` | GET | `@admin_requerido` | Renderiza `usuarios.html` | ✅ |
| `/auth/usuarios/crear` | POST | `@admin_requerido` | Crea usuario | ✅ |
| — | — | — | **DELETE usuario** | ❌ **No existe** |
| — | — | — | **EDIT usuario** | ❌ **No existe** |
| — | — | — | **Cambiar password** | ❌ **No existe** |

---

### Templates

| Template | Propósito | Estado |
|----------|-----------|--------|
| `login.html` | Login tradicional (standalone, sin herencia) | ✅ |
| `base.html` | Layout global + logout link + modal login easter egg + JS auth | ✅ |
| `home.html` | Dashboard con cards por área (filtradas por permisos) | ✅ |
| `usuarios.html` | Admin: crear usuario + listar tabla | ⚠️ Sin delete ni edit |
| `unauthorized.html` | Página 401 (extiende base.html) | ✅ |

**Nav:** El `home.html` NO tiene enlace a `/auth/usuarios`. La única forma de llegar es escribiendo la URL manualmente. El `base.html` solo muestra "Cerrar sesión" y el username.

---

### SQLAlchemy Models vs JSON Store

| Aspecto | JSON Store (`users_store.py`) | SQLAlchemy (`models.py`) |
|---------|-------------------------------|--------------------------|
| **¿En uso?** | ✅ Activo | ❌ **Dead code** |
| **Persistencia** | `instance/users.json` | Tabla `users` en PostgreSQL |
| **Modelos** | `User` como dict | `User` + `UserArea` classes |
| **Passwords** | Werkzeug `generate_password_hash` | `password_hash` column |
| **Permisos** | Lista plana en `permisos` | `UserArea` relationship (muchos a muchos) |
| **Rol** | String `"admin"` / `"usuario"` | String `rol` |
| **Flask-Login** | NO | Sí — `is_authenticated`, `get_id()`, etc. |
| **¿Migrar?** | — | Posible pero requiere cambios mayores |

Los modelos SQLAlchemy tienen `User` y `UserArea` preparados para un sistema de permisos por área (relación muchos-a-muchos), mientras que el JSON store actual usa lista plana de strings. Son dos concepciones distintas de permisos.

---

### Frontend JS

Dos sistemas coexisten:

1. **`base.html` inline script** (~160 líneas): Sistema de autenticación completo con fetch a `/auth/api/login`, `/auth/api/logout`, `/auth/api/status`. Usa localStorage key `ce_auth` para UI sync. Es el sistema activo que funciona con la sesión del servidor.

2. **`static/js/auth.js`** (~65 líneas): Sistema LEGACY con localStorage key `admin_authenticated`. Maneja clases CSS (`.require-auth`, `.action-icon--delete`, `.editable-cell`) para UI en control_errores. **No se comunica con el servidor.**

Ambos coexisten y no entran en conflicto porque usan distintas localStorage keys. El `auth.js` legacy debería ser refactorizado para usar `ce-auth-change` events del sistema moderno.

---

### Tests Existentes

**No hay tests para auth.** Los tests existentes para rutas (urgencias, control_errores, etc.) bypassan la autenticación completamente seteando session directo:

```python
with app_client.session_transaction() as sess:
    sess["ce_authenticated"] = True
    sess["permisos"] = ["odontologia"]
```

Esto significa que cualquier cambio al auth system NO está cubierto por tests automatizados.

---

### Flujo de Login Completo (para referencia)

```
1. Usuario GET /auth/login → render login.html (form)
2. POST /auth/login (user + pass)
3. auth_session.check_credentials(user, pass)
   → users_store.check_credentials() → werkzeug check_password_hash()
   → retorna dict {username, rol, permisos} o None
4. auth_session.do_login(user_data)
   → session["ce_authenticated"] = True
   → session["username"] = user_data["username"]
   → session["rol"] = user_data["rol"]
   → session["permisos"] = user_data["permisos"]
   → session.permanent = True
5. Redirect a home (o next page)
```

---

## Affected Areas

| Archivo | Por qué está afectado |
|---------|----------------------|
| `app/routes/auth.py` | Necesita endpoints DELETE, PUT/PATCH para usuarios |
| `app/utils/users_store.py` | `delete_user()` existe pero no se llama. Falta `update_user()`. |
| `app/utils/auth.py` | `login_requerido` decorator no usado. `admin_requerido` usado en auth routes. |
| `app/utils/auth_session.py` | `has_permission()` no usado. Posible refactor. |
| `app/templates/usuarios.html` | Sin botones delete/edit. Bug checkbox duplicado. |
| `app/templates/home.html` | Sin enlace a `/auth/usuarios` |
| `app/static/js/auth.js` | Legacy con localStorage key separada |
| `app/models.py` | Dead code SQLAlchemy — decide si eliminar o mantener |
| `tests/` | Sin tests para auth — hay que crearlos |

---

## Approaches

### 1. **Evolucionar el JSON Store actual** — Agregar endpoints faltantes sin cambiar store

Agregar a `routes/auth.py`:
- `DELETE /auth/usuarios/<username>` → llama `users_store.delete_user()`
- `POST /auth/usuarios/<username>/editar` → nuevo `users_store.update_user()`
- `POST /auth/usuarios/<username>/cambiar-password` → nuevo cambio de password

En template: botones delete (con confirmación JS) y edit (modal o inline form). Enlace desde home.

- **Pros**: Mínimo riesgo. Rápido. Consistente con lo que ya existe.
- **Cons**: Sigue preso del JSON file (no concurrente, no escalable). No resuelve la brecha con los modelos SQLAlchemy.
- **Effort**: Bajo (~1-2 días)

### 2. **Migrar a SQLAlchemy + Flask-Login** — Reemplazar JSON store con DB

Activar los modelos `User` + `UserArea` existentes, conectar Flask-Login, migrar datos del JSON a PostgreSQL. Repensar permisos como relaciones muchos-a-muchos.

- **Pros**: Escalable, concurrente, preparado para futuro. Usa infraestructura existente (DB ya configurada).
- **Cons**: Cambio MASIVO. Rompe todo el sistema de sesión actual. Migración de 4 usuarios a DB con schema distinto (user_areas vs permisos planos). Sin tests de auth existentes. Alto riesgo de regresión.
- **Effort**: Muy alto (~2-3 semanas)

### 3. **Híbrido — JSON store mejorado + ruta hacia SQLAlchemy** 

Mantener JSON store para ahora, pero:
- Agregar los endpoints faltantes (delete, edit, change password)
- Mejorar el template (con delete/edit, fix checkbox bug, enlace desde home)
- Agregar tests de auth (unit + integration)
- Refactorizar el `auth.js` legacy para usar el sistema moderno
- Dejar los modelos SQLAlchemy como están (dead code documentado)

- **Pros**: Bajo riesgo, entrega valor inmediato, sienta base de tests para futura migración.
- **Cons**: No resuelve la deuda técnica del JSON store.
- **Effort**: Medio (~3-5 días)

---

## Recommendation

**Approach 3 — Híbrido.** Razones:

1. El JSON store funciona y tiene solo 4 usuarios. La falta de concurrencia no es un problema real hoy.
2. Los modelos SQLAlchemy `User` + `UserArea` tienen un schema DISTINTO (permisos por área vs permisos planos). Migrar requeriría repensar todo el sistema de permisos — es un cambio conceptual, no solo técnico.
3. Lo que el sistema NECESITA ahora son endpoints faltantes (delete, edit) y tests. No una migración de storage.
4. Una migración a SQLAlchemy debería ser su PROPIO cambio SDD, con proposal, design, y plan de migración incremental.

Enfoque concreto para este cambio:
1. Agregar `POST /auth/usuarios/<username>/editar` — formulario con campos: username (readonly), password (opcional, si se deja vacío no cambia), rol, permisos
2. Agregar `POST /auth/usuarios/<username>/eliminar` (DELETE no es soportado por HTML forms, usar POST)
3. Agregar `users_store.update_user()` — soporta actualización parcial (password opcional)
4. Mejorar `usuarios.html`: botones delete con confirmación, botón edit que lleva a formulario (en misma página o modal)
5. Agregar enlace a `/auth/usuarios` en `home.html` visible solo para admin
6. Fix bug checkbox duplicado `equipos_basicos`
7. Agregar tests unitarios para `users_store.py` y tests de integración para rutas auth
8. NO tocar Flask-Login, NO migrar a DB — dejar modelos como dead code documentado

---

## Risks

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Eliminar admin por accidente** | Baja | Crítico | Bloquear delete del usuario `admin`. Validar en backend y frontend. |
| **Admin pierde acceso por cambio de rol/permisos** | Media | Crítico | Si un admin edita su propio rol a `usuario` y se remueve `*`, queda lockeado. Validar que admin no pueda auto-desactivarse. Mejor: crear usuario admin separado antes de editar. |
| **Regresión en login** | Media | Alto | No hay tests de auth actualmente. Cualquier cambio a `users_store.py` sin tests puede romper login. |
| **JSON file corruption** | Baja | Alto | `_save_users` escribe el archivo completo. Un crash en medio deja el archivo corrupto. Usar escritura atómica (write a temp + rename). |
| **Concurrencia** | Baja | Medio | Dos admins editando usuarios simultáneamente → el último escritor gana. No crítico para 1-2 admins. |

---

## Decisiones Pendientes

1. **¿Cómo manejar la edición de usuarios?** — ¿Modal en la misma página (SPA-like con fetch) o página separada (form tradicional)? Recomiendo modal para edit (consistente con modal login existente) y página separada solo si el form es muy complejo.

2. **¿Proteger al admin de auto-desactivarse?** — Recomiendo: (a) no permitir eliminar el usuario `admin`, (b) al editar tu propio usuario, mostrar advertencia si vas a remover `*`, (c) requerir confirmación explícita.

3. **¿Incluir refactor del `auth.js` legacy en este cambio?** — Recomiendo SÍ, es pequeño (~65 líneas) y el cambio afecta la UI de auth. Mejor dejarlo limpio.

4. **¿Incluir el enlace a /auth/usuarios en home.html?** — Recomiendo SÍ, es trivial y sin eso la feature es invisible.

---

## Ready for Proposal

**Sí.** La exploración identificó claramente:
- Qué endpoints faltan (delete, edit, change password)
- Qué funciones existen pero no se usan (`delete_user()`, `login_requerido`, `has_permission()`)
- Dónde está el bug en el template (checkbox duplicado)
- Qué NO hacer (migrar a SQLAlchemy ahora — cambio separado)
- Qué tests crear
- Los riesgos de autodesactivación del admin

La propuesta debe plantear el **Híbrido (Approach 3)** con los 8 puntos listados en la recomendación.
