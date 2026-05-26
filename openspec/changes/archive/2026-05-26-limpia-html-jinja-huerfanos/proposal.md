# Proposal: Limpia los HTML Jinja huérfanos

## Intent

Eliminar templates Jinja que ninguna ruta renderiza, eliminando confusión durante cambios futuros. Conservar `control_errores.html`, `base.html` y sidebar — aún no migrados a React.

## Scope

### In Scope
- Eliminar 7 huérfanos: `home`, `login`, `usuarios`, `import_facturas`, `derechos`, `abiertas_urgencias`, `ordenado_facturado`
- Convertir 2 semi-activos (`urgencias.html`, `excel_headers.html`) a JSON error responses (solo usados en fallback POST)
- Actualizar tests: `test_favicon_titles.py`, `test_visual_redesign.py`
- Eliminar `auth.login_legacy` de `PUBLIC_ENDPOINTS` en `__init__.py`

### Out of Scope
- Migrar `control_errores` a React (cambio separado)
- Lógica de negocio o refactor de rutas

## Capabilities

### New Capabilities
None — refactor puro.

### Modified Capabilities
None — ningún cambio a nivel de spec.

## Approach

**Opción recomendada (A):** Eliminar huérfanos + convertir semi-activos a JSON.
Las rutas POST de urgencias y odontología ya retornan JSON en éxito; los fallbacks Jinja (`render_template("urgencias.html")` / `render_template("excel_headers.html")`) son código muerto que el frontend React nunca espera. Convertirlos a `jsonify(error), 400` elimina 2 dependencias sin perder funcionalidad.

## Affected Areas

| Area | Impact | Descripción |
|------|--------|-------------|
| `app/templates/{7 orphans}.html` | Removed | home, login, usuarios, import_facturas, derechos, abiertas_urgencias, ordenado_facturado |
| `app/routes/urgencias.py` (L78,90) | Modified | Fallback Jinha → JSON |
| `app/routes/excel_headers.py` (L97,109) | Modified | Fallback Jinja → JSON |
| `app/__init__.py` (L15) | Modified | Quitar `auth.login_legacy` de PUBLIC_ENDPOINTS |
| `tests/services/test_favicon_titles.py` | Modified | Remover login, import_facturas, usuarios de TEMPLATES |
| `tests/services/test_visual_redesign.py` | Modified | Remover tests de templates eliminados |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fallback Jinja aún usado por cliente no-React | Baja | React es el único frontend; POST que falla retorna JSON a fetch(), nunca renderiza HTML |
| Tests rotos hasta actualizarlos | Baja | Tests se actualizan en el mismo cambio |
| `auth.login_legacy` tiene código asociado | Baja | La ruta NO existe — eliminarlo de la whitelist solo evita error silencioso |

## Rollback Plan

1. Commit por capa: templates → rutas → tests → endpoints
2. Revertir commit completo si hay issues
3. Templates eliminados se recuperan del historial git

## Success Criteria

- [ ] 7 templates huérfanos eliminados de `app/templates/`
- [ ] `urgencias.html` y `excel_headers.html` ya no se renderizan (post-error retorna JSON)
- [ ] `pytest -v` pasa sin errores
- [ ] `auth.login_legacy` removido de `PUBLIC_ENDPOINTS`
- [ ] Sidebar y control_errores funcionales (sin cambios)
