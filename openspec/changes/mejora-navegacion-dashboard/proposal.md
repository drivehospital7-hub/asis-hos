# Proposal: Mejora de Experiencia de Navegación entre Dashboard y Áreas

## Intent

Usuarios no pueden volver al dashboard desde las áreas porque el link "Mini.local" en el header está roto por un easter-egg JS. No existe barra de navegación ni breadcrumbs. La única navegación entre áreas es un enlace manual en `control_errores.html` ↔ `abiertas_urgencias.html`.

## Scope

### In Scope
- Arreglar link Mini.local para que navegue al dashboard correctamente
- Mover el easter-egg de login a un trigger alternativo (doble-click en footer/versión)
- Agregar barra de navegación horizontal con links a áreas accesibles según permisos
- Agregar cards faltantes en dashboard (Derechos, Import/Genderize)

### Out of Scope
- Hacer que `usuarios.html` e `import_facturas.html` extiendan `base.html` (standalone por diseño)
- Navegación responsive / colapso mobile
- Breadcrumbs adicionales por sub-sección
- Renombrar "Mini.local" a otro nombre

## Capabilities

> Esta sección es el CONTRATO entre proposal y specs.

### New Capabilities
None — cambio puro de UX/UI, no introduce nuevas capacidades de negocio.

### Modified Capabilities
None — no cambia requisitos a nivel spec, solo implementación de layout.

## Approach

**Enfoque 1** (exploración): arreglar Mini.local + agregar nav horizontal.

1. Remover el event listener JS que secuestra el click en `.layout__title--clickable`. El `href="url_for('home.home_page')"` ya existe — solo necesita funcionar.
2. Mover la lógica del easter-egg (3-clicks → modal login) a un doble-click en el footer o versión de la app.
3. Agregar un nav horizontal en `base.html` con links permission-aware, iterando `session['permisos']` contra un mapeo route → permiso.
4. Agregar cards para Derechos e Import/Genderize en `home.html`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/templates/base.html` | Modified | Remover easter-egg JS del título, agregar nav |
| `app/templates/home.html` | Modified | Agregar cards faltantes |
| `app/static/css/base.css` | Modified | Estilos para el nuevo nav |
| `app/routes/home.py` | None | No requiere cambios |

Los templates de área (`excel_headers.html`, `urgencias.html`, etc.) NO requieren cambios individuales porque heredan el nav de `base.html`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Easter-egg login modal es ruta secundaria de login | Medium | Mantener funcionalidad intacta, solo mover trigger |
| Nav permission-aware se desincronice con decoradores de rutas | Low | Mapeo centralizado en constants o helper |
| Templates con headers custom (control_errores, abiertas_urgencias) choquen visualmente con nav | Low | Verificar spacing después del cambio |

## Rollback Plan

Revertir cambios en `base.html`, `home.html` y `base.css` mediante `git revert`. El easter-egg original se restaura completamente. Sin migraciones ni cambios de datos.

## Dependencies

Ninguna.

## Success Criteria

- [ ] Click en "Mini.local" navega al dashboard desde cualquier área
- [ ] Easter-egg login sigue funcionando desde nuevo trigger
- [ ] Nav en `base.html` muestra solo áreas que el usuario tiene permiso de ver
- [ ] Dashboard incluye cards para Derechos e Import/Genderize
- [ ] `control_errores.html` y `abiertas_urgencias.html` se ven correctamente con el nav
