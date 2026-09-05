# Proposal: Unified Permission Model — /procesar, cronogramas, and security gating

## Intent

The old area-based permissions (`urgencias`, `odontologia`, `odontologia_equipos_basicos`) no longer reflect the architecture — all routes now go through a single `/procesar` endpoint. Users with those old permissions need a unified `procesar` permission. Cronogramas are admin-only (`*`) but should be granular. Several route files have zero permission decorators, leaving security gaps.

## Scope

### In Scope
- New `procesar` / `procesar:write` permission — replaces old `urgencias`, `odontologia`, `odontologia_equipos_basicos`
- New `cronograma_bacteriologas` and `cronograma_urgencias` granular permissions
- Permission migration in `_load_users()` for backward compatibility
- Route decorator updates for cronogramas, derechos API, notas_api, import_csv, procedimientos
- Frontend sidebar and usuarios page updates
- Dead page deletion (odontologia, urgencias, odontologia-equipos-basicos frontend pages)
- Tests for migration, validation, and integration

### Out of Scope
- UI redesign of the usuarios page
- Changes to the actual processing logic in services
- Database changes (users are file-based)

## Approach

1. **Phase 1 — Constants & Migration**: Update `ALLOWED_PERMISOS`, `PERMISO_MUTUAL_EXCLUSION`, `DASHBOARD_AREAS`, `DEFAULT_TEMPLATES`, `DEFAULT_USERS` in `app/constants/base.py` and `app/utils/users_store.py`. Add migration loop in `_load_users()`.
2. **Phase 2 — Route Decorators**: Update permission checks on `procesar.py`, `cronograma_bacteriologas.py`, `cronograma_urgencias.py`, `derechos.py`, `procedimientos.py`, `notas_api.py`, `import_csv.py`.
3. **Phase 3 — Frontend**: Update sidebar nav permissions, usuarios page `ALL_PERMISOS`, delete dead frontend pages.
4. **Phase 4 — Tests**: Unit tests for migration, mutual exclusion, validation; integration tests for route access.

## Rollback

Revert the commit. Old permissions are still valid for login but will be migrated on next `_load_users()` call. Reverting restores the old checks.
