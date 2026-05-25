# Proposal: Perfiles de Usuarios — Plantillas

## Intent

Transformar los 3 usuarios default (`odontologia`, `urgencias`, `auditor`) en plantillas reutilizables de permisos que un admin pueda asignar al crear usuarios, preservando las cuentas reales existentes para no romper sesiones activas.

## Scope

### In Scope
- Modelo de datos de plantillas (nombre, descripción, permisos)
- Store: archivo `instance/templates.json` separado (schema distinto — sin password)
- CRUD de plantillas en `app/utils/templates_store.py`
- React UI: dropdown "Plantilla" → pre-rellena checkboxes en crear/editar
- Jinja2 UI legacy: mismo selector
- Migración: `DEFAULT_USERS` dividido — `admin` como real; los otros 3 como real + plantilla

### Out of Scope
- Nuevos permisos o roles — solo organizar existentes
- Herencia anidada de permisos (template hereda de otro template)
- Limpiar permisos fantasma (`cruce_facturas`, `derechos`) — cambio separado
- Migración a DB

## Capabilities

### New Capabilities
- `user-templates`: Plantillas de permisos reutilizables — CRUD backend + selector UI

### Modified Capabilities
- `admin-users-permissions`: formularios crear/editar ganan selector de plantilla; lista de usuarios filtra plantillas

## Approach

**Store**: `instance/templates.json` separado. Schema: `{nombre, descripcion, permisos: []}`. Sin password — las plantillas no loguean.

**Migración**: `DEFAULT_USERS` se parte en 2 grupos. `admin` = real. Los otros 3 se crean como cuenta real (preservar sesiones) + plantilla en `templates.json`. `_create_default_users()` crea ambos archivos.

**Backend**: `templates_store.py` con `list_templates()`, `get_template()`. Endpoint `GET /api/templates` para React. `list_users()` excluye cuentas que también son plantilla — o usa flag `is_template` si se prefiere schema unificado.

**React UI**: Dropdown "Basado en plantilla" arriba de checkboxes en crear/editar. Al seleccionar → permisos se pre-rellenan (editables manualmente). Sin efecto si el usuario es admin.

**Jinja2 UI**: Misma feature en `usuarios.html` — dropdown + JS que checkea boxes.

## Affected Areas

| Area | Impact |
|------|--------|
| `app/utils/users_store.py` | Modified — DEFAULT_USERS dividido |
| `app/utils/templates_store.py` | New — CRUD plantillas |
| `app/constants/base.py` | Minor — posible constante TEMPLATE_NAMES |
| `app/routes/auth.py` | Modified — endpoint /api/templates, filtrar plantillas |
| `frontend/src/pages/usuarios/page.tsx` | Modified — dropdown + pre-fill |
| `app/templates/usuarios.html` | Modified — mismo dropdown |
| `instance/templates.json` | New — datos (auto-creado) |
| `tests/utils/test_templates_store.py` | New — tests unitarios |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Romper sesiones de odontologia/urgencias/auditor | Baja | Preservar cuentas reales + crear plantillas duplicando permisos |
| React vs Jinja2 divergencia | Media | React primero (activo), Jinja2 después con paridad exacta |
| Admin confunde plantilla con usuario real | Media | No mostrar plantillas en lista de usuarios; badge si se muestran |

## Rollback

1. Commit por capa: store → API → React → Jinja2
2. Revertir commit de `templates_store.py` elimina la feature
3. UIs se revierten independientemente
4. Usuarios reales intactos — migración aditiva, no destructiva

## Success Criteria

- [ ] Admin crea usuario y ve dropdown con 3 plantillas
- [ ] Seleccionar plantilla pre-rellena checkboxes de permisos (editables)
- [ ] Usuarios reales odontologia/urgencias/auditor siguen existiendo y logueando
- [ ] `list_users()` NO muestra plantillas como cuentas
- [ ] Tests: template CRUD, migración defaults, pre-fill UI
