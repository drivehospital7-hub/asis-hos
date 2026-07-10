# Delta for admin-users-permissions

## MODIFIED Requirements

### R1: `users_store.update_user()` — Validación de Rol Expandida

`update_user(username, updates)` MUST validar que `rol` sea uno de `["admin", "usuario", "medico", "facturador"]`.
(Previously: rol validado como `"admin"` o `"usuario"` únicamente)

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Update to medico | existing user | `update_user("u", {"rol": "medico"})` | rol changed to "medico" |
| Update to facturador | existing user | `update_user("u", {"rol": "facturador"})` | rol changed to "facturador" |
| Invalid rol | existing user | `update_user("u", {"rol": "enfermero"})` | returns `(False, "Rol inválido: debe ser admin, usuario, medico o facturador")` |

### Template: Rol Select en Modal de Edición

The `usuarios.html` edit modal `<select name="rol">` MUST incluir las 4 opciones.
(Previously: solo "Usuario" y "Admin")

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Render modal | admin opens edit modal | inspect `<select name="rol">` | options: Usuario, Admin, Médico, Facturador |
| Render create form | admin on `/auth/usuarios` | inspect create form select | same 4 options |

### Template: Rol Select en React (`frontend/src/pages/usuarios/page.tsx`)

The React usuarios page dropdown MUST list the same 4 roles.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Render React page | admin navigates to `/auth/usuarios` (React version) | dropdown options | includes "Médico" and "Facturador" |

## MODIFIED Validation Rules

### R1: `update_user()` — Field Validation (rol row updated)

| Field | Rule | Error Message |
|-------|------|---------------|
| `rol` | MUST be `"admin"`, `"usuario"`, `"medico"`, or `"facturador"` | `"Rol inválido: debe ser admin, usuario, medico o facturador"` |

(Previously: rol MUST be `"admin"` or `"usuario"`; message was `"Rol inválido: debe ser admin o usuario"`)

## MODIFIED Acceptance Criteria

The following criteria are ADDED to the existing list:
- [ ] `update_user()` accepts `"medico"` and `"facturador"` as valid roles
- [ ] `update_user()` rejects unknown roles with descriptive message
- [ ] `usuarios.html` rol dropdown shows 4 options
- [ ] React usuarios page dropdown shows 4 options
- [ ] `create_user()` accepts new roles without error
