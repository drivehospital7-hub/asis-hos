# Proposal: Roles Facturador y Responsables Dinámicos

## Intent

Agregar roles "medico" y "facturador" al sistema de usuarios. Reemplazar responsables hardcodeados (3 lugares duplicados) por una lista dinámica: usuarios con rol "facturador" servida por API. El admin define quién es facturador desde la UI de usuarios — todo el sistema se sincroniza.

## Scope

### In Scope
- Validación de `rol` en `users_store.py`: agregar `"medico"` y `"facturador"`
- Dropdown de roles en UI usuarios (Jinja2 + React): nuevas opciones
- `GET /api/users/facturadores` → usuarios con rol facturador
- `control_errores_service.get_opciones()` → poblar responsables desde API
- `abiertas-urgencias` → consumir `/api/facturadores` en vez de `constants.ts`
- Fallback a hardcoded si no hay facturadores

### Out of Scope
- Migración retroactiva de `control_errores.json` (free-text existente)
- Normalización nombres schedule vs nombres usuario (dominios distintos)
- Validación responsable vs usuario (sigue siendo free-text en registros)

## Capabilities

### New
- `facturadores-dynamic-responsables`: Endpoint `/api/facturadores` como fuente única de responsables para control-errores y abiertas-urgencias.

### Modified
- `admin-users-permissions`: Validación de `rol` se expande de `["admin","usuario"]` a `["admin","usuario","medico","facturador"]`. UI dropdown actualizado.

## Approach

**Approach 1 (Minimal)**. Cadena: `users_store.py` (rol=facturador) → `GET /api/facturadores` → `get_opciones()` reemplaza constantes → frontends consumen mismo endpoint. Graceful degradation: si no hay facturadores, se usan hardcodeados.

## Affected Areas

| Area | Impact |
|------|--------|
| `app/utils/users_store.py` | Validación rol + `get_facturadores()` |
| `app/routes/auth.py` | Endpoint `GET /api/facturadores` |
| `app/constants/urgencias.py` | Pasa a fallback |
| `app/services/control_errores_service.py` | `get_opciones()` usa facturadores |
| `app/templates/usuarios.html` | Dropdown nuevos roles |
| `frontend/src/pages/usuarios/page.tsx` | Dropdown nuevos roles |
| `frontend/src/pages/abiertas-urgencias/constants.ts` | API-driven |
| `tests/` | Validación de rol ampliada |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Carga masiva espera formato exacto de nombres | Medium | Fallback mantiene compatibilidad |
| Admin crea facturadores sin nombres → responsables vacíos | Low | Validar `primer_nombre` en store |

## Rollback Plan

1. Revertir `users_store.py` a validación original
2. Revertir `get_opciones()` a constantes
3. Remover endpoint `/api/facturadores`
4. Frontend a `constants.ts` original
5. Sin pérdida de datos — registros existentes intactos

## Success Criteria

- [ ] Admin crea/edita usuarios con rol "medico" y "facturador"
- [ ] `GET /api/facturadores` retorna solo `rol == "facturador"`
- [ ] Filtro responsables en control-errores refleja facturadores dinámicos (o fallback)
- [ ] Carga masiva matchea contra facturadores dinámicos
- [ ] Abiertas-urgencias obtiene responsables desde API
- [ ] Tests pasan sin regresión
