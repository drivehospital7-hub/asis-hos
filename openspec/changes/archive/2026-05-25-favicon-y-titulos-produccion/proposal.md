# Proposal: Favicon y títulos de producción

## Intent

El sitio muestra `— React` en el título de las páginas SPA, lo que no tiene sentido en producción. Además, no existe ningún favicon — el navegador muestra el icono por defecto. La usuaria pide poner un favicon como el del login de HOS (monograma verde "HO") y cambiar los títulos para que reflejen el nombre real del sistema.

## Scope

### In Scope
- Agregar `<link rel="icon">` con el favicon de HOS a todas las plantillas HTML head
- Crear/extraer el favicon (`favicon.ico` o `favicon.svg`) desde el branding del login de HOS
- Cambiar `— React` por `· Hospital Orito` en `react_shell.html` y `react_standalone.html`
- Normalizar el título por defecto en `base.html` de `"Control Facturacion"` a `"Hospital Orito · Control de Facturación"`
- Agregar favicon a `login.html`, `import_facturas.html`, `usuarios.html` y cualquier otra standalone
- Actualizar título de `login.html` a `"Ingresar · Hospital Orito"`

### Out of Scope
- Normalizar el resto de títulos de templates server-side (ya mezclan estilos y separadores) — queda como mejora futura
- Cambiar el branding visual del login (colores, logo, layout)
- Modificar los títulos de las SPA React (ya están correctos: `Login · Hospital Orito`, `Panel principal · Hospital Orito`, etc.)

## Capabilities

> No hay cambios a nivel de especificaciones de negocio. Es un cambio puramente visual/de presentación sin impacto en reglas de negocio.

### New Capabilities
None

### Modified Capabilities
None

## Approach

1. **Obtener el favicon**: Extraer o recrear el monograma "HO" verde del login de HOS como `favicon.ico` (32×32) y `favicon.svg` (para navegadores modernos). Ubicar en `app/static/`.
2. **Agregar a templates**: Insertar `<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">` y `<link rel="alternate icon" href="/static/favicon.ico">` en el `<head>` de:
   - `app/templates/base.html` (cubre todos los que extienden base)
   - `app/templates/react_shell.html`
   - `app/templates/react_standalone.html`
   - `app/templates/login.html`
   - `app/templates/import_facturas.html`
   - `app/templates/usuarios.html`
3. **Corregir títulos**:
   - `react_shell.html` y `react_standalone.html`: cambiar `— React` → `· Hospital Orito` en el título por defecto
   - `base.html`: cambiar `Control Facturacion` → `Hospital Orito · Control de Facturación`
   - `login.html`: cambiar `Login — Control Facturación` → `Ingresar · Hospital Orito`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/static/favicon.ico` | New | Favicon clásico 32×32 |
| `app/static/favicon.svg` | New | Favicon SVG moderno |
| `app/templates/base.html` | Modified | + favicon link, + title por defecto |
| `app/templates/react_shell.html` | Modified | + favicon link, title `— React` → `· Hospital Orito` |
| `app/templates/react_standalone.html` | Modified | + favicon link, title `— React` → `· Hospital Orito` |
| `app/templates/login.html` | Modified | + favicon link, title normalizado |
| `app/templates/import_facturas.html` | Modified | + favicon link |
| `app/templates/usuarios.html` | Modified | + favicon link |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Favicon no se ve por caché del navegador | Medium | Usar SVG + ICO; hard-refresh指导 en verify |
| No se tiene acceso al asset original del monograma HO | Medium | Recrear SVG simple con las letras "HO" en verde (#16a34a) como fallback |
| Template standalone olvidada | Low | Grepear `<!DOCTYPE html` en `templates/` para encontrar TODAS las plantillas |

## Rollback Plan

1. Revertir cambios en los templates con `git checkout -- app/templates/`
2. Eliminar los archivos `app/static/favicon.ico` y `app/static/favicon.svg`
3. `git revert` del commit si ya se pusheó

## Dependencies

- Acceso al asset del monograma "HO" del login de HOS (si no se tiene, se crea un SVG equivalente)

## Success Criteria

- [ ] El favicon de HOS aparece en la pestaña del navegador en todas las páginas (login, SPA, server-side)
- [ ] Ningún título de página muestra `— React` — todos usan `· Hospital Orito`
- [ ] Los títulos por defecto en server-side son consistentes con el formato del sistema
- [ ] `git diff --stat` muestra solo los templates y los nuevos assets de favicon — sin cambios colaterales
