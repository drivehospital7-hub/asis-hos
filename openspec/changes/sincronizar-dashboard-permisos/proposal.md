# Proposal: Sincronizar Dashboard con Permisos

## Intent

El sidebar ya filtra navegación por `permisos`, pero el dashboard (home) muestra áreas hardcodeadas sin filtrar, la ruta `/derechos` carece de guard, y no hay un mapeo centralizado área↔permiso. Unificar la lógica para que dashboard, sidebar y guards compartan la misma fuente de verdad.

## Scope

### In Scope
- Filtrar áreas del dashboard contra `session["permisos"]` (backend)
- Agregar `@permiso_requerido("derechos")` a `derechos.py`
- Centralizar mapeo área↔permiso en `app/constants/base.py`
- Remover fallback hardcodeado de áreas en frontend `page.tsx`
- Tests: dashboard filtrado por permisos + guard de derechos

### Out of Scope
- Refactor del sidebar `ALL_NAV` para consumir mapeo centralizado (es frontend TS puro, no comparte backend)
- Agregar nuevas áreas al dashboard (solo sincronizar las existentes)
- Migrar permisos existentes o agregar nuevos

## Capabilities

### New Capabilities
- `dashboard-permissions`: Filtrado del dashboard por permisos de usuario

### Modified Capabilities
- `admin-users-permissions`: se agrega `derechos` al mapeo canónico de permisos `ALLOWED_PERMISOS` y se sincroniza dashboard

*Nota: `derechos` ya está en `ALLOWED_PERMISOS`.*

## Approach

**Central mapping** (`app/constants/base.py`):
```python
DASHBOARD_AREAS = [
    {"title": "Urgencias", "slug": "urgencias", "permiso": "urgencias",
     "href": "/urgencias", "tone": "danger", "pending_label": "errores"},
    {"title": "Odontología", "slug": "odontologia", "permiso": "odontologia",
     "href": "/odontologia", "tone": "info", "pending_label": "errores"},
    {"title": "Control de Novedades", "slug": "control_errores", "permiso": "control_urgencias",
     "href": "/control-errores", "tone": "warning", "pending_label": "pendientes"},
    {"title": "Facturas Abiertas", "slug": "abiertas_urgencias", "permiso": "facturas_abiertas",
     "href": "/abiertas-urgencias", "tone": "info", "pending_label": "sin horario"},
    {"title": "Ordenado y Facturado", "slug": "ordenado_facturado", "permiso": "equipos_basicos",
     "href": "/ordenado-facturado", "tone": "info", "pending_label": "pendientes"},
    {"title": "Derechos", "slug": "derechos", "permiso": "derechos",
     "href": "/derechos", "tone": "info", "pending_label": "pendientes"},
]
```

**Backend filter** (`home.py`): iterar `DASHBOARD_AREAS`, incluir solo si `permiso in session["permisos"]` o `"*"` en permisos.

**Frontend** (`page.tsx`): usar `initialData.areas` directamente (ya filtrado por backend). Remover el `areas` fallback hardcodeado.

**Route guard** (`derechos.py`): agregar `@permiso_requerido("derechos")` antes de `def derechos_react()`.

## Affected Areas

| Area | Impact | Descripción |
|------|--------|-------------|
| `app/constants/base.py` | Modified | Agregar `DASHBOARD_AREAS` |
| `app/routes/home.py` | Modified | Filtrar áreas por permisos |
| `app/routes/derechos.py` | Modified | Agregar `@permiso_requerido("derechos")` |
| `frontend/src/pages/index/page.tsx` | Modified | Usar solo `initialData.areas` |
| `tests/services/test_react_frontend.py` | Modified | Tests: dashboard filtrando, derechos con guard |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dashboard oculta áreas para admin si mapping no incluye `"*"` check | Baja | Filter explícito: si `"*"` en permisos → mostrar todo |
| Frontend fallback se rompe si `initialData` es null | Baja | `initialData?.areas ?? []` (lista vacía, no crash) |
| Sidebar y dashboard divergen si se agrega área solo en un lado | Media | `DASHBOARD_AREAS` documentado como source of truth del backend |

## Rollback Plan

1. Commit por capa: constants → home → derechos → frontend → tests
2. Revertir commit de `base.py` elimina el mapping
3. Revertir `home.py` y `derechos.py` restaura comportamiento anterior
4. Frontend revierte independientemente (JS/TS build)
5. Tests se revierten con cada capa

## Success Criteria

- [ ] Usuario con solo `odontologia` ve solo tarjeta Odontología en dashboard
- [ ] Admin (`*`) ve todas las áreas
- [ ] Usuario sin `derechos` recibe 403 en `/derechos`
- [ ] `DASHBOARD_AREAS` definido en `base.py` y usado por `home.py`
- [ ] Frontend no tiene áreas hardcodeadas en `page.tsx`
- [ ] Tests: dashboard filtra, derechos rechaza sin permiso
