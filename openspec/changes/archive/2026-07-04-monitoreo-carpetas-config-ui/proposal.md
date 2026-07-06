# Proposal: Monitoreo de Carpetas — Config UI

## Intent

Rutas de red solo de env var. Cambiarlas requiere infraestructura (editar + reiniciar). Los facturadores cambian de estructura constantemente — necesitamos edición admin desde UI, sin reinicios.

## Scope

### In Scope
- `monitoreo_store.py` — JSON store con atomic write (patrón `errores_storage.py`)
- `GET /config`, `PUT /config`, `POST /config/reset`
- `POST /scan` lee del store, fallback a env var
- `monitoreo_carpetas` + `monitoreo_carpetas:write` en `ALLOWED_PERMISOS`, `PERMISO_MUTUAL_EXCLUSION`, `ALL_PERMISOS`, `DASHBOARD_AREAS`
- Card de configuración en `page.tsx` (textarea + Guardar/Resetear, solo si `can_write`)
- Nav item en sidebar con permiso `monitoreo_carpetas`

### Out of Scope
- Edición concurrente, validación de reachability, historial de cambios, notificaciones

## Capabilities

### New
- `folder-scanner-config`: Persistencia de rutas raíz desde UI con atomic write, fallback a env var, reset.

### Modified
- `folder-scanner`: Scan lee del store. API y data contract no cambian.

## Approach

Store liviano con `get_roots()`, `save_roots()`, `reset_roots()` (tempfile + Path.replace). Endpoints protegidos con `@permiso_requerido('monitoreo_carpetas:write')`. Card condicional en frontend.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/utils/monitoreo_store.py` | New | JSON store atomic write |
| `app/constants/monitoreo_carpetas.py` | Modified | +`MONITOREO_CONFIG_FILE` |
| `app/constants/base.py` | Modified | +permisos en listas |
| `app/routes/monitoreo_carpetas.py` | Modified | +3 config endpoints; scan usa store |
| `frontend/.../monitoreo-carpetas/page.tsx` | Modified | Card config + botones |
| `frontend/.../usuarios/page.tsx` | Modified | +permisos en `ALL_PERMISOS` |
| `frontend/.../app-sidebar.tsx` | Modified | +nav item |
| `data/monitoreo_carpetas_config.json` | New | Creado en primer save |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| JSON corrupto por corte energía | Low | Atomic write |
| Admin guarda rutas inválidas | Low | Scan tolera errores; reset rápido |
| Permiso débil | Low | Nav usa `monitoreo_carpetas` (lectura); `:write` controla edición |

## Rollback Plan

1. Revertir `app/routes/monitoreo_carpetas.py`
2. Borrar `monitoreo_store.py` + `monitoreo_carpetas_config.json`
3. Revertir `app/constants/` y frontend files
4. Cada commit independiente — revertir en orden inverso

## Dependencies

- `Path` + `json` + `tempfile` (stdlib). Blueprint ya registrado.

## Success Criteria

- [ ] `GET /config` retorna rutas persistidas o env var
- [ ] `PUT /config` persiste atómicamente y se refleja
- [ ] `POST /config/reset` borra persistido, GET retorna env var
- [ ] `POST /scan` usa store si existe, fallback a env var
- [ ] Admin edita desde UI; sin `:write` solo lectura
- [ ] Permisos aparecen en listas de usuario
- [ ] Nav item visible según permiso
- [ ] Tests existentes pasan
