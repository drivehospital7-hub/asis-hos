# Design: Mejora de Experiencia de Navegación entre Dashboard y Áreas

## Technical Approach

Cuatro cambios independientes en templates + CSS, cero cambios en rutas Python:

1. **Fix Mini.local**: Remover el `addEventListener('click', ...)` que intercepta el click (líneas 184-195 de `base.html`). El `<a href>` nativo ya tiene la URL correcta — solo necesita no ser secuestrado.
2. **Mover easter egg**: Agregar footer a `base.html` con texto de versión. Mover `openModal()` a un `dblclick` listener sobre el footer.
3. **Nav bar**: Bloque `<nav>` en `base.html` que itera `session_permisos` contra un mapeo Jinja de permiso → {label, url, endpoint}. Usa el `inject_session_user` context processor existente que ya expone `session_permisos`.
4. **Cards faltantes**: Agregar dos bloques `{% if %}` en `home.html` para Derechos e Import/Genderize.

## Architecture Decisions

### Decision: Nav como Jinja inline vs. Python helper

| Opción | Tradeoff |
|--------|----------|
| **Elegido**: Diccionario Jinja en la template | Cero cambios Python. El mapeo es declarativo y fácil de modificar. |
| Alternativa: Helper Python que retorna lista filtrada | Requiere modificar el context processor o crear uno nuevo. Violenta "no cambiar rutas". |

### Decision: Footer existente en CSS vs. nuevo

| Opción | Tradeoff |
|--------|----------|
| **Elegido**: Usar `.layout__footer` ya definido en `base.css` | Ya existe con estilos, solo falta el markup en `base.html`. Consistente con la arquitectura actual. |
| Alternativa: Footer nuevo con clase distinta | Duplicaría estilos. Sin beneficio. |

### Decision: Permiso para Import/Genderize

| Opción | Tradeoff |
|--------|----------|
| **Elegido**: Sin permiso específico, visible para todo auth | `import_facturas_page` no tiene `@permiso_requerido` — mostrar el link a todos los autenticados. |
| Alternativa: Agregar permiso y decorador | Cambia ruta Python, out of scope. |

### Decision: Nav items mapping en base.html

| Opción | Tradeoff |
|--------|----------|
| **Elegido**: `{% set nav_items = {...} %}` en `base.html` | Simple, sin nuevos archivos. El nav solo vive aquí. |
| Alternativa: Template parcial `_nav.html` | Mejor para reuso, pero no hay reuso — solo `base.html` usa nav. |

## Data Flow

```
Session (permisos list)
    │
    ▼
inject_session_user()          ← context processor en app/__init__.py
    │
    ▼
base.html: {{ session_permisos }}  ← disponible en TODAS las templates que extienden base.html
    │
    ├─► Nav: filtra nav_items contra session_permisos
    │    Renderiza <a> para cada match
    │
    └─► home.html: filtra area_cards contra session.get('permisos', [])
         (patrón existente, sin cambios)
```

El nav usa el mismo source de verdad (`session['permisos']`) que los decoradores `@permiso_requerido` — no hay desincronización posible.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/templates/base.html` | Modify | Remover easter-egg del title (L184-195). Agregar footer con versión + dblclick easter-egg. Agregar `<nav>` horizontal permission-aware. |
| `app/templates/home.html` | Modify | Agregar cards para Derechos (`derechos_page`) e Import/Genderize (`import_facturas_page`). |
| `app/static/css/base.css` | Modify | Agregar estilos para `.layout__nav` y `.layout__footer--clickable`. Sin cambios a estilos existentes. |

### Sin cambios
- `app/routes/home.py` — No requiere cambios (permissions via `session.get('permisos')` ya funciona).
- `app/templates/control_errores.html`, `abiertas_urgencias.html` — Heredan nav de `base.html` automáticamente.
- `app/templates/usuarios.html`, `import_facturas.html` — Standalone por diseño, no extienden `base.html`.

## Interfaces / Contracts

### Nav Item Mapping (Jinja dict en base.html)

```jinja
{% set nav_items = {
    'odontologia':        {'label': 'Odontología',        'endpoint': 'excel_headers.excel_headers_page'},
    'urgencias':          {'label': 'Urgencias',          'endpoint': 'urgencias.urgencias_page'},
    'control_urgencias':  {'label': 'Control Urgencias',  'endpoint': 'control_errores.control_errores_page'},
    'equipos_basicos':    {'label': 'Ordenado y Facturado','endpoint': 'ordenado_facturado.ordenado_facturado_page'},
    'facturas_abiertas':  {'label': 'Facturas Abiertas',  'endpoint': 'abiertas_urgencias.abiertas_urgencias_page'},
    'derechos':           {'label': 'Derechos',           'endpoint': 'derechos.derechos_page'},
    '*':                  {'label': 'Usuarios',           'endpoint': 'auth.listar_usuarios'},
} %}
```

### Permission Resolution para nav

```
Para cada permiso P en session_permisos:
  Si P == '*':
    Mostrar TODOS los items del nav (admin)
  Si P existe como clave en nav_items:
    Mostrar ese item
  Si P contiene ':' (e.g. 'control_urgencias:write'):
    Usar la parte antes de ':' como clave (e.g. 'control_urgencias')
```

### Import/Genderize en nav

No tiene permiso específico. Se muestra como ítem siempre visible para usuarios autenticados con `session_permisos` no vacío, o como ítem separado fuera del loop de permisos.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Manual | Mini.local link navega a `/dashboard` | Click en title desde cualquier área child → confirma URL |
| Manual | Easter egg en footer | Doble-click en versión del footer → modal login aparece |
| Manual | Nav permission-aware | Login como admin → ve todos los links. Login como usuario odontologia → ve solo Odontología + Dashboard |
| Manual | Templates custom headers | Navegar a `control_errores.html` y `abiertas_urgencias.html` → layout correcto con nav |
| Visual | Dashboard cards nuevas | Login como admin → ve cards Derechos e Import/Genderize |

No hay tests unitarios automatizados para templates puros (Flask no renderiza templates en tests sin app context). Verificación 100% manual + visual.

## Migration / Rollout

No migration required. Rollback via `git revert` de los commits en `base.html`, `home.html`, `base.css`.

## Open Questions

- [ ] ¿El nav debe mostrar "Importar Facturas" a TODOS los autenticados o solo a los que tienen al menos un permiso? (Propuesta: a todos los auth, pues la ruta no tiene `@permiso_requerido`).
- [ ] ¿Iconos en el nav o solo texto? Los cards del dashboard tienen SVG icons, pero el nav horizontal con icons puede ser visualmente pesado. Propuesta: solo texto con hover highlight.
