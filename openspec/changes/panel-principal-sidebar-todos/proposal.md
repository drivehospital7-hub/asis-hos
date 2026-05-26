# Proposal: Panel principal en sidebar para todos los usuarios

## Intent

Todos los usuarios autenticados deben ver "Panel principal" en el sidebar para acceder al dashboard con sus áreas permitidas. Actualmente solo admin (`*`) lo ve, aunque el backend de `/dashboard` ya filtra correctamente por permisos.

## Scope

### In Scope
1. Jinja2 sidebar (`base.html`): mostrar "Panel principal" para usuarios no-admin antes del loop por dominio
2. React sidebar (`app-sidebar.tsx`): mostrar "Panel principal" para todos los usuarios autenticados

### Out of Scope
- Cambiar la lógica de seguridad o permisos del dashboard (ya funciona)
- Agregar/remover áreas del dashboard
- Refactorizar el sistema de navegación del sidebar

## Capabilities

### New Capabilities
None — cambio puramente de UI/navegación. No hay nueva capacidad a nivel de spec.

### Modified Capabilities
None — el acceso al dashboard y su comportamiento no cambian. Solo se modifica la visibilidad del enlace en la navegación.

## Approach

**Jinja2** (`app/templates/base.html`): Antes del loop `_ep_map` (línea 90), agregar un link standalone a `home.home_react` con icono `LayoutDashboard`. Este link se renderiza siempre para usuarios no-admin. El loop existente continúa después para los items por dominio.

**React** (`frontend/src/components/app-sidebar.tsx`): Remover `permiso: "*"` del item "Panel principal" (línea 23). El filtro en línea 49 ya tiene `if (!item.permiso) return true;` — sin permiso definido, aparece para todos.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/templates/base.html` | Modified | Agregar link "Panel principal" antes del loop `_ep_map` para no-admin |
| `frontend/src/components/app-sidebar.tsx` | Modified | Quitar `permiso: "*"` del nav item "Panel principal" |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Admin pierde "Panel principal" | Baja | Admin path (`*` loop) no se toca — sigue iterando todo `nav_items` incluyendo `home.home_react` |
| React sidebar muestra duplicado | Baja | Solo se modifica un item, no se agrega nada nuevo. Filter `!item.permiso` solo aplica a este item |
| `/dashboard` no funciona para no-admin | Ya verificado | `_filter_areas()` en `home.py` ya filtra por `session["permisos"]` — funciona correctamente |

## Rollback Plan

1. Jinja2: revertir el bloque de link agregado en `base.html`
2. React: restaurar `permiso: "*"` en el item "Panel principal"
3. Cada cambio es independiente y reversible en un commit

## Success Criteria

- [ ] Usuario no-admin ve "Panel principal" en Jinja2 sidebar
- [ ] Usuario no-admin ve "Panel principal" en React sidebar
- [ ] Admin (`*`) sigue viendo todos los items incluyendo "Panel principal"
- [ ] `/dashboard` renderiza correctamente para todos los usuarios (ya verificado)
- [ ] Tests pasan (`pytest -v`)
